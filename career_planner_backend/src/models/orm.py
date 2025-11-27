from __future__ import annotations

from typing import List, Optional

from sqlalchemy import String, Integer, ForeignKey, Text, Float, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base


class User(Base):
    """
    Basic user profile table (separate from Supabase auth).
    Stores minimal info used by backend features.
    """
    __tablename__ = "users"

    # Use Supabase auth user id (UUID) as PK (string for simplicity).
    id: Mapped[str] = mapped_column(String(64), primary_key=True, doc="Auth user id (UUID)")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

    # Relationships
    plans: Mapped[List["CareerPlan"]] = relationship("CareerPlan", back_populates="owner", cascade="all, delete-orphan")


class CareerPlan(Base):
    """
    A user's career plan that can contain multiple goals.
    """
    __tablename__ = "career_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    target_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="plans")
    goals: Mapped[List["Goal"]] = relationship("Goal", back_populates="plan", cascade="all, delete-orphan")


class Goal(Base):
    """
    A goal within a plan.
    """
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("career_plans.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    plan: Mapped["CareerPlan"] = relationship("CareerPlan", back_populates="goals")


class Role(Base):
    """
    Catalog role table (id, code unique, name, summary).
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_roles_code", "code"),
    )


class Competency(Base):
    """
    Catalog competency table (id, code unique, name, category).
    """
    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    __table_args__ = (
        Index("ix_competencies_code", "code"),
    )


class RoleAdjacency(Base):
    """
    Weighted edges between roles indicating adjacency/similarity.
    Composite primary key (from_role_id, to_role_id).
    """
    __tablename__ = "role_adjacency"

    from_role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    to_role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships (optional, not eagerly loaded)
    from_role: Mapped["Role"] = relationship("Role", foreign_keys=[from_role_id])
    to_role: Mapped["Role"] = relationship("Role", foreign_keys=[to_role_id])


class RoleCompetency(Base):
    """
    Required competency levels for a given role.
    Composite primary key (role_id, competency_id).
    """
    __tablename__ = "role_competencies"

    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    competency_id: Mapped[int] = mapped_column(Integer, ForeignKey("competencies.id", ondelete="CASCADE"), primary_key=True)
    required_level: Mapped[int] = mapped_column(Integer, nullable=False)

    role: Mapped["Role"] = relationship("Role")
    competency: Mapped["Competency"] = relationship("Competency")
