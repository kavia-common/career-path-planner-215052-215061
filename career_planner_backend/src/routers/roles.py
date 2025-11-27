from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from src.core.auth import AuthUser, AdminGuard
from src.core.supabase_client import SupabaseClient
from src.models.schemas import Role, RoleIn

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "",
    response_model=List[Role],
    summary="List roles",
    description="Returns the list of roles from catalog.",
)
async def list_roles(
    authorization: Optional[str] = Header(None, description="Optional: Bearer <Supabase JWT> for personalized RLS; falls back to anon read"),
):
    """
    List roles from the catalog.

    Auth:
        - If Authorization is provided, uses the user's JWT (RLS via user).
        - If missing, falls back to anon key allowing public read where RLS permits.

    Returns:
        List[Role]: Roles ordered by id.
    """
    # Choose client mode
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        client = SupabaseClient.user_mode(token)
    else:
        client = SupabaseClient.anon_mode()
    try:
        resp = await client.get(
            "roles",
            params={"select": "id,code,name,summary", "order": "id"},
        )
        resp.raise_for_status()
        return resp.json()
    finally:
        await client.close()


@router.get(
    "/{role_id}",
    response_model=Role,
    summary="Get role",
    description="Get a single role by id.",
)
async def get_role(
    role_id: int,
    authorization: Optional[str] = Header(None, description="Optional: Bearer <Supabase JWT>; falls back to anon read"),
):
    """
    Fetch one role by id.

    Auth:
        - If Authorization is provided, uses user's JWT (RLS via user).
        - Otherwise uses anon key for public read.

    Raises:
        HTTPException 404 if role not found.
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        client = SupabaseClient.user_mode(token)
    else:
        client = SupabaseClient.anon_mode()
    try:
        resp = await client.get(
            "roles",
            params={"id": f"eq.{role_id}", "select": "id,code,name,summary"},
        )
        resp.raise_for_status()
        arr = resp.json()
        if not arr:
            raise HTTPException(status_code=404, detail="Role not found")
        return arr[0]
    finally:
        await client.close()


@router.post(
    "",
    response_model=Role,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    description="Create a new role (admin only).",
)
async def create_role(
    payload: RoleIn,
    authorization: str = Header(..., description="Bearer <Supabase JWT>"),
    _: AuthUser = Depends(AdminGuard),
):
    """
    Create a new role in the catalog.

    Auth:
        Admins only. Uses service role key to ensure write is permitted regardless of RLS.

    Request body:
        RoleIn: { code, name, summary? }

    Returns:
        Role: Created role record with id.
    """
    # Use admin client to write
    client = SupabaseClient.admin_mode()
    body = {"code": payload.code, "name": payload.name, "summary": payload.summary}
    try:
        resp = await client.post("roles", json=[body])
        if resp.status_code not in (200, 201):
            # Bubble up error from Supabase if present
            try:
                detail = resp.json()
            except Exception:
                detail = {"message": resp.text}
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Failed to create role", "supabase": detail},
            )
        arr = resp.json()
        if not arr:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No role returned")
        # Ensure response conforms to Role model
        created = arr[0]
        return {
            "id": created.get("id"),
            "code": created.get("code"),
            "name": created.get("name"),
            "summary": created.get("summary"),
        }
    finally:
        await client.close()
