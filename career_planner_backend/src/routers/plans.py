from typing import List, Optional

from fastapi import APIRouter, Depends, Header
from src.core.auth import current_user, AuthUser
from src.core.supabase_client import SupabaseClient
from src.models.schemas import Plan, PlanCreate, Goal, GoalCreate

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=List[Plan], summary="List plans for current user")
async def list_plans(
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    token = authorization.split(" ", 1)[1] if authorization else None
    client = SupabaseClient.user_mode(token) if token else SupabaseClient.anon_mode()
    resp = await client.get("plans", params={"select": "id,user_id,title,target_role_id", "user_id": f"eq.{user.id}", "order": "id"})
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data


@router.post("", response_model=Plan, summary="Create plan")
async def create_plan(
    payload: PlanCreate,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    token = authorization.split(" ", 1)[1] if authorization else None
    client = SupabaseClient.user_mode(token) if token else SupabaseClient.anon_mode()
    body = {"user_id": user.id, "title": payload.title, "target_role_id": payload.target_role_id}
    resp = await client.post("plans", json=[body])
    resp.raise_for_status()
    arr = resp.json()
    await client.close()
    return arr[0]


@router.get("/{plan_id}/goals", response_model=List[Goal], summary="List goals in a plan")
async def list_goals(
    plan_id: int,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    token = authorization.split(" ", 1)[1] if authorization else None
    client = SupabaseClient.user_mode(token) if token else SupabaseClient.anon_mode()
    # Enforce ownership via RLS; client token ensures only owned rows returned
    resp = await client.get("plan_goals", params={"select": "id,plan_id,description,status", "plan_id": f"eq.{plan_id}", "order": "id"})
    resp.raise_for_status()
    data = resp.json()
    await client.close()
    return data


@router.post("/{plan_id}/goals", response_model=Goal, summary="Create goal in plan")
async def create_goal(
    plan_id: int,
    payload: GoalCreate,
    authorization: Optional[str] = Header(None),
    user: AuthUser = Depends(current_user),
):
    token = authorization.split(" ", 1)[1] if authorization else None
    client = SupabaseClient.user_mode(token) if token else SupabaseClient.anon_mode()
    body = {"plan_id": plan_id, "description": payload.description, "status": payload.status}
    resp = await client.post("plan_goals", json=[body])
    resp.raise_for_status()
    arr = resp.json()
    await client.close()
    return arr[0]
