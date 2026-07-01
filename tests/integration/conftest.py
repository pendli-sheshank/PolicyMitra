"""Integration test fixtures: a dedicated `policymitra_test` database, wiped
and recreated once per test session, migrated fresh, then ingested with the
real synthetic corpus so every integration test has real data to work
against — no mocking of the DB layer."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

TEST_DB_NAME = "policymitra_test"
ADMIN_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
CORPUS_DIR = Path(__file__).parent.parent.parent / "corpus" / "insurers"


def _admin_connect() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DATABASE_URL, autocommit=True)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with _admin_connect() as admin_conn:
        admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        admin_conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")

    os.environ["DATABASE_URL"] = f"postgresql://postgres:postgres@localhost:5432/{TEST_DB_NAME}"

    from db.migrate import run_migrations

    run_migrations(os.environ["DATABASE_URL"])

    from ingestion.embedding.local_hash_embedder import LocalHashEmbedder
    from ingestion.pipeline import run_ingestion

    for insurer_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        run_ingestion(insurer_dir, LocalHashEmbedder())

    yield

    with _admin_connect() as admin_conn:
        admin_conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")


@pytest.fixture()
def conn():
    from db.connection import get_connection

    connection = get_connection()
    yield connection
    connection.close()
