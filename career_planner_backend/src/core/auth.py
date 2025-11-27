from typing import Optional
import httpx
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.core.settings import get_settings


class AuthUser(BaseModel):
    """Represents the authenticated Supabase user and derived flags."""
    id: str = Field(..., description="Supabase auth user id (uuid)")
    email: Optional[str] = Field(None, description="User email")
    is_admin: bool = Field(False, description="Whether user is admin per users table")


async def _get_user_profile(client: httpx.AsyncClient, url: str, key: str, user_id: str) -> Optional[dict]:
    """
    Fetch user profile from public.users table to determine admin flag.

    Args:
        client: httpx Async client
        url: Supabase URL
        key: Supabase service role key (RLS bypass for server-side lookup)
        user_id: Supabase auth user id

    Returns:
        dict | None: User row if found
    """
    # Use service role to read users for admin flag
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    # PostgREST path for users table
    endpoint = f"{url}/rest/v1/users?id=eq.{user_id}&select=id,email,full_name,is_admin"
    resp = await client.get(endpoint, headers=headers, timeout=10.0)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]
        return None
    # If users table not accessible yet, ignore admin
    return None


# PUBLIC_INTERFACE
async def supabase_user_from_jwt(authorization: Optional[str] = Header(None)) -> AuthUser:
    """
    Dependency that validates a Supabase JWT and returns an AuthUser.

    Parameters:
        authorization (str | None): Authorization header value "Bearer <jwt>"

    Returns:
        AuthUser: authenticated user details including admin flag.

    Raises:
        HTTPException 401: if token missing or invalid.
    """
    settings = get_settings()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    # Validate and get user via Supabase auth v1 (/auth/v1/user)
    # This endpoint expects Authorization: Bearer <token> and apikey header.
    headers = {"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(f"{settings.supabase_url}/auth/v1/user", headers=headers, timeout=10.0)
        if user_resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user_json = user_resp.json()
        user_id = user_json.get("id")
        email = user_json.get("email")

        # Determine admin flag from users table using service role
        profile = await _get_user_profile(
            client, settings.supabase_url, settings.supabase_service_role_key, user_id
        )
        is_admin = bool(profile.get("is_admin")) if profile else False

        return AuthUser(id=user_id, email=email, is_admin=is_admin)


class AdminGuard:
    """Dependency class to enforce admin access on routes."""

    # PUBLIC_INTERFACE
    def __call__(self, user: AuthUser = Depends(supabase_user_from_jwt)) -> AuthUser:
        """
        Ensure the current user has admin privileges.

        Args:
            user (AuthUser): Current authenticated user.

        Returns:
            AuthUser: Same user if admin.

        Raises:
            HTTPException 403: if not admin.
        """
        if not user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return user
