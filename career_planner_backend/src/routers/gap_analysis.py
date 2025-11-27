from typing import List

from fastapi import APIRouter, Depends, Header
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import GapAnalysisResponse, GapItem

router = APIRouter(prefix="/gap-analysis", tags=["gap-analysis"])


@router.get("/role/{role_id}", response_model=GapAnalysisResponse, summary="Compute gap analysis for a target role")
async def compute_gap(role_id: int, authorization: str = Header(...), user: AuthUser = Depends(current_user)):
    token = authorization.split(" ", 1)[1]
    client = SupabaseClient.user_mode(token)

    # Prefer view if exists
    view_resp = await client.get(
        "vw_user_role_gaps",
        params={
            "select": "competency_id,required_level,self_level,delta",
            "user_id": f"eq.{user.id}",
            "role_id": f"eq.{role_id}",
            "order": "competency_id",
        },
    )
    if view_resp.status_code == 200:
        items_arr = view_resp.json()
        await client.close()
        return GapAnalysisResponse(
            role_id=role_id,
            items=[GapItem(**x) for x in items_arr],
        )

    # Fallback: compute by joining mappings + user_competencies
    req_resp = await client.get(
        "role_competencies",
        params={"select": "competency_id,required_level", "role_id": f"eq.{role_id}", "order": "competency_id"},
    )
    req_resp.raise_for_status()
    reqs = req_resp.json()

    self_resp = await client.get(
        "user_competencies",
        params={"select": "competency_id,self_level", "user_id": f"eq.{user.id}"},
    )
    self_resp.raise_for_status()
    self_map = {x["competency_id"]: x["self_level"] for x in self_resp.json()}

    items: List[GapItem] = []
    for r in reqs:
        self_level = self_map.get(r["competency_id"])
        delta = None
        if self_level is not None:
            delta = max(0, int(r["required_level"]) - int(self_level))
        items.append(
            GapItem(
                competency_id=r["competency_id"],
                required_level=r["required_level"],
                self_level=self_level,
                delta=delta,
            )
        )
    await client.close()
    return GapAnalysisResponse(role_id=role_id, items=items)
