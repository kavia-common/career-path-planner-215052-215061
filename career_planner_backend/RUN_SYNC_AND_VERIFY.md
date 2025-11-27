# Sync and Verify

- Ensure `.env` contains DATABASE_URL (PostgreSQL).
- Run: `python -m src.cli_sync_schema`
- Quick check: start server and call `/health/ready` to confirm DB connectivity.
- Verify endpoints: `python -m src.verify_endpoints`
