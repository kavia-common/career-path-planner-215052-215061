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

JSON catalog seeding (idempotent):
- Place the following optional files under career_planner_backend/data:
  * roles.json
  * competencies.json
  * role_adjacency.json
  * role_competencies.json
- File formats:
  * roles.json: [{ "id"?: int, "code": str, "name": str, "summary"?: str }, ...]
  * competencies.json: [{ "id"?: int, "code": str, "name": str, "category"?: str }, ...]
  * role_adjacency.json: [{ "from_role_id": int, "to_role_id": int, "weight": number }, ...]
  * role_competencies.json: [{ "role_id": int, "competency_id": int, "required_level": int }, ...]
- Missing files are skipped with a warning. Safe to run multiple times.
- Unique keys used for idempotency:
  * roles: code
  * competencies: code
  * role_adjacency: (from_role_id, to_role_id)
  * role_competencies: (role_id, competency_id)

Diagnostics:
- Console will print concise startup messages including JSON seed results, e.g.:
  [startup] JSON seed: {'ok': True, 'roles': 'ins:10,upd:0', ...}

- You can GET /health/db to verify connectivity.

Additional DB endpoints (demo):
- GET /db/users — list users from a simple demo `users` table (id, name, email)
- GET /db/users/{user_id} — fetch a single user by id
These use DATABASE_URL via SQLAlchemy and auto-create/seed two rows (Alice, Bob) idempotently on startup.
