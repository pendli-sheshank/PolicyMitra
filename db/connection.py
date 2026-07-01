"""Shared Postgres connection helper used by ingestion, retrieval, and the API."""

from __future__ import annotations

import os

import psycopg
from pgvector.psycopg import register_vector


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/policymitra")


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(database_url(), autocommit=True)
    register_vector(conn)
    return conn
