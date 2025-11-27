#!/usr/bin/env python3
"""
CLI to initialize ORM models and then enforce Excel-derived catalog schema via SQL.

This reads DATABASE_URL from environment (Settings.database_url) and executes
CREATE TABLE IF NOT EXISTS and guarded ALTER TABLE statements for:

- roles
- competencies
- role_competencies
- role_adjacency

Logs are concise and suitable for CI output.

Usage:
    python -m src.cli_sync_schema
"""
from src.core.db import init_db
from src.core.schema_sync import run_schema_sync
from src.core.db import ping_db


def main() -> None:
    status = ping_db()
    print(f"[cli] db_ping: {status}")
    if not status.get("ok"):
        return
    init_db()
    print("[cli] create_all: done")
    sync = run_schema_sync()
    print(f"[cli] schema_sync: {sync}")


if __name__ == "__main__":
    main()
