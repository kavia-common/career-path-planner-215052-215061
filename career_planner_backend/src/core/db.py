from __future__ import annotations

import time
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .settings import settings

# Lazy engine/session initialization so import of app doesn't fail if DB isn't ready.
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def _normalize_database_url(raw: str) -> str:
    """
    Normalize DATABASE_URL when users paste 'psql "<url>"' or wrap in quotes.
    This mirrors CLI normalization used elsewhere to keep behavior consistent.
    """
    if not raw:
        return raw
    s = raw.strip()
    if s.startswith("psql "):
        # Extract content between quotes if present
        import shlex

        parts = shlex.split(s)
        if len(parts) >= 2:
            return parts[1]
    # Strip surrounding quotes accidentally included
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def _ensure_engine() -> Optional[Engine]:
    """
    Ensure global SQLAlchemy engine exists without throwing on failure.
    Returns None if creation fails (e.g., invalid URL); logs concise error.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    try:
        db_url = _normalize_database_url(settings.DATABASE_URL)
        # Do not raise here; let connections fail gracefully via ping_db
        _engine = create_engine(db_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine
    except Exception as exc:
        # Log a clear message; app should still start
        print(f"[db] ERROR: failed to create engine: {exc.__class__.__name__}: {exc}")
        _engine = None
        _SessionLocal = None
        return None


def _get_sessionmaker() -> Optional[sessionmaker]:
    if _SessionLocal is None:
        _ensure_engine()
    return _SessionLocal


# PUBLIC_INTERFACE
def get_db() -> Generator:
    """Yield a SQLAlchemy session."""
    SessionLocal = _get_sessionmaker()
    if SessionLocal is None:
        # Yield a dummy context that raises a clear error on use
        raise RuntimeError("Database session is not available: engine not initialized or DATABASE_URL invalid")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def ping_db(max_retries: int = 0, backoff_seconds: float = 0.5) -> dict:
    """
    Ping the database and return status.
    Parameters:
      - max_retries: number of retries after the first attempt (0 = single attempt)
      - backoff_seconds: sleep between retries (exponential backoff applied)
    """
    attempt = 0
    last_error: Optional[str] = None
    while True:
        try:
            engine = _ensure_engine()
            if engine is None:
                return {"ok": False, "error": last_error or "Engine not initialized"}
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar_one()
                return {"ok": True, "result": int(result)}
        except Exception as exc:
            last_error = f"{exc.__class__.__name__}: {exc}"
            if attempt >= max_retries:
                return {"ok": False, "error": last_error}
            # Sleep with simple exponential backoff
            sleep_for = backoff_seconds * (2 ** attempt)
            print(f"[db] WARN: ping attempt {attempt+1} failed: {last_error}; retrying in {sleep_for:.2f}s")
            time.sleep(sleep_for)
            attempt += 1


# PUBLIC_INTERFACE
def init_db(retries: int = 0, backoff_seconds: float = 0.5) -> dict:
    """
    Initialize database connectivity by ensuring engine is created and accessible.
    Non-fatal: returns a dict with ok/error and does not raise.
    """
    # Ensure engine
    engine = _ensure_engine()
    if engine is None:
        return {"ok": False, "error": "Engine creation failed"}
    # Ping with retries
    status = ping_db(max_retries=retries, backoff_seconds=backoff_seconds)
    if status.get("ok"):
        return {"ok": True}
    return {"ok": False, "error": status.get("error")}


# PUBLIC_INTERFACE
def ensure_simple_users_table_and_seed() -> dict:
    """
    Ensure a simple 'demo_users' table exists and seed two baseline users (Alice/Bob).
    This should be safe to call; no-op if DB is not reachable.
    """
    engine = _ensure_engine()
    if engine is None:
        return {"ok": False, "error": "No engine"}
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS demo_users (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        email VARCHAR(100) UNIQUE
                    )
                    """
                )
            )
            # Seed Alice/Bob idempotently
            conn.execute(
                text(
                    "INSERT INTO demo_users (name, email) VALUES (:n, :e) "
                    "ON CONFLICT (email) DO NOTHING"
                ),
                [{"n": "Alice", "e": "alice@example.com"}, {"n": "Bob", "e": "bob@example.com"}],
            )
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
