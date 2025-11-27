from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .settings import settings

# Create SQLAlchemy engine using DATABASE_URL
engine: Engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# PUBLIC_INTERFACE
def get_db() -> Generator:
    """Yield a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def ping_db() -> dict:
    """Ping the database and return basic status info."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar_one()
            return {"ok": True, "result": int(result)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
