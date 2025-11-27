"""
Database module configuring SQLAlchemy engine and session using DATABASE_URL from environment.

This module exposes:
- engine: SQLAlchemy Engine created from Settings.database_url
- SessionLocal: sessionmaker for request-scoped sessions
- Base: declarative base for defining ORM models (future expansion)
- get_db(): FastAPI dependency yielding a session
- ping_db(): utility to verify connectivity
"""

from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from src.core.settings import get_settings

# Declarative base for future ORM models
Base = declarative_base()

# Initialize the SQLAlchemy engine from DATABASE_URL if provided.
# Use pool_pre_ping to ensure stale connections are detected.
def _make_engine() -> Optional[Engine]:
    settings = get_settings()
    if not settings.database_url:
        return None
    # Normalize driver: if user passed postgres://, SQLAlchemy recommends postgresql+psycopg
    url = settings.database_url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        # default to psycopg2 driver for compatibility
        url = "postgresql+psycopg2://" + url[len("postgresql://") :]

    engine = create_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )
    return engine


engine: Optional[Engine] = _make_engine()

# Session factory (only if engine is configured)
SessionLocal: Optional[sessionmaker] = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True) if engine else None
)


# PUBLIC_INTERFACE
def get_db() -> Generator:
    """Yield a SQLAlchemy session if DATABASE_URL is configured; otherwise raises RuntimeError."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured; database session is unavailable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def ping_db() -> dict:
    """
    Pings the database to verify connectivity.

    Returns:
        dict: {"ok": bool, "details": str}
    """
    if engine is None:
        return {"ok": False, "details": "DATABASE_URL not configured"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "details": "Connection successful"}
    except OperationalError as e:
        return {"ok": False, "details": f"OperationalError: {e.__class__.__name__}: {e}"}
    except Exception as e:  # defensive
        return {"ok": False, "details": f"{e.__class__.__name__}: {e}"}
