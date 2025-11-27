from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.core.auth import AuthUser, AdminGuard
from src.core.supabase_client import SupabaseClient

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest", summary="Trigger ingestion job", description="Creates an ingestion_runs entry to trigger ingestion (admin only).")
async def trigger_ingestion(authorization: str = Header(...), user: AuthUser = Depends(AdminGuard)):
    # Use admin mode to ensure permission even if RLS locks table
    client = SupabaseClient.admin_mode()
    body = {"triggered_by": user.id, "status": "queued"}
    resp = await client.post("ingestion_runs", json=[body])
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create ingestion run")
    arr = resp.json()
    await client.close()
    return {"run": arr[0]}


@router.get("/ingest/latest", summary="Get latest ingestion run", description="Gets latest ingestion run for monitoring (admin only).")
async def get_latest_ingestion(user: AuthUser = Depends(AdminGuard)):
    client = SupabaseClient.admin_mode()
    resp = await client.get("ingestion_runs", params={"select": "id,triggered_by,status,started_at,finished_at", "order": "id.desc", "limit": 1})
    resp.raise_for_status()
    arr = resp.json()
    await client.close()
    return arr[0] if arr else {}
