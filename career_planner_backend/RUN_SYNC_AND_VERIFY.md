# Backend run, DB connectivity, and readiness

This backend uses PostgreSQL via SQLAlchemy (psycopg2). It will start even if the DB is not yet ready, and exposes health endpoints:

- GET /            -> liveness (no DB required)
- GET /health/db   -> DB ping result
- GET /health/ready-> readiness (includes DB ping)

ENV configuration:
- Prefer DATABASE_URL (e.g., postgresql+psycopg2://user:pass@career_planner_database:5432/db)
- If DATABASE_URL is not present, legacy POSTGRES_* vars will be used to construct one.

Service name:
- In containerized environments, ensure the host in the URL is the service name `career_planner_database` so networking resolves across containers.

Local dev quick start:
1) Install deps: pip install -r requirements.txt
2) Copy .env.example to .env and set real values
3) Start: python uvicorn_app.py
4) Check health: curl http://localhost:3001/ ; curl http://localhost:3001/health/db

Readiness / retry:
- On startup the app tries a brief, non-blocking DB init (2 retries with short backoff). It won't prevent the app from starting.
- Probes should use /health/ready to gate traffic when DB is still initializing.
