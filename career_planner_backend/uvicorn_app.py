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
    """
    PUBLIC_INTERFACE
    Entrypoint to start the FastAPI app with uvicorn.
    - Binds to 0.0.0.0 so containerized environments can access it.
    - Defaults to port 3001 to match project expectations; override with PORT env var.
    - Uses reload=True for dev; in production, set UVICORN_RELOAD=0 or run via a proper server command.
    """
    _ensure_src_on_path()
    import uvicorn
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
