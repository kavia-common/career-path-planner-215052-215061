from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    Uses pydantic-settings v2; unknown/extra env vars are ignored so imports never fail when .env contains extra keys.
    """

    # App metadata
    API_TITLE: str = "Career Planner Backend API"
    API_DESCRIPTION: str = (
        "Backend API for the Career Planner MVP. Uses PostgreSQL via SQLAlchemy only. Supabase has been removed."
    )
    API_VERSION: str = "0.1.0"

    # Server bind
    HOST: str = Field(default="0.0.0.0", description="Host interface for the ASGI server")
    PORT: int = Field(default=8000, description="Port for the ASGI server")

    # Database
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection URL. If not provided, will be constructed from legacy POSTGRES_* vars if available.",
    )

    # Legacy optional postgres parts (used to build DATABASE_URL when missing)
    POSTGRES_HOST: Optional[str] = Field(default=None, description="Legacy: Postgres host")
    POSTGRES_PORT: Optional[int] = Field(default=None, description="Legacy: Postgres port")
    POSTGRES_DB: Optional[str] = Field(default=None, description="Legacy: Postgres database name")
    POSTGRES_USER: Optional[str] = Field(default=None, description="Legacy: Postgres user")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, description="Legacy: Postgres password")
    POSTGRES_SSLMODE: Optional[str] = Field(
        default=None, description="Legacy: SSL mode (e.g., require, disable)"
    )

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default_factory=list, description="Allowed CORS origins"
    )

    # Pydantic v2 settings configuration
    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # IMPORTANT: ignore unknown keys so extra env vars do not cause errors
        "extra": "ignore",
    }

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_or_validate_db_url(cls, v, values):
        """If DATABASE_URL is missing, try to build it from legacy POSTGRES_* variables.
        Ensures the app can start with various env setups.
        """
        if v and isinstance(v, str) and v.strip():
            return v.strip()

        host = values.get("POSTGRES_HOST")
        db = values.get("POSTGRES_DB")
        user = values.get("POSTGRES_USER")
        password = values.get("POSTGRES_PASSWORD")
        port = values.get("POSTGRES_PORT") or 5432
        sslmode = values.get("POSTGRES_SSLMODE")

        if host and db and user is not None:
            # Quote password if present
            passwd = f":{quote_plus(password)}" if password else ""
            ssl_q = f"?sslmode={sslmode}" if sslmode else ""
            return f"postgresql+psycopg2://{user}{passwd}@{host}:{port}/{db}{ssl_q}"

        # Leave as None; downstream code handles missing URL gracefully
        return None

    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        return 1 if v <= 0 else (65535 if v > 65535 else v)


@lru_cache()
# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Load and cache application settings."""
    return Settings()


settings = get_settings()
