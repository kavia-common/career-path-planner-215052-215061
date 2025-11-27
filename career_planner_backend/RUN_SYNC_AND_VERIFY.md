# Sync and Verify

- Ensure `.env` contains DATABASE_URL (PostgreSQL).
- Run: `python -m src.cli_sync_schema`
- Verify endpoints: `python -m src.verify_endpoints`
