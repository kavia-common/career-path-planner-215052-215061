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
import os
from dotenv import load_dotenv

# Ensure .env is loaded when running as a CLI
load_dotenv(override=False)

# Normalize accidental "psql '...'" copy-paste in .env to just the URL
dbu = os.getenv("DATABASE_URL")
if dbu and dbu.strip().startswith("psql "):
    # Extract content within single or double quotes
    import shlex
    parts = shlex.split(dbu)
    if len(parts) >= 2:
        os.environ["DATABASE_URL"] = parts[1]

from src.core.db import init_db, ping_db, engine
from src.core.schema_sync import run_schema_sync
from sqlalchemy import text


def main() -> None:
    # Verify DATABASE_URL presence and connectivity first
    status = ping_db()
    print(f"[cli] db_ping: {status}")
    if not status.get("ok"):
        # Explicit guidance if missing env
        print("[cli] ERROR: DATABASE_URL missing or unreachable. Ensure DATABASE_URL is set and points to Neon Postgres.")
        return

    # Ensure ORM base tables are created (safe if already present)
    init_db()
    print("[cli] create_all: done")

    # Run schema synchronization (idempotent CREATE/ALTER)
    sync = run_schema_sync()
    print(f"[cli] schema_sync: ok={sync.get('ok')} executed={sync.get('executed')}")

    # Show concise warnings if any errors captured
    errors = sync.get("errors") or []
    for e in errors:
        print(f"[cli] WARN: {e}")

    # Final connectivity check via a quick SELECT 1
    try:
        assert engine is not None
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[cli] verify: SELECT 1 OK")
    except Exception as e:
        print(f"[cli] verify: SELECT 1 FAILED: {e.__class__.__name__}: {e}")


if __name__ == "__main__":
    main()
