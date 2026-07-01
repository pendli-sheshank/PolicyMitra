"""Forward-only migration runner: applies db/schema/*.sql in filename order.

No ORM migration framework is needed at this scale (a handful of schema files
that are largely idempotent via IF NOT EXISTS). Run with:
    python -m db.migrate [--database-url postgresql://...]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg

SCHEMA_DIR = Path(__file__).parent / "schema"


def default_database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/policymitra")


def run_migrations(database_url: str) -> None:
    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    if not sql_files:
        print(f"No schema files found in {SCHEMA_DIR}", file=sys.stderr)
        sys.exit(1)

    with psycopg.connect(database_url, autocommit=True) as conn:
        for sql_file in sql_files:
            print(f"Applying {sql_file.name} ...")
            conn.execute(sql_file.read_text())
    print(f"Applied {len(sql_files)} migration file(s) to {database_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PolicyMitra DB migrations")
    parser.add_argument("--database-url", default=default_database_url())
    args = parser.parse_args()
    run_migrations(args.database_url)


if __name__ == "__main__":
    main()
