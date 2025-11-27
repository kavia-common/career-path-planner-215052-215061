from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    API_TITLE: str = "Career Planner Backend API"
    API_DESCRIPTION: str = (
        "Backend API for the Career Planner MVP. Uses PostgreSQL via SQLAlchemy only. Supabase has been removed."
    )
    API_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=list, description="Allowed CORS origins"
    )

    # Pydantic v2 settings configuration (replaces Config in v1)
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("DATABASE_URL is required and must be a string")
        return v


@lru_cache()
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and cache application settings."""
    return Settings()


settings = get_settings()
