from typing import Any, Dict, List, Optional

import httpx

from src.core.settings import get_settings


class SupabaseClient:
    """
    Lightweight wrapper around Supabase PostgREST endpoints.

    Two modes:
    - user_mode(token): uses user's JWT to honor RLS policies for end-user requests.
    - admin_mode(): uses service role key to bypass RLS for administrative operations.
    """

    def __init__(self, token: Optional[str] = None, admin: bool = False) -> None:
        settings = get_settings()
        self.base_url: str = f"{settings.supabase_url}/rest/v1"
        self.apikey: str = settings.supabase_anon_key if not admin else settings.supabase_service_role_key
        # Authorization uses service role if admin, otherwise the provided user token
        auth_token = self.apikey if admin else (token or "")
        self.authorization: str = f"Bearer {auth_token}"
        self._client: httpx.AsyncClient = httpx.AsyncClient(timeout=20.0)

    @classmethod
    # PUBLIC_INTERFACE
    def user_mode(cls, token: str) -> "SupabaseClient":
        """Create client using user's JWT (RLS enabled)."""
        return cls(token=token, admin=False)

    @classmethod
    # PUBLIC_INTERFACE
    def admin_mode(cls) -> "SupabaseClient":
        """Create client using service role key (admin; RLS bypass)."""
        return cls(token=None, admin=True)

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.apikey,
            "Authorization": self.authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        url = f"{self.base_url}/{path}"
        return await self._client.get(url, headers=self._headers(), params=params or {})

    async def post(self, path: str, json: Any) -> httpx.Response:
        url = f"{self.base_url}/{path}"
        return await self._client.post(url, headers=self._headers(), json=json)

    async def patch(self, path: str, json: Any, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        url = f"{self.base_url}/{path}"
        headers = self._headers()
        headers["Prefer"] = "return=representation"
        return await self._client.patch(url, headers=headers, json=json, params=params or {})

    async def upsert(self, path: str, json: Any) -> httpx.Response:
        url = f"{self.base_url}/{path}"
        headers = self._headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        return await self._client.post(url, headers=headers, json=json)

    async def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        url = f"{self.base_url}/{path}"
        return await self._client.delete(url, headers=self._headers(), params=params or {})

    async def close(self) -> None:
        await self._client.aclose()

    # PUBLIC_INTERFACE
    async def list_paginated(
        self,
        table: str,
        select: str,
        limit: int = 1000,
        offset: int = 0,
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> List[dict]:
        """
        List rows from a table with basic pagination.

        Args:
            table: table or view name
            select: PostgREST select clause
            limit: max rows to return
            offset: offset for pagination
            extra_filters: extra PostgREST filters like {"role_id": "eq.1"}

        Returns:
            List of row objects.
        """
        params: Dict[str, Any] = {"select": select, "limit": limit, "offset": offset}
        if extra_filters:
            params.update(extra_filters)
        resp = await self.get(table, params=params)
        resp.raise_for_status()
        return resp.json()
