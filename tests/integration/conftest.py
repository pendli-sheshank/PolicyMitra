"""Integration test fixtures: a dedicated test database (TEST_DATABASE_URL),
reset once per test session — the four PolicyMitra schemas are dropped and
re-migrated, then ingested with the real synthetic corpus so every
integration test has real data to work against — no mocking of the DB layer.

TEST_DATABASE_URL must point at a Postgres database with pgvector available
and which is safe to wipe (schemas kb/mem/agent/audit are dropped with
CASCADE). Without it the integration suite is skipped, keeping `pytest`
runnable in environments that have no database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

CORPUS_DIR = Path(__file__).parent.parent.parent / "corpus" / "insurers"

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

if not TEST_DATABASE_URL:
    collect_ignore_glob = ["*"]
    pytest.skip(
        "TEST_DATABASE_URL is not set; skipping integration tests (they need a "
        "disposable Postgres database with pgvector).",
        allow_module_level=True,
    )


@pytest.fixture(scope="session", autouse=True)
def test_database():
    # Must be set before the first get_connection() call anywhere in the suite.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    from db.migrate import run_migrations

    run_migrations(TEST_DATABASE_URL, reset=True)

    from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
    from ingestion.pipeline import run_ingestion

    for insurer_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        run_ingestion(insurer_dir, LocalHashEmbedder())

    yield
    # Schemas are left in place for post-mortem inspection; the next run resets them.


@pytest.fixture()
def conn():
    from db.connection import get_connection

    connection = get_connection()
    yield connection
    connection.close()
