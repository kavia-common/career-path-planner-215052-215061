# Schema Sync, Seed, and API Verification

Prereqs:
- Install deps: `pip install -r requirements.txt`
- Create `.env` from `.env.example` in this directory and set a valid DATABASE_URL (Neon/Supabase Postgres).
- Optional: add JSON files to `data/` (roles.json, competencies.json, role_adjacency.json, role_competencies.json) for catalog seeding.

Steps (run from career_planner_backend directory):

1) Sync schema (idempotent)
   python -m src.cli_sync_schema
   Expected output includes:
   - [cli] db_ping: {'ok': True, ...}
   - [cli] create_all: done
   - [cli] schema_sync: ok=True executed=...
   - [cli] verify: SELECT 1 OK

2) Seed minimal and JSON catalog data (idempotent)
   python -m src.seed_cli
   Expected output includes:
   - [seed-cli] DB ping OK
   - [seed-cli] create_all completed
   - [seed-cli] minimal: {...}
   - [seed-cli] catalog: {'ok': True, 'roles': 'ins:X,upd:Y', ...}

3) Start API (choose one)
   python uvicorn_app.py
   # or: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

4) Verify endpoints (examples)
   - GET /health/db
     curl -s http://localhost:8000/health/db
     => {"ok":true,"details":"Connection successful"}

   - GET /db/users
     curl -s http://localhost:8000/db/users
     => demo users (Alice/Bob)

   - GET /db/roles
     curl -s http://localhost:8000/db/roles
     => roles (from JSON or built-in minimal seed)

   - GET /db/competencies
     curl -s http://localhost:8000/db/competencies
     => competencies (from JSON or built-in minimal seed)

Notes:
- All operations are idempotent; re-running will not duplicate data.
- If any of the GETs return empty arrays, check that seeding ran successfully and that DATABASE_URL points to the expected database.
- For Supabase-authenticated routes, supply Authorization: Bearer <jwt>. Direct DB routes under /db/* do not require Supabase.
