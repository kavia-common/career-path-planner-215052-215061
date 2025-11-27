# Backend Dev Notes

- Pydantic v2 is required. Settings use `from pydantic_settings import BaseSettings`.
- Ensure Python deps are installed:

  pip install -r requirements.txt

- Quick import check (no server start):

  python -c "import sys,os; sys.path.insert(0, os.path.abspath('career-path-planner-215052-215061/career_planner_backend')); import src.api.main as m; print('OK' if getattr(m,'app',None) else 'NO APP')"

If import fails due to missing packages, install dependencies first.
