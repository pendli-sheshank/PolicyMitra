"""Forward-only migration runner: applies db/schema/*.sql in filename order.

No ORM migration framework is needed at this scale (a handful of schema files
that are largely idempotent via IF NOT EXISTS). Runs automatically on first
connection to a fresh database (db/connection.py), or explicitly with:
    python -m db.migrate [--database-url postgresql://...] [--reset]

--reset drops the four PolicyMitra schemas (kb, mem, agent, audit) with
CASCADE and re-applies every schema file — the Postgres equivalent of
deleting the old SQLite file. It never touches other schemas in the database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

SCHEMA_DIR = Path(__file__).parent / "schema"
POLICYMITRA_SCHEMAS = ("kb", "mem", "agent", "audit")


def run_migrations(database_url: str, reset: bool = False) -> None:
    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    if not sql_files:
        print(f"No schema files found in {SCHEMA_DIR}", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(database_url, autocommit=True, prepare_threshold=None) as conn:
        if reset:
            for schema in POLICYMITRA_SCHEMAS:
                print(f"Dropping schema {schema} ...")
                conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        for sql_file in sql_files:
            print(f"Applying {sql_file.name} ...")
            conn.execute(sql_file.read_text())
    print(f"Applied {len(sql_files)} migration file(s)")


def main() -> None:
    from db.connection import database_url

    parser = argparse.ArgumentParser(description="Run PolicyMitra DB migrations")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--reset", action="store_true", help="Drop PolicyMitra schemas first, then re-apply")
    args = parser.parse_args()
    run_migrations(args.database_url or database_url(), reset=args.reset)


if __name__ == "__main__":
    main()
