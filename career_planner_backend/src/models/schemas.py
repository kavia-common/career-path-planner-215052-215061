"""
Pydantic models used by routers for request/response validation.

Note: Keep these models aligned with Supabase table schemas and views.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# PUBLIC_INTERFACE
class Role(BaseModel):
    """Represents a job role from the catalog."""
    id: int = Field(..., description="Primary key of the role")
    code: str = Field(..., description="Short code for the role")
    name: str = Field(..., description="Display name of the role")
    summary: Optional[str] = Field(None, description="Short summary or description for the role")


# PUBLIC_INTERFACE
class Competency(BaseModel):
    """Represents a competency definition."""
    id: int = Field(..., description="Primary key of the competency")
    code: str = Field(..., description="Short code for the competency")
    name: str = Field(..., description="Display name for the competency")
    category: Optional[str] = Field(None, description="Optional category/grouping")


# PUBLIC_INTERFACE
class RoleCompetency(BaseModel):
    """Mapping row indicating competency requirements for a role."""
    role_id: int = Field(..., description="Role identifier")
    competency_id: int = Field(..., description="Competency identifier")
    required_level: int = Field(..., description="Required proficiency level for the competency in this role")


# PUBLIC_INTERFACE
class RoleAdjacency(BaseModel):
    """Edge in a role adjacency graph, weighted by similarity/transition ease."""
    from_role_id: int = Field(..., description="Source role id")
    to_role_id: int = Field(..., description="Destination role id")
    weight: float = Field(..., description="Adjacency weight (higher implies stronger adjacency)")


# PUBLIC_INTERFACE
class RoleCard(BaseModel):
    """Rich content for a role card (markdown or structured content)."""
    role_id: int = Field(..., description="Role id")
    content: str = Field(..., description="Role card content (e.g., markdown/json)")


# PUBLIC_INTERFACE
class SelfAssessmentItem(BaseModel):
    """A user's self-assessed competency level."""
    competency_id: int = Field(..., description="Competency identifier")
    self_level: int = Field(..., description="User's self-assessed level")


# PUBLIC_INTERFACE
class SelfAssessmentUpsert(BaseModel):
    """Payload to upsert multiple self-assessments."""
    items: List[SelfAssessmentItem] = Field(..., description="List of self-assessment items")


# PUBLIC_INTERFACE
class UserProfile(BaseModel):
    """Current user's basic profile returned by /me endpoint."""
    id: str = Field(..., description="Auth user id (UUID)")
    email: Optional[str] = Field(None, description="User email")
    full_name: Optional[str] = Field(None, description="Full name if available")
    is_admin: bool = Field(False, description="Admin flag from profile")


# PUBLIC_INTERFACE
class Plan(BaseModel):
    """Represents a career plan owned by a user."""
    id: int = Field(..., description="Plan id")
    user_id: str = Field(..., description="Owner's auth user id")
    title: str = Field(..., description="Plan title")
    target_role_id: Optional[int] = Field(None, description="Optional target role id for the plan")


# PUBLIC_INTERFACE
class PlanCreate(BaseModel):
    """Payload to create a plan."""
    title: str = Field(..., description="Plan title")
    target_role_id: Optional[int] = Field(None, description="Optional target role id")


# PUBLIC_INTERFACE
class Goal(BaseModel):
    """Represents a goal within a plan."""
    id: int = Field(..., description="Goal id")
    plan_id: int = Field(..., description="Associated plan id")
    description: str = Field(..., description="Goal description")
    status: Optional[str] = Field(None, description="Status label (e.g., not_started, in_progress, done)")


# PUBLIC_INTERFACE
class GoalCreate(BaseModel):
    """Payload to create a goal within a plan."""
    description: str = Field(..., description="Goal description")
    status: Optional[str] = Field("not_started", description="Initial status label")


# PUBLIC_INTERFACE
class GapItem(BaseModel):
    """Single competency gap analysis item for a target role."""
    competency_id: int = Field(..., description="Competency identifier")
    required_level: int = Field(..., description="Required level for the role")
    self_level: Optional[int] = Field(None, description="User's current level (if available)")
    delta: Optional[int] = Field(None, description="Gap delta (required - self), if computable")


# PUBLIC_INTERFACE
class GapAnalysisResponse(BaseModel):
    """Response payload for gap analysis against a target role."""
    role_id: int = Field(..., description="Target role id for analysis")
    items: List[GapItem] = Field(..., description="List of gap items by competency")


# PUBLIC_INTERFACE
class RoleIn(BaseModel):
    """Payload to create a new role."""
    code: str = Field(..., description="Short code for the role")
    name: str = Field(..., description="Display name of the role")
    summary: Optional[str] = Field(None, description="Short summary or description for the role")


# PUBLIC_INTERFACE
class RoleListResponse(BaseModel):
    """Wrapper for listing roles (reserved for future pagination/metadata)."""
    items: List["Role"] = Field(..., description="List of roles")
