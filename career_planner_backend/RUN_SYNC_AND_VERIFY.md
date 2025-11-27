# Schema Sync, Seed, and API Verification

Prereqs:
- Install deps: `pip install -r requirements.txt`
- Create `.env` from `.env.example` in this directory and set a valid DATABASE_URL (Neon/Supabase Postgres).
- Optional: add JSON files to `data/` (roles.json, competencies.json, role_adjacency.json, role_competencies.json, users.json, plans.json, goals.json) for catalog seeding.

Steps (run from career_planner_backend directory):

1) Sync schema (idempotent)
   python -m src.cli_sync_schema
   Expected output includes:
   - [cli] db_ping: {'ok': True, ...}
   - [cli] create_all: done
   - [cli] schema_sync: ok=True executed=...
   - [cli] verify: SELECT 1 OK

2) Seed complete dataset (idempotent; JSON-first, fallback dataset otherwise)
   python -m src.seed_full_cli
   Expected output includes:
   - [seed-full] schema_sync: ok=True executed=...
   - [seed-full] skipped_files: ... (if any JSON files are missing)
   - [seed-full] seed summary: {"mode":"json|fallback","roles":"ins:X,upd:Y", "competencies":"...", "role_adjacency":"...", "role_competencies":"...", "users(simple)":"...", "career_plans":"...", "goals":"..."}
   - [seed-full] verify: {"\/db\/users":{"status":200,"count":...}, ...}

   Alternative minimal seed:
   python -m src.seed_cli

3) Start API (choose one)
   python uvicorn_app.py
   # or: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

4) Verify endpoints (examples)
   - GET /health/db
     curl -s http://localhost:8000/health/db
     => {"ok":true,"details":"Connection successful"}

   - GET /db/users
     curl -s http://localhost:8000/db/users
     => seeded users

   - GET /db/roles
     curl -s http://localhost:8000/db/roles
     => roles (from JSON or fallback dataset)

   - GET /db/competencies
     curl -s http://localhost:8000/db/competencies
     => competencies (from JSON or fallback dataset)

   - GET /db/roles/{id}/adjacent
     curl -s http://localhost:8000/db/roles/1/adjacent

Notes:
- All operations are idempotent; re-running will not duplicate data.
- If any of the GETs return empty arrays, ensure seeding ran successfully and that DATABASE_URL points to the expected database.
- For Supabase-authenticated routes, supply Authorization: Bearer <jwt>. Direct DB routes under /db/* do not require Supabase.
