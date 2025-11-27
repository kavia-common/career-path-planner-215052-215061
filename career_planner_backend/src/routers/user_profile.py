from fastapi import APIRouter, Depends
from src.core.auth import supabase_user_from_jwt, AuthUser
from src.models.schemas import UserProfile

router = APIRouter(prefix="/me", tags=["user"])


@router.get("", response_model=UserProfile, summary="Get current user profile")
async def get_me(user: AuthUser = Depends(supabase_user_from_jwt)):
    return UserProfile(id=user.id, email=user.email, full_name=None, is_admin=user.is_admin)
