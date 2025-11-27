from typing import List

from fastapi import APIRouter, Depends, Header
from src.core.auth import supabase_user_from_jwt, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import Competency

router = APIRouter(prefix="/competencies", tags=["competencies"])


@router.get("", response_model=List[Competency], summary="List competencies")
async def list_competencies(authorization: str = Header(...), user: AuthUser = Depends(supabase_user_from_jwt)):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1])
    resp = await client.get("competencies", params={"select": "id,code,name,category", "order": "id"})
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data
