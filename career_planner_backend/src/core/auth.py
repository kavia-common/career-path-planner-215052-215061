from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field


def _parse_bearer(token: Optional[str]) -> Optional[str]:
    """Extracts the token from a 'Bearer <token>' header string."""
    if not token:
        return None
    parts = token.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# PUBLIC_INTERFACE
class AuthUser(BaseModel):
    """Minimal authenticated user representation used by routers."""
    id: str = Field(..., description="User identifier (UUID or token-derived)")
    email: Optional[str] = Field(None, description="User email if known")
    is_admin: bool = Field(False, description="Admin privileges flag")


# PUBLIC_INTERFACE
def current_user(authorization: Optional[str] = Header(default=None)) -> AuthUser:
    """Dependency that returns a minimal AuthUser.

    Behavior:
    - If Authorization header contains a Bearer token, synthesizes a user id from it.
    - If not present, returns an anonymous AuthUser with id='anon', is_admin=False.

    This is a stub for development; no real verification is performed.
    """
    token = _parse_bearer(authorization)
    if not token:
        return AuthUser(id="anon", email=None, is_admin=False)
    # In a real setup, validate token and fetch user profile/claims.
    # Here we synthesize a deterministic id for dev purposes.
    return AuthUser(id="token_user", email=None, is_admin=False)


# PUBLIC_INTERFACE
def admin_guard(user: AuthUser = Depends(current_user)) -> AuthUser:
    """Dependency that ensures the caller is admin or raises 403.

    For the stub, only users with is_admin=True pass. Since current_user() sets
    is_admin to False by default, this will reject unless upstream logic sets it True.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


# Backwards-compatible export expected by routers
AdminGuard = admin_guard
