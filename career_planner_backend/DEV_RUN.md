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
