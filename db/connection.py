"""Shared SQLite connection helper used by ingestion, retrieval, and the API.

The database is a single file (data/policymitra.db by default, POLICYMITRA_DB
to override) — no server, no credentials, no required .env. Connections run in
autocommit mode (isolation_level=None), matching the previous psycopg
autocommit=True contract; callers that need atomicity issue an explicit BEGIN
(see ingestion/pipeline.py). Do not add code that relies on the stdlib
sqlite3 context-manager transaction semantics — the subclasses below give
psycopg-style semantics instead (cursor is a context manager; closing the
connection on `with` exit).
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from array import array
from datetime import UTC, date, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# One migration pass per process is enough; guarded for concurrent first calls.
_migrate_lock = threading.Lock()


def db_path() -> Path:
    return Path(os.environ.get("POLICYMITRA_DB", _REPO_ROOT / "data" / "policymitra.db"))


def utc_now_iso() -> str:
    """Single timestamp format for every writer — TTL logic compares these
    lexicographically, so all timestamps must be UTC ISO-8601 with offset."""
    return datetime.now(UTC).isoformat()


class Cursor(sqlite3.Cursor):
    """sqlite3.Cursor with psycopg-style `with` support (closes on exit)."""

    def __enter__(self) -> Cursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        self.close()
        return False


class Connection(sqlite3.Connection):
    """sqlite3.Connection with psycopg-style `with` support: exiting the block
    closes the connection (autocommit mode makes commit-on-exit moot)."""

    def cursor(self, factory: type[sqlite3.Cursor] = Cursor) -> Cursor:  # type: ignore[override]
        return super().cursor(factory)  # type: ignore[return-value]

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *exc: object) -> bool:
        self.close()
        return False


sqlite3.register_adapter(uuid.UUID, str)
sqlite3.register_adapter(datetime, datetime.isoformat)
sqlite3.register_adapter(date, date.isoformat)


def pack_vector(vector: list[float]) -> bytes:
    """Embedding list -> packed little-endian float32 BLOB."""
    return array("f", vector).tobytes()


def unpack_vector(blob: bytes) -> array:
    vec = array("f")
    vec.frombytes(blob)
    return vec


def _check_sqlite_features() -> None:
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise RuntimeError(
            f"PolicyMitra needs SQLite >= 3.35 (for RETURNING); found {sqlite3.sqlite_version}. "
            "Upgrade Python's bundled SQLite (e.g. use a python:3.11-bookworm image, not bullseye)."
        )
    probe = sqlite3.connect(":memory:")
    try:
        probe.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(x)")
    except sqlite3.OperationalError as exc:
        raise RuntimeError("PolicyMitra needs an SQLite build with FTS5 compiled in.") from exc
    finally:
        probe.close()


_features_checked = False


def _ensure_migrated(conn: sqlite3.Connection, path: Path) -> None:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kb_documents'").fetchone()
    if row is not None:
        return
    with _migrate_lock:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kb_documents'").fetchone()
        if row is None:
            from db.migrate import run_migrations

            run_migrations(path)


def get_connection() -> Connection:
    global _features_checked
    if not _features_checked:
        _check_sqlite_features()
        _features_checked = True

    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        path,
        factory=Connection,
        check_same_thread=False,
        isolation_level=None,
        timeout=5.0,
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    _ensure_migrated(conn, path)
    return conn  # type: ignore[return-value]
