from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import RoleCompetency

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.get("/role/{role_id}", response_model=List[RoleCompetency], summary="List role->competency requirements")
async def list_role_requirements(
    role_id: int,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1]) if authorization else SupabaseClient.anon_mode()
    resp = await client.get(
        "role_competencies",
        params={"select": "role_id,competency_id,required_level", "role_id": f"eq.{role_id}", "order": "competency_id"},
    )
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data
