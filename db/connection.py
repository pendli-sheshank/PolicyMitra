"""Shared Postgres connection helper used by ingestion, retrieval, and the API.

The database is Postgres with the pgvector extension — a Supabase project in
the default deployment, but any Postgres 15+ with `CREATE EXTENSION vector`
available works. DATABASE_URL is required; there is no embedded fallback.

Connections run in autocommit mode; callers that need atomicity open an
explicit transaction (see ingestion/pipeline.py). prepare_threshold=None
disables server-side prepared statements, which break behind PgBouncer-style
poolers — including Supabase's connection pooler, whose session-mode DSN
(aws-*-*.pooler.supabase.com:5432) is the one IPv4-only clients must use
(the direct db.<ref>.supabase.co host is IPv6-only).
"""

from __future__ import annotations

import os
import threading

import psycopg
from pgvector.psycopg import register_vector

# One migration pass per process is enough; guarded for concurrent first calls.
_migrate_lock = threading.Lock()
_migration_checked = False


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. PolicyMitra needs a Postgres database with the "
            "pgvector extension (e.g. a Supabase project's session-pooler DSN: "
            "postgresql://postgres.<project-ref>:<password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres). "
            "Set it in the environment or in .env — see .env.example."
        )
    return url


def _ensure_migrated(conn: psycopg.Connection) -> None:
    global _migration_checked
    if _migration_checked:
        return
    with _migrate_lock:
        if _migration_checked:
            return
        row = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'kb' AND table_name = 'documents'"
        ).fetchone()
        if row is None:
            from db.migrate import run_migrations

            run_migrations(database_url())
        _migration_checked = True


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(database_url(), autocommit=True, prepare_threshold=None)
    _ensure_migrated(conn)
    register_vector(conn)
    return conn
