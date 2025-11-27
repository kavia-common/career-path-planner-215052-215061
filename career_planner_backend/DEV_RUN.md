# Running the Career Planner Backend Locally

Recommended commands (run from this directory):

- Install dependencies:
  pip install -r requirements.txt

- Start the API with reload:
  python uvicorn_app.py

Alternate direct uvicorn command (ensure you are in career_planner_backend directory so `src` is importable):
  uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

If you must run from the repository root, use:
  python -m career_planner_backend.uvicorn_app

Database configuration:
- Set DATABASE_URL in your environment (see .env.example for format). Neon/Supabase Postgres URLs are supported.
- On startup, the app:
  * pings the DB,
  * creates the initial schema (users, career_plans, goals, roles, competencies, role_adjacency, role_competencies) if missing,
  * seeds minimal demo data idempotently (demo user, one plan, one goal),
  * and then attempts JSON-based catalog seeding from career_planner_backend/data (if files exist).
  * If no JSON files are present, a tiny built-in catalog is inserted (idempotent) to enable UI exploration.

Schema synchronization (Neon):
- To align Neon with the Excel-derived catalog schema without inserting data, run:
  python -m src.cli_sync_schema
  This reads DATABASE_URL and executes idempotent CREATE/ALTER statements for roles, competencies, role_competencies, and role_adjacency, printing concise logs.

Full database seed (users, roles, competencies, adjacency, mappings, plans, goals):
- Run the comprehensive seeder which will:
  * Verify DATABASE_URL,
  * run schema sync,
  * upsert from JSON files if present (see file names below),
  * otherwise insert a robust minimal dataset,
  * and verify key /db/* endpoints if BACKEND URL env is provided.
  
  Command:
    python -m src.seed_full_cli

JSON seed files (all optional; place under career_planner_backend/data):
  * roles.json                  # [{ "id"?: int, "code": str, "name": str, "summary"?: str }, ...]
  * competencies.json           # [{ "id"?: int, "code": str, "name": str, "category"?: str }, ...]
  * role_adjacency.json         # [{ "from_role_id": int, "to_role_id": int, "weight": number }, ...]
  * role_competencies.json      # [{ "role_id": int, "competency_id": int, "required_level": int }, ...]
  * users.json                  # [{ "name": str, "email": str }, ...]   # for simple /db/users table
  * plans.json                  # [{ "user_id": str, "title": str, "target_role_id"?: int }, ...]
  * goals.json                  # [{ "plan_id": int, "description": str, "status"?: str }, ...]

- Missing files are skipped with a warning. Safe to run multiple times.
- Unique keys used for idempotency:
  * roles: code
  * competencies: code
  * role_adjacency: (from_role_id, to_role_id)
  * role_competencies: (role_id, competency_id)
  * users(simple): email
  * plans: (user_id, title)
  * goals: (plan_id, description)

Diagnostics:
- Console will print concise messages, e.g.:
  [seed-full] seed summary: {"mode":"json","roles":"ins:10,upd:0", ...}

- You can GET /health/db to verify connectivity.

Additional DB endpoints (demo):
- GET /db/users — list users from a simple demo `users` table (id, name, email)
- GET /db/users/{user_id} — fetch a single user by id
These use DATABASE_URL via SQLAlchemy and auto-create/seed two rows (Alice, Bob) idempotently on startup. The full seeder can add more demo users via users.json.
