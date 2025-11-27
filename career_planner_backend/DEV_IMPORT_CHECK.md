Run a quick import check (no server start) to verify FastAPI app imports without errors.

Example:
  python -c "import sys,os; sys.path.insert(0, os.path.abspath('career-path-planner-215052-215061/career_planner_backend')); import src.api.main as m; print('OK' if getattr(m,'app',None) else 'NO APP')"
