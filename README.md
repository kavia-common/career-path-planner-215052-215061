# career-path-planner-215052-215061

Backend setup notes:
- Configure DATABASE_URL via environment or .env file inside career_planner_backend (see .env.example).
  - Paste only the actual Postgres URL. If you accidentally paste `psql "<url>"` the backend normalizes it automatically.
- Optional CORS origins: set CORS_ORIGINS (comma-separated) e.g., http://localhost:3000,http://127.0.0.1:3000. Defaults to "*" for development.
- Health endpoints:
  * GET /                 -> {"status":"ok","service":"alive"} (liveness; never hits DB)
  * GET /health/ready     -> {"status":"ready|not_ready","db": {...}} (readiness including DB ping)
  * GET /health/db        -> database connectivity status only
- The FastAPI backend starts even if the database is not ready. DB-backed routes will return errors until the DB becomes reachable; the health endpoints allow orchestration to wait for readiness.
- The backend will auto-create a minimal schema (including roles/competencies/adjacency/mappings) and seed demo data when seeding CLIs are run and the DB is reachable.
- Optional: Place JSON files under career_planner_backend/data (roles.json, competencies.json, role_adjacency.json, role_competencies.json, users.json, plans.json, goals.json) to seed the catalog on startup or via the full seeding CLI. Seeding is idempotent and missing files are skipped with warnings.
- Optional direct-DB endpoints (if Supabase REST is not configured): GET /db/roles, /db/competencies, /db/roles/{id}/adjacent
- Simple users endpoints (direct DB): GET /db/users, /db/users/{id}. A minimal `demo_users` table (id serial, name, email unique) can be ensured and seeded (Alice/Bob) idempotently using DATABASE_URL to avoid conflict with auth/users tables.
- CLI seeding:
  * Minimal seed (users table + minimal catalog): `python -m src.seed_cli`
  * Full seed (users, roles, competencies, role mappings, adjacency, plans, goals; JSON-first with fallback): `python -m src.seed_full_cli`

Neon schema synchronization:
- Run the idempotent schema sync to align Neon with the required catalog schema derived from Roles, Competencies, Role-Competency mapping, and Role Adjacency.
- Command (run from career_planner_backend directory): `python -m src.cli_sync_schema`
- Behavior:
  * Reads DATABASE_URL from environment. If missing, prints a clear error and exits.
  * Executes CREATE TABLE IF NOT EXISTS and guarded ALTER TABLE statements across: roles, competencies, role_competencies, role_adjacency.
  * Emits concise logs including per-section executed counts and any warnings.
  * After sync, verifies connectivity with a quick `SELECT 1` and prints the result.