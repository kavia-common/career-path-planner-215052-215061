# Backend Dev Run Instructions

This backend uses FastAPI with Pydantic v2 and pydantic-settings v2. Ensure dependencies are installed:

```bash
pip install -r requirements.txt
```

Recommended way to run (uses the provided launcher that sets up sys.path and sensible defaults):

```bash
python uvicorn_app.py
```

Notes:
- Binds to 0.0.0.0 and defaults to PORT=3001. Override with: `PORT=3002 python uvicorn_app.py`
- Launcher does not require the database to be ready; health endpoints will still load.

Alternatively, run uvicorn directly pointing to the FastAPI app inside src:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

Do NOT use:
```
uvicorn uvicorn_app:app
```
`uvicorn_app.py` contains a launcher (main) and does not export a module-level `app`.

Quick import check (no server start), useful for CI smoke tests:

```bash
python -c "import sys,os; sys.path.insert(0, os.path.abspath('career-path-planner-215052-215061/career_planner_backend')); import src.api.main as m; print('OK' if getattr(m,'app',None) else 'NO APP')"
```
