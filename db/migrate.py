"""Forward-only migration runner: applies db/schema/*.sql in filename order.

No ORM migration framework is needed at this scale (a handful of schema files
that are idempotent via IF NOT EXISTS). Runs automatically on first connection
to a fresh database file (db/connection.py), or explicitly with:
    python -m db.migrate [--db-path data/policymitra.db]
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent / "schema"


def run_migrations(path: Path | str) -> None:
    path = Path(path)
    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    if not sql_files:
        print(f"No schema files found in {SCHEMA_DIR}", file=sys.stderr)
        sys.exit(1)

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for sql_file in sql_files:
            print(f"Applying {sql_file.name} ...")
            conn.executescript(sql_file.read_text())
    finally:
        conn.close()
    print(f"Applied {len(sql_files)} migration file(s) to {path}")


def main() -> None:
    from db.connection import db_path

    parser = argparse.ArgumentParser(description="Run PolicyMitra DB migrations")
    parser.add_argument("--db-path", default=str(db_path()))
    args = parser.parse_args()
    run_migrations(args.db_path)


if __name__ == "__main__":
    main()
