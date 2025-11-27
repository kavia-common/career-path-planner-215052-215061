from typing import List

from fastapi import APIRouter, Depends, Header
from src.core.auth import supabase_user_from_jwt, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import SelfAssessmentUpsert, SelfAssessmentItem

router = APIRouter(prefix="/user-competencies", tags=["user-competencies"])


@router.get("", response_model=List[SelfAssessmentItem], summary="List self-assessments for current user")
async def list_self(authorization: str = Header(...), user: AuthUser = Depends(supabase_user_from_jwt)):
    token = authorization.split(" ", 1)[1]
    client = SupabaseClient.user_mode(token)
    resp = await client.get(
        "user_competencies",
        params={"select": "competency_id,self_level", "user_id": f"eq.{user.id}", "order": "competency_id"},
    )
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data


@router.post("", response_model=List[SelfAssessmentItem], summary="Upsert self-assessments for current user")
async def upsert_self(payload: SelfAssessmentUpsert, authorization: str = Header(...), user: AuthUser = Depends(supabase_user_from_jwt)):
    token = authorization.split(" ", 1)[1]
    client = SupabaseClient.user_mode(token)
    rows = [{"user_id": user.id, "competency_id": it.competency_id, "self_level": it.self_level} for it in payload.items]
    resp = await client.upsert("user_competencies", json=rows)
    resp.raise_for_status()
    data = [{"competency_id": r["competency_id"], "self_level": r["self_level"]} for r in resp.json()] if resp.content else payload.items
    await client.close()
    return data
