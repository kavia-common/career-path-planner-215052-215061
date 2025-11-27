#!/usr/bin/env python3
"""
Seed Neon PostgreSQL with realistic data for Users, Roles, Competencies, Role-Competency mappings,
Role Adjacency, Plans, and Goals based on JSON files (if present) or a robust minimal dataset.

Behavior:
1) Ensure DATABASE_URL is read from env; if missing, return a clear error (no code changes required).
2) Run schema sync to ensure tables exist: python -m src.cli_sync_schema
3) Seed data:
   - If JSON files exist under career_planner_backend/data (roles.json, competencies.json,
     role_adjacency.json, role_competencies.json, users.json, plans.json, goals.json),
     run idempotent upserts using unique keys.
   - Otherwise, insert a robust minimal dataset.
4) Verify endpoints used by the frontend:
   GET /db/users, /db/roles, /db/competencies, /db/roles/{id}/adjacent, and plans/goals if possible.
5) Print concise summary of seed counts and any skipped files.

Notes:
- No credentials are hardcoded; only DATABASE_URL from env is used.
- Idempotent: safe to run multiple times.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.db import engine, SessionLocal, ping_db, init_db, ensure_simple_users_table_and_seed
from src.core.schema_sync import run_schema_sync


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def _load_json_list(name: str) -> Optional[List[Dict[str, Any]]]:
    """Load an optional JSON array from data/<name>. None if missing or invalid."""
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                return data["items"]
            print(f"[seed-full] WARN: {name} is not a JSON array; skipping")
            return None
    except Exception as e:
        print(f"[seed-full] WARN: failed reading {name}: {e}")
        return None


def _ensure_catalog_tables(db: Session) -> None:
    """Ensure minimal catalog tables exist (raw SQL to allow seeding on blank DB)."""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS roles (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            summary TEXT
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS competencies (
            id SERIAL PRIMARY KEY,
            code VARCHAR(64) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(128)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS role_competencies (
            role_id INTEGER NOT NULL,
            competency_id INTEGER NOT NULL,
            required_level INTEGER NOT NULL,
            PRIMARY KEY (role_id, competency_id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS role_adjacency (
            from_role_id INTEGER NOT NULL,
            to_role_id INTEGER NOT NULL,
            weight DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (from_role_id, to_role_id)
        )
    """))
    # Plans & goals for DB seed verification (align with ORM tables names)
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS career_plans (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(64) NOT NULL,
            title VARCHAR(255) NOT NULL,
            target_role_id INTEGER NULL
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            plan_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(64) NULL
        )
    """))


def _upsert_roles(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    inserted = 0
    updated = 0
    for it in items:
        code = it.get("code")
        name = it.get("name")
        summary = it.get("summary")
        if not code or not name:
            continue
        row = db.execute(text("SELECT id,name,summary FROM roles WHERE code=:code"), {"code": code}).first()
        if row:
            if row[1] != name or row[2] != summary:
                db.execute(text("UPDATE roles SET name=:name, summary=:summary WHERE code=:code"),
                           {"name": name, "summary": summary, "code": code})
                updated += 1
        else:
            if "id" in it and isinstance(it["id"], int):
                db.execute(text(
                    "INSERT INTO roles (id, code, name, summary) VALUES (:id,:code,:name,:summary) "
                    "ON CONFLICT (code) DO NOTHING"
                ), {"id": it["id"], "code": code, "name": name, "summary": summary})
            else:
                db.execute(text(
                    "INSERT INTO roles (code, name, summary) VALUES (:code,:name,:summary) "
                    "ON CONFLICT (code) DO NOTHING"
                ), {"code": code, "name": name, "summary": summary})
            inserted += 1
    return inserted, updated


def _upsert_competencies(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    inserted = 0
    updated = 0
    for it in items:
        code = it.get("code")
        name = it.get("name")
        category = it.get("category")
        if not code or not name:
            continue
        row = db.execute(text("SELECT id,name,category FROM competencies WHERE code=:code"), {"code": code}).first()
        if row:
            if row[1] != name or row[2] != category:
                db.execute(text("UPDATE competencies SET name=:name, category=:category WHERE code=:code"),
                           {"name": name, "category": category, "code": code})
                updated += 1
        else:
            if "id" in it and isinstance(it["id"], int):
                db.execute(text(
                    "INSERT INTO competencies (id, code, name, category) VALUES (:id,:code,:name,:category) "
                    "ON CONFLICT (code) DO NOTHING"
                ), {"id": it["id"], "code": code, "name": name, "category": category})
            else:
                db.execute(text(
                    "INSERT INTO competencies (code, name, category) VALUES (:code,:name,:category) "
                    "ON CONFLICT (code) DO NOTHING"
                ), {"code": code, "name": name, "category": category})
            inserted += 1
    return inserted, updated


def _upsert_role_competencies(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    ins = 0
    upd = 0
    for it in items:
        r = it.get("role_id")
        c = it.get("competency_id")
        lvl = it.get("required_level")
        if r is None or c is None or lvl is None:
            continue
        row = db.execute(text(
            "SELECT required_level FROM role_competencies WHERE role_id=:r AND competency_id=:c"
        ), {"r": r, "c": c}).first()
        if row:
            if int(row[0]) != int(lvl):
                db.execute(text(
                    "UPDATE role_competencies SET required_level=:lvl WHERE role_id=:r AND competency_id=:c"
                ), {"lvl": int(lvl), "r": r, "c": c})
                upd += 1
        else:
            db.execute(text(
                "INSERT INTO role_competencies (role_id, competency_id, required_level) VALUES (:r,:c,:lvl) "
                "ON CONFLICT (role_id,competency_id) DO UPDATE SET required_level=EXCLUDED.required_level"
            ), {"r": r, "c": c, "lvl": int(lvl)})
            ins += 1
    return ins, upd


def _upsert_role_adjacency(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    ins = 0
    upd = 0
    for it in items:
        fr = it.get("from_role_id")
        to = it.get("to_role_id")
        w = it.get("weight")
        if fr is None or to is None or w is None:
            continue
        row = db.execute(text(
            "SELECT weight FROM role_adjacency WHERE from_role_id=:fr AND to_role_id=:to"
        ), {"fr": fr, "to": to}).first()
        if row:
            if float(row[0]) != float(w):
                db.execute(text(
                    "UPDATE role_adjacency SET weight=:w WHERE from_role_id=:fr AND to_role_id=:to"
                ), {"w": float(w), "fr": fr, "to": to})
                upd += 1
        else:
            db.execute(text(
                "INSERT INTO role_adjacency (from_role_id, to_role_id, weight) VALUES (:fr,:to,:w) "
                "ON CONFLICT (from_role_id,to_role_id) DO UPDATE SET weight=EXCLUDED.weight"
            ), {"fr": fr, "to": to, "w": float(w)})
            ins += 1
    return ins, upd


def _upsert_simple_users(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert into simple users table (serial id, name, email unique) for /db/users.
    JSON format: [{ "name": "...", "email": "..." }, ...]
    """
    ins = 0
    upd = 0
    # Make sure table exists
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE
        )
    """))
    for it in items:
        email = it.get("email")
        name = it.get("name")
        if not email:
            continue
        row = db.execute(text("SELECT name FROM users WHERE email=:e"), {"e": email}).first()
        if row:
            if row[0] != name:
                db.execute(text("UPDATE users SET name=:n WHERE email=:e"), {"n": name, "e": email})
                upd += 1
        else:
            db.execute(text(
                "INSERT INTO users (name, email) VALUES (:n,:e) ON CONFLICT (email) DO NOTHING"
            ), {"n": name, "e": email})
            ins += 1
    return ins, upd


def _upsert_plans(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert plans: unique key (user_id, title) to avoid duplicates.
    JSON: [{ "user_id": "uuid-or-string", "title": "Plan Title", "target_role_id": 1 }, ...]
    """
    ins = 0
    upd = 0
    for it in items:
        user_id = it.get("user_id")
        title = it.get("title")
        target_role_id = it.get("target_role_id")
        if not user_id or not title:
            continue
        row = db.execute(text(
            "SELECT id,target_role_id FROM career_plans WHERE user_id=:u AND title=:t"
        ), {"u": user_id, "t": title}).first()
        if row:
            if (row[1] != target_role_id):
                db.execute(text(
                    "UPDATE career_plans SET target_role_id=:tr WHERE id=:id"
                ), {"tr": target_role_id, "id": row[0]})
                upd += 1
        else:
            db.execute(text(
                "INSERT INTO career_plans (user_id, title, target_role_id) VALUES (:u,:t,:tr)"
            ), {"u": user_id, "t": title, "tr": target_role_id})
            ins += 1
    return ins, upd


def _upsert_goals(db: Session, items: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Upsert goals: dedupe by (plan_id, description).
    JSON: [{ "plan_id": 1, "description": "Goal", "status": "not_started" }, ...]
    """
    ins = 0
    upd = 0
    for it in items:
        plan_id = it.get("plan_id")
        description = it.get("description")
        status = it.get("status")
        if not plan_id or not description:
            continue
        row = db.execute(text(
            "SELECT id,status FROM goals WHERE plan_id=:p AND description=:d"
        ), {"p": plan_id, "d": description}).first()
        if row:
            if row[1] != status:
                db.execute(text("UPDATE goals SET status=:s WHERE id=:id"), {"s": status, "id": row[0]})
                upd += 1
        else:
            db.execute(text(
                "INSERT INTO goals (plan_id, description, status) VALUES (:p,:d,:s)"
            ), {"p": plan_id, "d": description, "s": status})
            ins += 1
    return ins, upd


def _fallback_dataset() -> Dict[str, List[Dict[str, Any]]]:
    """
    Provide a robust minimal dataset with:
    - 3 demo users for simple users table
    - ~10 roles, ~10-15 competencies
    - adjacency links among several roles
    - a few mappings
    - plans and goals for two users
    """
    roles = [
        {"code": "CA", "name": "Chief Architect", "summary": "Leads enterprise architecture and guardrails."},
        {"code": "CTO", "name": "Chief Technology Officer", "summary": "Owns platform bets and developer productivity."},
        {"code": "CIO", "name": "Chief Information Officer", "summary": "Owns IT portfolio and operations."},
        {"code": "CDAO", "name": "Chief Data & Analytics Officer", "summary": "Owns data products and analytics outcomes."},
        {"code": "CInO", "name": "Chief Innovation Officer", "summary": "Explores and incubates future bets."},
        {"code": "CPTO", "name": "Chief Product & Technology Officer", "summary": "Unifies product and platform execution."},
        {"code": "CTrO", "name": "Chief Transformation Officer", "summary": "Drives modernization and simplification."},
        {"code": "Infra", "name": "Head of Infrastructure", "summary": "Runs core infra and reliability posture."},
        {"code": "AppDev", "name": "Head of Application Development", "summary": "Leads app delivery and DX."},
        {"code": "DigProd", "name": "Head of Digital Product", "summary": "Leads product mgmt and UX outcomes."},
    ]
    competencies = [
        {"code": "DX", "name": "Developer Experience", "category": "Engineering"},
        {"code": "RA", "name": "Reference Architectures", "category": "Architecture"},
        {"code": "ST", "name": "Standards Lifecycle", "category": "Architecture"},
        {"code": "RM", "name": "Risk-by-Design", "category": "Reliability"},
        {"code": "MOD", "name": "Modernization", "category": "Architecture"},
        {"code": "AI", "name": "AI Model Risk Mgmt", "category": "AI"},
        {"code": "FIN", "name": "FinOps/Chargeback", "category": "Portfolio"},
        {"code": "ORG", "name": "Org & Talent Systems", "category": "Leadership"},
        {"code": "EXT", "name": "External Ecosystem Signaling", "category": "Leadership"},
        {"code": "STORY", "name": "Executive Storytelling", "category": "Leadership"},
        {"code": "REL", "name": "Reliability/SLOs", "category": "Reliability"},
        {"code": "SEC", "name": "Security by Design", "category": "Security"},
        {"code": "DATA", "name": "Data Product Thinking", "category": "Data"},
        {"code": "PORT", "name": "Portfolio Capital Allocation", "category": "Portfolio"},
    ]
    # Adjacency will reference numeric ids after insert; fallback uses first 6 roles assuming IDs start at 1
    adjacency = [
        {"from_role_id": 1, "to_role_id": 2, "weight": 0.9},
        {"from_role_id": 1, "to_role_id": 6, "weight": 0.7},
        {"from_role_id": 2, "to_role_id": 1, "weight": 0.7},
        {"from_role_id": 2, "to_role_id": 9, "weight": 0.6},
        {"from_role_id": 3, "to_role_id": 1, "weight": 0.5},
        {"from_role_id": 4, "to_role_id": 2, "weight": 0.5},
        {"from_role_id": 5, "to_role_id": 2, "weight": 0.4},
        {"from_role_id": 9, "to_role_id": 2, "weight": 0.6},
    ]
    # A handful of mappings (assumes first few ids)
    mappings = [
        {"role_id": 1, "competency_id": 1, "required_level": 4},   # CA needs DX 4
        {"role_id": 1, "competency_id": 2, "required_level": 4},   # RA 4
        {"role_id": 1, "competency_id": 3, "required_level": 4},   # ST 4
        {"role_id": 2, "competency_id": 1, "required_level": 4},   # CTO DX 4
        {"role_id": 2, "competency_id": 6, "required_level": 3},   # AI risk 3
        {"role_id": 2, "competency_id": 7, "required_level": 3},   # FinOps 3
        {"role_id": 2, "competency_id": 8, "required_level": 3},   # Org/Talent 3
        {"role_id": 2, "competency_id": 10, "required_level": 3},  # Storytelling 3
        {"role_id": 3, "competency_id": 7, "required_level": 3},   # CIO FinOps 3
        {"role_id": 9, "competency_id": 1, "required_level": 3},   # AppDev DX 3
    ]
    simple_users = [
        {"name": "Alice Example", "email": "alice@example.com"},
        {"name": "Bob Example", "email": "bob@example.com"},
        {"name": "Carol Example", "email": "carol@example.com"},
    ]
    # Plans associated with two pseudo user_ids for demonstration (string ids)
    plans = [
        {"user_id": "00000000-0000-0000-0000-000000000001", "title": "CTO Readiness Plan", "target_role_id": 2},
        {"user_id": "00000000-0000-0000-0000-000000000002", "title": "Architecture Excellence Plan", "target_role_id": 1},
    ]
    # Goals referencing plan ids; we cannot know ids prior; seed by plan title after insert in code path
    goals = [
        {"plan_title": "CTO Readiness Plan", "description": "Publish first golden path", "status": "in_progress"},
        {"plan_title": "CTO Readiness Plan", "description": "Stand up DX telemetry", "status": "not_started"},
        {"plan_title": "Architecture Excellence Plan", "description": "Ship standards catalog v1", "status": "not_started"},
    ]
    return {
        "roles": roles,
        "competencies": competencies,
        "role_adjacency": adjacency,
        "role_competencies": mappings,
        "simple_users": simple_users,
        "plans": plans,
        "goals_by_title": goals,
    }


def _attach_goals_by_title(db: Session, goals_by_title: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Attach goals by resolving plan_id from plan title (used by fallback dataset).
    """
    ins = 0
    upd = 0
    for g in goals_by_title:
        title = g.get("plan_title")
        description = g.get("description")
        status = g.get("status")
        if not title or not description:
            continue
        row = db.execute(text("SELECT id FROM career_plans WHERE title=:t ORDER BY id LIMIT 1"), {"t": title}).first()
        if not row:
            continue
        plan_id = row[0]
        i, u = _upsert_goals(db, [{"plan_id": plan_id, "description": description, "status": status}])
        ins += i
        upd += u
    return ins, upd


def seed_full() -> Dict[str, Any]:
    """
    Execute full seed flow and return a summary dict.
    """
    # 1) Check DB connectivity
    status = ping_db()
    if not status.get("ok"):
        return {
            "ok": False,
            "details": f"DATABASE_URL missing or unreachable: {status.get('details')}",
        }

    # 2) Ensure ORM tables and run schema sync
    init_db()
    sync = run_schema_sync()

    if engine is None or SessionLocal is None:
        return {"ok": False, "details": "No DATABASE_URL configured"}

    summary: Dict[str, Any] = {
        "ok": True,
        "schema_sync": {"ok": sync.get("ok"), "executed": sync.get("executed"), "sections": sync.get("sections")},
        "seed": {},
        "verify": {},
        "skipped_files": [],
    }

    # 3) Seed data (JSON first, else fallback)
    roles = _load_json_list("roles.json")
    competencies = _load_json_list("competencies.json")
    adjacency = _load_json_list("role_adjacency.json")
    mappings = _load_json_list("role_competencies.json")
    users_simple = _load_json_list("users.json")
    plans = _load_json_list("plans.json")
    goals = _load_json_list("goals.json")

    use_fallback = all(x is None for x in [roles, competencies, adjacency, mappings, users_simple, plans, goals])

    with SessionLocal() as db:
        # Minimal table existence
        _ensure_catalog_tables(db)

        # Ensure simple users demo table and seed Alice/Bob baseline
        ensure_simple_users_table_and_seed()

        if use_fallback:
            ds = _fallback_dataset()
            r_ins, r_upd = _upsert_roles(db, ds["roles"])
            c_ins, c_upd = _upsert_competencies(db, ds["competencies"])
            a_ins, a_upd = _upsert_role_adjacency(db, ds["role_adjacency"])
            m_ins, m_upd = _upsert_role_competencies(db, ds["role_competencies"])
            su_ins, su_upd = _upsert_simple_users(db, ds["simple_users"])
            p_ins, p_upd = _upsert_plans(db, ds["plans"])
            gti, gtu = _attach_goals_by_title(db, ds["goals_by_title"])

            summary["seed"] = {
                "mode": "fallback",
                "roles": f"ins:{r_ins},upd:{r_upd}",
                "competencies": f"ins:{c_ins},upd:{c_upd}",
                "role_adjacency": f"ins:{a_ins},upd:{a_upd}",
                "role_competencies": f"ins:{m_ins},upd:{m_upd}",
                "users(simple)": f"ins:{su_ins},upd:{su_upd}",
                "career_plans": f"ins:{p_ins},upd:{p_upd}",
                "goals": f"ins:{gti},upd:{gtu}",
            }
        else:
            # JSON-based idempotent upserts (skip missing files)
            if roles is None:
                summary["skipped_files"].append("roles.json")
            if competencies is None:
                summary["skipped_files"].append("competencies.json")
            if adjacency is None:
                summary["skipped_files"].append("role_adjacency.json")
            if mappings is None:
                summary["skipped_files"].append("role_competencies.json")
            if users_simple is None:
                summary["skipped_files"].append("users.json")
            if plans is None:
                summary["skipped_files"].append("plans.json")
            if goals is None:
                summary["skipped_files"].append("goals.json")

            r_ins, r_upd = _upsert_roles(db, roles or [])
            c_ins, c_upd = _upsert_competencies(db, competencies or [])
            a_ins, a_upd = _upsert_role_adjacency(db, adjacency or [])
            m_ins, m_upd = _upsert_role_competencies(db, mappings or [])
            su_ins, su_upd = _upsert_simple_users(db, users_simple or [])
            p_ins, p_upd = _upsert_plans(db, plans or [])
            g_ins, g_upd = _upsert_goals(db, goals or [])

            summary["seed"] = {
                "mode": "json",
                "roles": f"ins:{r_ins},upd:{r_upd}",
                "competencies": f"ins:{c_ins},upd:{c_upd}",
                "role_adjacency": f"ins:{a_ins},upd:{a_upd}",
                "role_competencies": f"ins:{m_ins},upd:{m_upd}",
                "users(simple)": f"ins:{su_ins},upd:{su_upd}",
                "career_plans": f"ins:{p_ins},upd:{p_upd}",
                "goals": f"ins:{g_ins},upd:{g_upd}",
            }

        db.commit()

    # 4) Verify endpoints used by frontend
    # We cannot guarantee the server is running here; attempt HTTP GETs if env provides BACKEND URL, else skip.
    backend_url = os.getenv("REACT_APP_BACKEND_URL") or os.getenv("REACT_APP_API_BASE") or os.getenv("BACKEND_URL")
    verification: Dict[str, Any] = {}
    if backend_url:
        try:
            base = backend_url.rstrip("/")
            with httpx.Client(timeout=10.0) as client:
                r_users = client.get(f"{base}/db/users")
                verification["/db/users"] = {"status": r_users.status_code, "count": len(r_users.json()) if r_users.status_code == 200 else 0}
                r_roles = client.get(f"{base}/db/roles")
                verification["/db/roles"] = {"status": r_roles.status_code, "count": len(r_roles.json()) if r_roles.status_code == 200 else 0}
                r_comp = client.get(f"{base}/db/competencies")
                verification["/db/competencies"] = {"status": r_comp.status_code, "count": len(r_comp.json()) if r_comp.status_code == 200 else 0}
                # attempt first role adjacency if roles exists
                if r_roles.status_code == 200 and isinstance(r_roles.json(), list) and r_roles.json():
                    role_id = r_roles.json()[0]["id"]
                    r_adj = client.get(f"{base}/db/roles/{role_id}/adjacent")
                    verification["/db/roles/{id}/adjacent"] = {"status": r_adj.status_code, "count": len(r_adj.json()) if r_adj.status_code == 200 else 0}
        except Exception as e:
            verification["note"] = f"Skipped HTTP endpoint verification: {e.__class__.__name__}: {e}"
    else:
        verification["note"] = "No backend URL env (REACT_APP_BACKEND_URL/REACT_APP_API_BASE); skipped HTTP verification."

    summary["verify"] = verification
    return summary


def main() -> None:
    res = seed_full()
    if not res.get("ok"):
        print(f"[seed-full] ERROR: {res.get('details')}")
        return

    schema = res.get("schema_sync", {})
    seed = res.get("seed", {})
    verify = res.get("verify", {})
    skipped = res.get("skipped_files", [])

    print(f"[seed-full] schema_sync: ok={schema.get('ok')} executed={schema.get('executed')} sections={schema.get('sections')}")
    if skipped:
        print(f"[seed-full] skipped_files: {', '.join(skipped)}")
    print(f"[seed-full] seed summary: {json.dumps(seed)}")
    print(f"[seed-full] verify: {json.dumps(verify)}")


if __name__ == "__main__":
    main()
