"""Deprecated Supabase utilities.

This module is retained as a stub to avoid import errors after removing Supabase.
All functions return neutral values and do not perform any external calls.
"""

from typing import Optional, Dict, Any


# PUBLIC_INTERFACE
def get_supabase() -> None:
    """Return None; Supabase has been removed."""
    return None


# PUBLIC_INTERFACE
def parse_bearer(token: Optional[str]) -> Optional[str]:
    """Extract the token from an Authorization header of the form 'Bearer <token>'."""
    if not token:
        return None
    parts = token.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# PUBLIC_INTERFACE
def decode_supabase_jwt(token: Optional[str]) -> Dict[str, Any]:
    """Return empty payload; JWT handling via Supabase is not used."""
    return {}
