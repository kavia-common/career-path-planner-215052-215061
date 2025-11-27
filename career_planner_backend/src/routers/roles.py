from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from src.core.auth import supabase_user_from_jwt, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import Role

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=List[Role], summary="List roles", description="Returns the list of roles from catalog.")
async def list_roles(authorization: str = Header(...), user: AuthUser = Depends(supabase_user_from_jwt)):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1])
    resp = await client.get("roles", params={"select": "id,code,name,summary", "order": "id"})
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data


@router.get("/{role_id}", response_model=Role, summary="Get role", description="Get a single role by id.")
async def get_role(role_id: int, authorization: str = Header(...), user: AuthUser = Depends(supabase_user_from_jwt)):
    client = SupabaseClient.user_mode(authorization.split(" ", 1)[1])
    resp = await client.get("roles", params={"id": f"eq.{role_id}", "select": "id,code,name,summary"})
    resp.raise_for_status()
    arr = resp.json()
    await client.close()
    if not arr:
        raise HTTPException(status_code=404, detail="Role not found")
    return arr[0]
