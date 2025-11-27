from typing import List

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.db import get_db
from src.models.orm import Role, Competency, RoleAdjacency
from src.models.schemas import Role as RoleSchema
from src.models.schemas import Competency as CompetencySchema
from src.models.schemas import RoleAdjacency as RoleAdjacencySchema

router = APIRouter(prefix="/db", tags=["roles", "competencies", "adjacency"])

# PUBLIC_INTERFACE
@router.get("/roles", response_model=List[RoleSchema], summary="List roles (DB)")
def list_roles_db(db: Session = Depends(get_db), limit: int = Query(500, ge=1, le=10000)) -> List[RoleSchema]:
    """
    List roles directly from Neon via SQLAlchemy (bypasses Supabase REST).
    """
    rows = db.execute(select(Role).order_by(Role.id).limit(limit)).scalars().all()
    return [RoleSchema(id=r.id, code=r.code, name=r.name, summary=r.summary) for r in rows]

# PUBLIC_INTERFACE
@router.get("/competencies", response_model=List[CompetencySchema], summary="List competencies (DB)")
def list_competencies_db(db: Session = Depends(get_db), limit: int = Query(1000, ge=1, le=20000)) -> List[CompetencySchema]:
    """
    List competencies directly from Neon via SQLAlchemy.
    """
    rows = db.execute(select(Competency).order_by(Competency.id).limit(limit)).scalars().all()
    return [CompetencySchema(id=c.id, code=c.code, name=c.name, category=c.category) for c in rows]

# PUBLIC_INTERFACE
@router.get("/roles/{role_id}/adjacent", response_model=List[RoleAdjacencySchema], summary="Adjacent roles (DB)")
def list_adjacent_roles_db(
    role_id: int = Path(..., description="Source role id"),
    db: Session = Depends(get_db),
    limit: int = Query(1000, ge=1, le=10000),
) -> List[RoleAdjacencySchema]:
    """
    Return adjacency edges originating from the given role.
    """
    stmt = select(RoleAdjacency).where(RoleAdjacency.from_role_id == role_id).order_by(RoleAdjacency.weight.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        RoleAdjacencySchema(from_role_id=e.from_role_id, to_role_id=e.to_role_id, weight=float(e.weight))
        for e in rows
    ]
