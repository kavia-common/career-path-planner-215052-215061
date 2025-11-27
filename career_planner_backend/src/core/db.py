"""
Database module configuring SQLAlchemy engine and session using DATABASE_URL from environment.

This module exposes:
- engine: SQLAlchemy Engine created from Settings.database_url
- SessionLocal: sessionmaker for request-scoped sessions
- Base: declarative base for defining ORM models
- get_db(): FastAPI dependency yielding a session
- ping_db(): utility to verify connectivity
- init_db(): create tables if not present
- seed_minimal_data(): idempotent seed for MVP
"""
from __future__ import annotations

from typing import Generator, Optional, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.core.settings import get_settings

# Declarative base for ORM models
Base = declarative_base()

# Initialize the SQLAlchemy engine from DATABASE_URL if provided.
# Use pool_pre_ping to ensure stale connections are detected.
def _make_engine() -> Optional[Engine]:
    settings = get_settings()
    if not settings.database_url:
        return None
    # Normalize driver: prefer psycopg (psycopg3) or psycopg2
    url = settings.database_url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+psycopg" not in url and "+psycopg2" not in url:
        # default to psycopg2 driver for broad compatibility
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


def init_db() -> None:
    """
    Create database schema for all ORM models if migrations are not present.

    Safe to call on startup; no-op if tables already exist.
    Also ensures lightweight catalog tables (roles/competencies/role_adjacency/role_competencies)
    are present via ORM definitions.
    """
    if engine is None:
        return
    # Import models so they are registered with Base before create_all
    from src.models.orm import (  # noqa: F401
        User,
        CareerPlan,
        Goal,
        Role,
        Competency,
        RoleAdjacency,
        RoleCompetency,
    )

    Base.metadata.create_all(bind=engine)


def _table_empty(db: Session, table_name: str) -> bool:
    count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
    return int(count) == 0


def _exec_sql_statements(statements: List[str]) -> dict:
    """
    Execute a list of raw SQL statements sequentially against the configured engine.

    Args:
        statements: List of SQL statements to execute.

    Returns:
        dict: summary with ok flag and count executed.
    """
    if engine is None:
        return {"ok": False, "executed": 0, "details": "No DATABASE_URL configured"}
    executed = 0
    try:
        with engine.begin() as conn:
            for stmt in statements:
                if not stmt or not stmt.strip():
                    continue
                conn.execute(text(stmt))
                executed += 1
        return {"ok": True, "executed": executed}
    except Exception as e:
        return {"ok": False, "executed": executed, "details": f"{e.__class__.__name__}: {e}"}


def ensure_simple_users_table_and_seed() -> dict:
    """
    Ensure a simple 'demo_users' table (id serial, name, email unique) exists and seed sample rows.

    This is separate from the ORM User table used for Supabase profiles.
    We intentionally use a non-conflicting table name: demo_users.
    - CREATE TABLE IF NOT EXISTS demo_users ( id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE );
    - INSERT INTO demo_users (name, email) VALUES ('Alice Example','alice@example.com') ON CONFLICT (email) DO NOTHING;
    - INSERT INTO demo_users (name, email) VALUES ('Bob Example','bob@example.com') ON CONFLICT (email) DO NOTHING;

    Returns:
        dict: {ok: bool, executed: int, details?: str}
    """
    stmts = [
        "CREATE TABLE IF NOT EXISTS demo_users ( id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100) UNIQUE )",
        "INSERT INTO demo_users (name, email) VALUES ('Alice Example','alice@example.com') ON CONFLICT (email) DO NOTHING",
        "INSERT INTO demo_users (name, email) VALUES ('Bob Example','bob@example.com') ON CONFLICT (email) DO NOTHING",
    ]
    res = _exec_sql_statements(stmts)
    # concise log to stdout
    try:
        print(f"[demo_users-seed] ok={res.get('ok')} executed={res.get('executed')} details={res.get('details', '')}".strip())
    except Exception:
        pass
    return res


def seed_minimal_data() -> dict:
    """
    Idempotent seed routine that inserts minimal rows if tables are empty.

    Returns:
        dict: summary of what was seeded.
    """
    if SessionLocal is None:
        return {"seeded": False, "details": "No DATABASE_URL configured"}

    from src.models.orm import User, CareerPlan, Goal  # local import after Base

    summary: List[str] = []

    # Also ensure the simple demo users table (serial id, name, email) requested for /db/users
    users_simple = ensure_simple_users_table_and_seed()
    if users_simple.get("ok"):
        summary.append(f"demo_users(simple):{users_simple.get('executed')}")

    with SessionLocal() as db:
        # Users
        if _table_empty(db, User.__tablename__):
            demo_user = User(id="00000000-0000-0000-0000-000000000001", email="demo@example.com", full_name="Demo User", is_admin=True)
            db.add(demo_user)
            summary.append("users:1")
        # Plans
        if _table_empty(db, CareerPlan.__tablename__):
            # find or create demo user reference
            demo_user = db.get(User, "00000000-0000-0000-0000-000000000001")
            if demo_user is None:
                demo_user = User(id="00000000-0000-0000-0000-000000000001", email="demo@example.com", full_name="Demo User", is_admin=True)
                db.add(demo_user)
            plan = CareerPlan(user_id=demo_user.id, title="My First Career Plan", target_role_id=None)
            db.add(plan)
            summary.append("career_plans:1")
        # Goals
        if _table_empty(db, Goal.__tablename__):
            # attach to first plan if exists
            plan_row = db.execute(text(f"SELECT id FROM {CareerPlan.__tablename__} ORDER BY id LIMIT 1")).first()
            if plan_row:
                plan_id = plan_row[0]
                goal = Goal(plan_id=plan_id, description="Complete initial self-assessment", status="not_started")
                db.add(goal)
                summary.append("goals:1")

        db.commit()

    return {"seeded": True, "details": ", ".join(summary) if summary else "already-seeded"}
