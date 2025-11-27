# Environment Variables for career_planner_backend

Required for database connectivity:
- DATABASE_URL: Full SQLAlchemy DSN, e.g. postgresql+psycopg2://user:password@career_planner_database:5432/dbname

Optional legacy fallbacks (used only if DATABASE_URL is absent):
- POSTGRES_HOST (default: None)
- POSTGRES_PORT (default: 5432)
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD
- POSTGRES_SSLMODE (e.g., require|disable)

Server bind:
- HOST (default: 0.0.0.0)
- PORT (default: 8000; uvicorn_app.py uses 3001 if unset)

CORS:
- BACKEND_CORS_ORIGINS: Comma-separated list of full URLs (e.g., https://app.example.com,https://localhost:3000)

Notes:
- In multi-container setup, use the database service name in the host part (career_planner_database).
- Health endpoints: / (liveness), /health/db (db ping), /health/ready (readiness).
