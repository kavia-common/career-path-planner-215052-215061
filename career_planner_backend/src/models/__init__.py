# Models package marker
"""
Domain models and request/response schemas for the Career Planner backend.

This package exposes Pydantic models under src.models.schemas.
"""

# Re-export commonly used schemas so `from src.models import <Model>` can work if desired.
from . import schemas as schemas

__all__ = ["schemas"]
