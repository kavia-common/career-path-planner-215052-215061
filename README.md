# career-path-planner-215052-215061

Backend setup notes:
- Configure DATABASE_URL via environment or .env file inside career_planner_backend (see .env.example).
- The FastAPI backend will auto-create a minimal schema (including roles/competencies/adjacency/mappings) and seed demo data on first start.
- Optional: Place JSON files under career_planner_backend/data (roles.json, competencies.json, role_adjacency.json, role_competencies.json) to seed the catalog on startup. Seeding is idempotent and missing files are skipped with warnings.
- Optional direct-DB endpoints (if Supabase REST is not configured): GET /db/roles, /db/competencies, /db/roles/{id}/adjacent
- CLI seeding: from career_planner_backend run `python -m src.seed_cli` to force init/seed using DATABASE_URL.