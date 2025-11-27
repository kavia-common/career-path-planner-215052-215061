# Dev run

1. Create a `.env` file using `.env.example`. Ensure DATABASE_URL is set to your PostgreSQL instance.
2. Start the API with `python uvicorn_app.py`
3. Health:
   - Liveness: `GET /` should return `{"status":"ok","service":"alive"}` even if DB is down.
   - Readiness: `GET /health/ready` returns DB status and overall readiness.
   - DB only: `GET /health/db`.
4. Open docs at `/docs`
