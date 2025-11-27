#!/usr/bin/env python3
"""
Quick verification script for key endpoints after the API is running.

Usage:
    BACKEND_URL=http://localhost:3001 python -m src.verify_endpoints
"""
import os
import json
import httpx

def main() -> None:
    base = os.getenv("BACKEND_URL", "http://localhost:3001").rstrip("/")
    out = {}
    try:
        with httpx.Client(timeout=10.0, verify=False) as client:
            r_db = client.get(f"{base}/health/db")
            out["/health/db"] = {"status": r_db.status_code, "json": r_db.json() if r_db.status_code == 200 else None}

            r_users = client.get(f"{base}/db/users")
            users = r_users.json() if r_users.status_code == 200 else []
            out["/db/users"] = {"status": r_users.status_code, "count": len(users), "sample_ids": [u.get("id") for u in users[:3]]}

            r_roles = client.get(f"{base}/db/roles")
            roles = r_roles.json() if r_roles.status_code == 200 else []
            out["/db/roles"] = {"status": r_roles.status_code, "count": len(roles), "sample_ids": [r.get("id") for r in roles[:3]]}

            r_comp = client.get(f"{base}/db/competencies")
            comps = r_comp.json() if r_comp.status_code == 200 else []
            out["/db/competencies"] = {"status": r_comp.status_code, "count": len(comps), "sample_ids": [c.get("id") for c in comps[:3]]}

            if roles:
                rid = roles[0].get("id")
                r_adj = client.get(f"{base}/db/roles/{rid}/adjacent")
                adjs = r_adj.json() if r_adj.status_code == 200 else []
                out["/db/roles/{id}/adjacent"] = {"status": r_adj.status_code, "role_id": rid, "count": len(adjs)}
    except Exception as e:
        out["error"] = f"{e.__class__.__name__}: {e}"
    print(json.dumps(out))

if __name__ == "__main__":
    main()
