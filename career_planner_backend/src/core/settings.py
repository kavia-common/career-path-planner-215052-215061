from functools import lru_cache
from typing import List, Optional
import os
from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    """Application settings loaded from environment variables with safe defaults for local dev boot."""

    # Using aliases to support env var names; defaults allow the app to boot even without .env
    supabase_url: str = Field("http://localhost:54321", description="Supabase project URL", alias="SUPABASE_URL")
    supabase_anon_key: str = Field("dev-anon-key", description="Supabase anon/public API key", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field("dev-service-role-key", description="Supabase service role key (admin tasks only)", alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: Optional[str] = Field(None, description="PostgreSQL connection URL (optional if using Supabase REST)", alias="DATABASE_URL")
    cors_origins_raw: str = Field("*", description="Comma-separated list of allowed CORS origins", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        """
        Returns:
            List[str]: Parsed CORS origins. "*" becomes ["*"] which FastAPI CORS understands as allow all.
        """
        raw = (self.cors_origins_raw or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @field_validator("supabase_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v[:-1] if v.endswith("/") else v

    class Config:
        populate_by_name = True

    @staticmethod
    def from_env() -> "Settings":
        """
        Build Settings from environment with safe fallbacks.
        This avoids pydantic ValidationError when env vars are absent.
        """
        return Settings(
            SUPABASE_URL=os.getenv("SUPABASE_URL", "http://localhost:54321"),
            SUPABASE_ANON_KEY=os.getenv("SUPABASE_ANON_KEY", "dev-anon-key"),
            SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "dev-service-role-key"),
            DATABASE_URL=os.getenv("DATABASE_URL") or None,
            CORS_ORIGINS=os.getenv("CORS_ORIGINS", "*"),
        )


@lru_cache()
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """
    Return cached application settings from environment variables.

    Safe for boot without .env: provides local defaults so uvicorn can start.
    """
    return Settings.from_env()
