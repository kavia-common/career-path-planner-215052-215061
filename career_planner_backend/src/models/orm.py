from __future__ import annotations

from typing import List, Optional

from sqlalchemy import String, Integer, ForeignKey, Text
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
    target_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
    status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    plan: Mapped["CareerPlan"] = relationship("CareerPlan", back_populates="goals")
