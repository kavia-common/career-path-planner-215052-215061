#!/usr/bin/env python3
"""
Convenience launcher for running the FastAPI app under uvicorn with a stable import path.

Usage:
    python uvicorn_app.py
    or
    python -m career_planner_backend.uvicorn_app

This sets sys.path so that `src` is importable and runs:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys

def _ensure_src_on_path() -> None:
    """
    Ensure the backend's root directory (containing the `src` package) is on sys.path,
    regardless of where this script is invoked from.
    """
    this_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = this_dir  # contains the 'src' directory
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

def main() -> None:
    """
    Boot uvicorn with the FastAPI app.
    """
    _ensure_src_on_path()
    try:
        import uvicorn
    except Exception as e:
        # Provide a helpful error if uvicorn is missing
        sys.stderr.write(f"Failed to import uvicorn: {e}\n")
        sys.stderr.write("Ensure dependencies are installed from requirements.txt\n")
        sys.exit(1)

    # The FastAPI app is defined at src/api/main.py as variable `app`
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

if __name__ == "__main__":
    main()
