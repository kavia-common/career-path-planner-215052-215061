from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import Competency

router = APIRouter(prefix="/competencies", tags=["competencies"])


@router.get("", response_model=List[Competency], summary="List competencies")
async def list_competencies(
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1]) if authorization else SupabaseClient.anon_mode()
    resp = await client.get("competencies", params={"select": "id,code,name,category", "order": "id"})
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data
