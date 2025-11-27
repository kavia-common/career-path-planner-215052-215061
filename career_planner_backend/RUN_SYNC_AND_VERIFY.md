# Run schema sync, full seeding, and verify endpoints

Prereqs:
- Ensure .env has a valid DATABASE_URL (do not wrap in psql '...'; use pure URL).
- Optional: BACKEND_URL for verification (defaults to http://localhost:3001 if running locally).

Steps:
1) Schema sync:
   python -m src.cli_sync_schema

2) Full seed:
   python -m src.seed_full_cli

3) Start API (in a separate terminal):
   python uvicorn_app.py --host 0.0.0.0 --port 3001

4) Verify endpoints (examples):
   curl -s ${BACKEND_URL:-http://localhost:3001}/health/db | jq
   curl -s ${BACKEND_URL:-http://localhost:3001}/db/users | jq '.[0,1,2]'
   curl -s ${BACKEND_URL:-http://localhost:3001}/db/roles | jq '.[0,1,2]'
   curl -s ${BACKEND_URL:-http://localhost:3001}/db/competencies | jq '.[0,1,2]'
   # For adjacency, pick any role id from /db/roles
   RID=$(curl -s ${BACKEND_URL:-http://localhost:3001}/db/roles | jq '.[0].id')
   curl -s ${BACKEND_URL:-http://localhost:3001}/db/roles/$RID/adjacent | jq

Notes:
- Seeding is idempotent and can be re-run safely.
- The seed uses fallback dataset if no JSON exists in data/.
