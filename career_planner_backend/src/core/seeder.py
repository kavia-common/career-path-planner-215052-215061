"""
JSON-based data seeding utilities.

On app startup, this module loads JSON files from the 'data/' directory
(roles.json, competencies.json, role_adjacency.json, role_competencies.json)
and performs idempotent upserts into corresponding tables.

Notes:
- Uses DATABASE_URL via existing SQLAlchemy engine/session in src.core.db.
- If DATABASE_URL is missing, seeding is skipped.
- If any JSON file is missing or unreadable, skip that dataset with a warning.
- Seeding is safe to run multiple times (idempotent via unique constraints and/or merge logic).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.db import SessionLocal, engine


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")


def _load_json(file_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Load a JSON array from data/<file_name>. Returns None if file does not exist.
    """
    # Normalize data dir
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    path = os.path.join(data_dir, file_name)
    if not os.path.exists(path):
        print(f"[seed] WARN: missing {file_name}; skipping")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                return data["items"]
            if isinstance(data, list):
                return data
            print(f"[seed] WARN: {file_name} is not a JSON array; skipping")
            return None
    except Exception as e:
        print(f"[seed] WARN: failed reading {file_name}: {e}")
        return None


def _ensure_catalog_tables(db: Session) -> None:
    """
    Ensure the minimal catalog tables exist if running without migrations.
    This creates simple schemas to support seeding when using a blank database.

    Tables:
    - roles(id serial pk, code unique, name, summary)
    - competencies(id serial pk, code unique, name, category)
    - role_adjacency(from_role_id, to_role_id, weight, pk composite)
    - role_competencies(role_id, competency_id, required_level, pk composite)
    """
    # Create roles
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                code VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                summary TEXT
            )
            """
        )
    )
    # Competencies
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS competencies (
                id SERIAL PRIMARY KEY,
                code VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(128)
            )
            """
        )
    )
    # Role adjacency
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS role_adjacency (
                from_role_id INTEGER NOT NULL,
                to_role_id INTEGER NOT NULL,
                weight DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (from_role_id, to_role_id)
            )
            """
        )
    )
    # Role competencies
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS role_competencies (
                role_id INTEGER NOT NULL,
                competency_id INTEGER NOT NULL,
                required_level INTEGER NOT NULL,
                PRIMARY KEY (role_id, competency_id)
            )
            """
        )
    )


def _upsert_roles(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert roles by unique code. If 'id' present, try to preserve it (best-effort).
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    for itm in items:
        code = itm.get("code")
        name = itm.get("name")
        summary = itm.get("summary")
        if not code or not name:
            continue

        # Try update first by code
        res = db.execute(text("SELECT id, name, summary FROM roles WHERE code = :code"), {"code": code}).first()
        if res:
            # Update when fields differ
            if (res[1] != name) or (res[2] != summary):
                db.execute(
                    text("UPDATE roles SET name = :name, summary = :summary WHERE code = :code"),
                    {"name": name, "summary": summary, "code": code},
                )
                updated += 1
        else:
            # Insert new
            # If explicit id provided, try to insert with id; else default
            if "id" in itm and isinstance(itm["id"], int):
                db.execute(
                    text("INSERT INTO roles (id, code, name, summary) VALUES (:id, :code, :name, :summary) ON CONFLICT (code) DO NOTHING"),
                    {"id": itm["id"], "code": code, "name": name, "summary": summary},
                )
            else:
                db.execute(
                    text("INSERT INTO roles (code, name, summary) VALUES (:code, :name, :summary) ON CONFLICT (code) DO NOTHING"),
                    {"code": code, "name": name, "summary": summary},
                )
            inserted += 1
    return inserted, updated


def _upsert_competencies(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert competencies by unique code. Preserve id if present.
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    for itm in items:
        code = itm.get("code")
        name = itm.get("name")
        category = itm.get("category")
        if not code or not name:
            continue

        res = db.execute(text("SELECT id, name, category FROM competencies WHERE code = :code"), {"code": code}).first()
        if res:
            if (res[1] != name) or (res[2] != category):
                db.execute(
                    text("UPDATE competencies SET name = :name, category = :category WHERE code = :code"),
                    {"name": name, "category": category, "code": code},
                )
                updated += 1
        else:
            if "id" in itm and isinstance(itm["id"], int):
                db.execute(
                    text(
                        "INSERT INTO competencies (id, code, name, category) VALUES (:id, :code, :name, :category) ON CONFLICT (code) DO NOTHING"
                    ),
                    {"id": itm["id"], "code": code, "name": name, "category": category},
                )
            else:
                db.execute(
                    text("INSERT INTO competencies (code, name, category) VALUES (:code, :name, :category) ON CONFLICT (code) DO NOTHING"),
                    {"code": code, "name": name, "category": category},
                )
            inserted += 1
    return inserted, updated


def _upsert_role_adjacency(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert role adjacency edges by composite PK (from_role_id, to_role_id).
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    for itm in items:
        fr = itm.get("from_role_id")
        to = itm.get("to_role_id")
        weight = itm.get("weight")
        if fr is None or to is None or weight is None:
            continue

        res = db.execute(
            text("SELECT weight FROM role_adjacency WHERE from_role_id = :fr AND to_role_id = :to"),
            {"fr": fr, "to": to},
        ).first()
        if res:
            if float(res[0]) != float(weight):
                db.execute(
                    text("UPDATE role_adjacency SET weight = :w WHERE from_role_id = :fr AND to_role_id = :to"),
                    {"w": weight, "fr": fr, "to": to},
                )
                updated += 1
        else:
            db.execute(
                text(
                    "INSERT INTO role_adjacency (from_role_id, to_role_id, weight) VALUES (:fr, :to, :w) "
                    "ON CONFLICT (from_role_id, to_role_id) DO UPDATE SET weight = EXCLUDED.weight"
                ),
                {"fr": fr, "to": to, "w": weight},
            )
            inserted += 1
    return inserted, updated


def _upsert_role_competencies(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert role->competency requirements by composite PK (role_id, competency_id).
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    for itm in items:
        role_id = itm.get("role_id")
        competency_id = itm.get("competency_id")
        required_level = itm.get("required_level")
        if role_id is None or competency_id is None or required_level is None:
            continue

        res = db.execute(
            text(
                "SELECT required_level FROM role_competencies WHERE role_id = :r AND competency_id = :c"
            ),
            {"r": role_id, "c": competency_id},
        ).first()
        if res:
            if int(res[0]) != int(required_level):
                db.execute(
                    text(
                        "UPDATE role_competencies SET required_level = :lvl WHERE role_id = :r AND competency_id = :c"
                    ),
                    {"lvl": required_level, "r": role_id, "c": competency_id},
                )
                updated += 1
        else:
            db.execute(
                text(
                    "INSERT INTO role_competencies (role_id, competency_id, required_level) VALUES (:r, :c, :lvl) "
                    "ON CONFLICT (role_id, competency_id) DO UPDATE SET required_level = EXCLUDED.required_level"
                ),
                {"r": role_id, "c": competency_id, "lvl": required_level},
            )
            inserted += 1
    return inserted, updated


# PUBLIC_INTERFACE
def seed_catalog_from_json() -> Dict[str, Any]:
    """
    Seed roles, competencies, role adjacency, and role competencies from JSON files in data/.

    If JSON files are absent, insert a minimal demo catalog (idempotent) to enable UI exploration.
    Returns:
        dict: Summary of seeding actions taken per dataset.
    """
    if engine is None or SessionLocal is None:
        return {"ok": False, "details": "No DATABASE_URL configured; skipping seed"}

    # Load all JSON files
    roles = _load_json("roles.json")
    competencies = _load_json("competencies.json")
    adjacency = _load_json("role_adjacency.json")
    mappings = _load_json("role_competencies.json")

    summary: Dict[str, Any] = {
        "ok": True,
        "roles": "skip",
        "competencies": "skip",
        "role_adjacency": "skip",
        "role_competencies": "skip",
    }

    with SessionLocal() as db:
        # Ensure tables exist to receive data
        _ensure_catalog_tables(db)

        # If no JSON provided at all, seed a minimal built-in catalog
        if roles is None and competencies is None and adjacency is None and mappings is None:
            roles = [
                {"code": "CA", "name": "Chief Architect", "summary": "Leads enterprise architecture and guardrails."},
                {"code": "CTO", "name": "Chief Technology Officer", "summary": "Owns platform bets, DX, reliability."},
            ]
            competencies = [
                {"code": "DX", "name": "Developer Experience", "category": "Engineering"},
                {"code": "RA", "name": "Reference Architectures", "category": "Architecture"},
            ]
            adjacency = [
                {"from_role_id": 1, "to_role_id": 2, "weight": 0.9},
                {"from_role_id": 2, "to_role_id": 1, "weight": 0.7},
            ]
            mappings = [
                {"role_id": 1, "competency_id": 1, "required_level": 3},
                {"role_id": 1, "competency_id": 2, "required_level": 4},
                {"role_id": 2, "competency_id": 1, "required_level": 4},
                {"role_id": 2, "competency_id": 2, "required_level": 3},
            ]

        # Upsert in dependency-friendly order
        if roles is not None:
            ins, upd = _upsert_roles(db, roles)
            summary["roles"] = f"ins:{ins},upd:{upd}"
        if competencies is not None:
            ins, upd = _upsert_competencies(db, competencies)
            summary["competencies"] = f"ins:{ins},upd:{upd}"
        if adjacency is not None:
            ins, upd = _upsert_role_adjacency(db, adjacency)
            summary["role_adjacency"] = f"ins:{ins},upd:{upd}"
        if mappings is not None:
            ins, upd = _upsert_role_competencies(db, mappings)
            summary["role_competencies"] = f"ins:{ins},upd:{upd}"

        db.commit()

    return summary
