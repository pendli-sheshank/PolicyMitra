"""Integration test fixtures: a dedicated temp SQLite database file, created
once per test session, migrated fresh, then ingested with the real synthetic
corpus so every integration test has real data to work against — no mocking
of the DB layer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

CORPUS_DIR = Path(__file__).parent.parent.parent / "corpus" / "insurers"


@pytest.fixture(scope="session", autouse=True)
def test_database(tmp_path_factory: pytest.TempPathFactory):
    db_file = tmp_path_factory.mktemp("db") / "policymitra_test.db"
    # Must be set before the first get_connection() call anywhere in the suite.
    os.environ["POLICYMITRA_DB"] = str(db_file)

    from db.migrate import run_migrations

    run_migrations(db_file)

    from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
    from ingestion.pipeline import run_ingestion

    for insurer_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        run_ingestion(insurer_dir, LocalHashEmbedder())

    yield
    # No teardown needed: pytest cleans up the temp directory.


@pytest.fixture()
def conn():
    from db.connection import get_connection

    connection = get_connection()
    yield connection
    connection.close()
