"""
Schema synchronization utility for Neon PostgreSQL.

This module inspects/ensures the following catalog tables exist with the expected shape:
- roles (id serial pk, code unique not null, name not null, summary text, indexes)
- competencies (id serial pk, code unique not null, name not null, category, indexes)
- role_competencies (role_id, competency_id, required_level, composite pk, FKs)
- role_adjacency (from_role_id, to_role_id, weight, composite pk, FKs)

It runs using DATABASE_URL from environment (via src.core.settings + src.core.db engine).
All statements are idempotent using CREATE IF NOT EXISTS and ALTERs guarded by catalog checks.

Usage:
    python -m src.core.schema_sync          # prints concise logs
"""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.core.db import engine
from src.core.db import ping_db


def _exec_batch(conn: Connection, statements: List[str]) -> Tuple[int, List[str]]:
    executed = 0
    errors: List[str] = []
    for stmt in statements:
        if not stmt or not stmt.strip():
            continue
        try:
            conn.execute(text(stmt))
            executed += 1
        except Exception as e:  # log and continue
            errors.append(f"{e.__class__.__name__}: {e}")
    return executed, errors


def _ensure_roles(conn: Connection) -> Tuple[int, List[str]]:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS roles (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            summary TEXT
        )
        """,
        # indexes
        "CREATE INDEX IF NOT EXISTS ix_roles_code ON roles(code)",
        "CREATE INDEX IF NOT EXISTS ix_roles_name ON roles(name)",
    ]
    return _exec_batch(conn, stmts)


def _ensure_competencies(conn: Connection) -> Tuple[int, List[str]]:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS competencies (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(128)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_competencies_code ON competencies(code)",
        "CREATE INDEX IF NOT EXISTS ix_competencies_name ON competencies(name)",
        "CREATE INDEX IF NOT EXISTS ix_competencies_category ON competencies(category)",
    ]
    return _exec_batch(conn, stmts)


def _ensure_role_competencies(conn: Connection) -> Tuple[int, List[str]]:
    stmts: List[str] = [
        """
        CREATE TABLE IF NOT EXISTS role_competencies (
            role_id INTEGER NOT NULL,
            competency_id INTEGER NOT NULL,
            required_level INTEGER NOT NULL,
            PRIMARY KEY (role_id, competency_id)
        )
        """,
        # Add foreign keys if missing
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'role_competencies' AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'fk_role_competencies_role'
            ) THEN
                ALTER TABLE role_competencies
                ADD CONSTRAINT fk_role_competencies_role
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'role_competencies' AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'fk_role_competencies_competency'
            ) THEN
                ALTER TABLE role_competencies
                ADD CONSTRAINT fk_role_competencies_competency
                FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """,
        # Guard required_level type as integer (if a legacy type differs)
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'role_competencies' AND column_name = 'required_level'
                  AND data_type <> 'integer'
            ) THEN
                ALTER TABLE role_competencies
                ALTER COLUMN required_level TYPE INTEGER USING required_level::integer;
            END IF;
        END
        $$;
        """,
        # Helpful index for lookups
        "CREATE INDEX IF NOT EXISTS ix_role_comp_role ON role_competencies(role_id)",
        "CREATE INDEX IF NOT EXISTS ix_role_comp_comp ON role_competencies(competency_id)",
    ]
    return _exec_batch(conn, stmts)


def _ensure_role_adjacency(conn: Connection) -> Tuple[int, List[str]]:
    stmts: List[str] = [
        """
        CREATE TABLE IF NOT EXISTS role_adjacency (
            from_role_id INTEGER NOT NULL,
            to_role_id INTEGER NOT NULL,
            weight DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (from_role_id, to_role_id)
        )
        """,
        # Add foreign keys if missing
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'role_adjacency' AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'fk_role_adjacency_from_role'
            ) THEN
                ALTER TABLE role_adjacency
                ADD CONSTRAINT fk_role_adjacency_from_role
                FOREIGN KEY (from_role_id) REFERENCES roles(id) ON DELETE CASCADE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'role_adjacency' AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'fk_role_adjacency_to_role'
            ) THEN
                ALTER TABLE role_adjacency
                ADD CONSTRAINT fk_role_adjacency_to_role
                FOREIGN KEY (to_role_id) REFERENCES roles(id) ON DELETE CASCADE;
            END IF;
        END
        $$;
        """,
        # Enforce weight type
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'role_adjacency' AND column_name = 'weight'
                  AND data_type NOT IN ('double precision', 'numeric', 'real')
            ) THEN
                ALTER TABLE role_adjacency
                ALTER COLUMN weight TYPE DOUBLE PRECISION USING weight::double precision;
            END IF;
        END
        $$;
        """,
        # Helpful indexes
        "CREATE INDEX IF NOT EXISTS ix_role_adj_from ON role_adjacency(from_role_id)",
        "CREATE INDEX IF NOT EXISTS ix_role_adj_to ON role_adjacency(to_role_id)",
        "CREATE INDEX IF NOT EXISTS ix_role_adj_weight ON role_adjacency(weight)",
    ]
    return _exec_batch(conn, stmts)


# PUBLIC_INTERFACE
def run_schema_sync() -> dict:
    """Run the schema synchronization against the configured Neon database."""
    status = ping_db()
    if not status.get("ok"):
        return {"ok": False, "executed": 0, "details": status.get("details", "DB not reachable")}

    if engine is None:
        return {"ok": False, "executed": 0, "details": "DATABASE_URL not configured"}

    total_exec = 0
    errors: List[str] = []
    per_section: List[str] = []
    with engine.begin() as conn:
        for name, ensure in (
            ("roles", _ensure_roles),
            ("competencies", _ensure_competencies),
            ("role_competencies", _ensure_role_competencies),
            ("role_adjacency", _ensure_role_adjacency),
        ):
            executed, errs = ensure(conn)
            total_exec += executed
            errors.extend(errs)
            # concise per-section log
            per_section.append(f"{name}:{executed}")

    return {"ok": len(errors) == 0, "executed": total_exec, "sections": ", ".join(per_section), "errors": errors}


def main() -> None:
    res = run_schema_sync()
    ok = res.get("ok")
    executed = res.get("executed")
    errors = res.get("errors") or []
    # concise logs
    print(f"[schema-sync] ok={ok} executed={executed}")
    if errors:
        for e in errors:
            print(f"[schema-sync] WARN: {e}")


if __name__ == "__main__":
    main()
