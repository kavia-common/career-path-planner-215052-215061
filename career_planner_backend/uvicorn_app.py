#!/usr/bin/env python3
"""
uvicorn entrypoint for the FastAPI app.

Notes:
- App import does not block on database readiness. The service will start and expose / and /health endpoints,
  while /health/ready reflects DB status.
- Configure DATABASE_URL in .env or environment.
"""
import os
import sys

def _ensure_src_on_path() -> None:
    this_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = this_dir  # contains the 'src' directory
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

def main() -> None:
    _ensure_src_on_path()
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

if __name__ == "__main__":
    main()
