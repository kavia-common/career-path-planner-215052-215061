from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import RoleAdjacency

router = APIRouter(prefix="/adjacency", tags=["adjacency"])


@router.get("/from/{role_id}", response_model=List[RoleAdjacency], summary="Adjacency from role")
async def list_from_role(
    role_id: int,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1]) if authorization else SupabaseClient.anon_mode()
    resp = await client.get(
        "role_adjacency",
        params={"select": "from_role_id,to_role_id,weight", "from_role_id": f"eq.{role_id}", "order": "weight.desc"},
    )
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data
