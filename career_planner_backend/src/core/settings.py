from functools import lru_cache
from typing import List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    supabase_url: str = Field(..., description="Supabase project URL", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(..., description="Supabase anon/public API key", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(..., description="Supabase service role key (admin tasks only)", alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(..., description="PostgreSQL connection URL (optional if using Supabase REST)", alias="DATABASE_URL")
    cors_origins_raw: str = Field("*", description="Comma-separated list of allowed CORS origins", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        raw = (self.cors_origins_raw or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    class Config:
        populate_by_name = True


@lru_cache()
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return cached application settings from environment variables."""
    return Settings()  # type: ignore[arg-type]
