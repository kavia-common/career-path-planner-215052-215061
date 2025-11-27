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
  * creates the initial schema (users, career_plans, goals) if missing,
  * and seeds minimal demo data idempotently (demo user, one plan, one goal).
- You can GET /health/db to verify connectivity.
