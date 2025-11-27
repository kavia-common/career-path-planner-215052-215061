from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import RoleCard

router = APIRouter(prefix="/role-cards", tags=["role-cards"])


@router.get("/{role_id}", response_model=RoleCard, summary="Get role card content")
async def get_role_card(
    role_id: int,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1]) if authorization else SupabaseClient.anon_mode()
    resp = await client.get("role_cards", params={"select": "role_id,content", "role_id": f"eq.{role_id}"})
    resp.raise_for_status()
    arr = resp.json()
    await client.close()
    if not arr:
        raise HTTPException(status_code=404, detail="Role card not found")
    return arr[0]
