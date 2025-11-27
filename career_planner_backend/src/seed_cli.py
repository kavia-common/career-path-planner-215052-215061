#!/usr/bin/env python3
"""
CLI utility to initialize the Neon/Postgres schema and seed minimal data.

Usage:
    python -m src.seed_cli            # initialize tables and seed minimal and JSON catalog if present
"""

from src.core.db import init_db, seed_minimal_data
from src.core.seeder import seed_catalog_from_json
from src.core.db import ping_db

def main() -> None:
    status = ping_db()
    if not status.get("ok"):
        print(f"[seed-cli] DB ping failed: {status.get('details')}")
        return
    print("[seed-cli] DB ping OK")
    init_db()
    print("[seed-cli] create_all completed")
    print(f"[seed-cli] minimal: {seed_minimal_data()}")
    print(f"[seed-cli] catalog: {seed_catalog_from_json()}")

if __name__ == "__main__":
    main()
