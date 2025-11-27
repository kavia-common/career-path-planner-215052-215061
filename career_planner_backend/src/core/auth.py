from typing import Optional, Dict
from fastapi import Header


def _parse_bearer(token: Optional[str]) -> Optional[str]:
    """Extracts the token from a 'Bearer <token>' header string."""
    if not token:
        return None
    parts = token.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# PUBLIC_INTERFACE
def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict:
    """Return a minimal current user dict.

    For MVP, no real auth is enforced. If an Authorization header is present,
    we simply return a pseudo user with that token as raw reference.
    """
    token = _parse_bearer(authorization)
    if not token:
        return {"id": "anon", "is_admin": False}
    return {"id": "token_user", "is_admin": False}
