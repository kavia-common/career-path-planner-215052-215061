"""Deprecated Supabase utilities.

This module is retained as a stub to avoid import errors after removing Supabase.
It provides a minimal SupabaseClient class with the same surface used by routers,
but all network operations return 501 Not Implemented to make it explicit that
Supabase has been removed from this backend.

Routers that still depend on SupabaseClient can import it without breaking app startup.
Consider migrating those routes to use direct PostgreSQL access via src.core.db and ORM.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Mapping, Union
import json


class _StubResponse:
    """Simple HTTP-like response object to mimic httpx.Response methods used by routers."""

    def __init__(self, status_code: int = 501, payload: Optional[Union[dict, list, str]] = None):
        self.status_code = status_code
        # store text for error readability
        if payload is None:
            payload = {"error": "Supabase integration is disabled in this backend."}
        if isinstance(payload, (dict, list)):
            self._json = payload
            self.text = json.dumps(payload)
            self.content = self.text.encode("utf-8")
        else:
            # string fallback
            self._json = {"message": str(payload)}
            self.text = str(payload)
            self.content = self.text.encode("utf-8")

    def json(self):
        return self._json

    def raise_for_status(self):
        """Mimic httpx.Response.raise_for_status; raise on non-2xx codes."""
        if not (200 <= self.status_code < 300):
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")


# PUBLIC_INTERFACE
class SupabaseClient:
    """A stubbed Supabase client with the minimal interface expected by routers.

    All methods return 501 Not Implemented. Use the /db/* endpoints or migrate routers to SQLAlchemy.
    """

    def __init__(self, mode: str = "anon", token: Optional[str] = None):
        self.mode = mode
        self.token = token

    # PUBLIC_INTERFACE
    @classmethod
    def anon_mode(cls) -> "SupabaseClient":
        """Create a stub client in anonymous mode."""
        return cls(mode="anon", token=None)

    # PUBLIC_INTERFACE
    @classmethod
    def user_mode(cls, token: Optional[str]) -> "SupabaseClient":
        """Create a stub client using a user's bearer token (unused)."""
        return cls(mode="user", token=token)

    # PUBLIC_INTERFACE
    @classmethod
    def admin_mode(cls) -> "SupabaseClient":
        """Create a stub client with admin/service role privileges (unused)."""
        return cls(mode="admin", token=None)

    async def get(self, table: str, params: Optional[Mapping[str, str]] = None):
        """Stub GET; returns 501 Not Implemented with context of the request."""
        return _StubResponse(
            501,
            {
                "error": "supabase_disabled",
                "message": "Supabase REST is disabled; use /db/* endpoints.",
                "op": "get",
                "table": table,
                "params": dict(params) if params else {},
            },
        )

    async def post(self, table: str, json: Optional[Any] = None):
        """Stub POST; returns 501 Not Implemented."""
        return _StubResponse(
            501,
            {
                "error": "supabase_disabled",
                "message": "Supabase REST is disabled; writing via Supabase is not supported.",
                "op": "post",
                "table": table,
                "json": json,
            },
        )

    async def upsert(self, table: str, json: Optional[Any] = None):
        """Stub UPSERT; returns 501 Not Implemented."""
        return _StubResponse(
            501,
            {
                "error": "supabase_disabled",
                "message": "Supabase REST is disabled; upsert via Supabase is not supported.",
                "op": "upsert",
                "table": table,
                "json": json,
            },
        )

    async def close(self):
        """No-op close to match expected async client cleanup."""
        return None


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
