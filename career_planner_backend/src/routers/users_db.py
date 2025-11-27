from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.db import get_db

router = APIRouter(prefix="/db", tags=["users"])


# PUBLIC_INTERFACE
class DBUser(BaseModel):
    """Simple user row from 'users' table with serial id, name, email."""
    id: int = Field(..., description="User id (serial)")
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Unique email")


# PUBLIC_INTERFACE
@router.get(
    "/users",
    response_model=List[DBUser],
    summary="List users (DB)",
    description="Returns a list of users from the simple 'users' table using SQLAlchemy.",
    responses={200: {"description": "Successful Response"}},
)
def list_users_db(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[DBUser]:
    """
    List users from the simple demo users table (id, name, email).
    """
    rows = db.execute(
        text("SELECT id, name, email FROM users ORDER BY id LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    ).fetchall()
    return [DBUser(id=r[0], name=r[1], email=r[2]) for r in rows]


# PUBLIC_INTERFACE
@router.get(
    "/users/{user_id}",
    response_model=DBUser,
    summary="Get user by id (DB)",
    description="Fetch a single user from the 'users' table by id. Returns 404 if not found.",
)
def get_user_db(
    user_id: int = Path(..., description="User id (serial)"),
    db: Session = Depends(get_db),
) -> DBUser:
    """
    Return a single user by id or 404 if not found.
    """
    row = db.execute(
        text("SELECT id, name, email FROM users WHERE id = :id"),
        {"id": user_id},
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return DBUser(id=row[0], name=row[1], email=row[2])
