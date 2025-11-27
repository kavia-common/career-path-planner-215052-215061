from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_settings, Settings
from src.core.db import ping_db, init_db, seed_minimal_data
from src.core.seeder import seed_catalog_from_json
from src.routers import (
    roles,
    competencies,
    mappings,
    role_cards,
    adjacency,
    user_profile,
    user_competencies,
    plans,
    gap_analysis,
    admin,
)

# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application with metadata, CORS, and routers.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    settings: Settings = get_settings()

    app = FastAPI(
        title="Career Planner Backend API",
        description=(
            "Backend API for the Career Planner MVP. "
            "Includes Supabase JWT authentication, user self-assessments, roles/competencies catalog, "
            "gap analysis computation, and admin ingestion triggers."
        ),
        version="0.1.0",
        openapi_tags=[
            {"name": "health", "description": "Health and diagnostics"},
            {"name": "auth", "description": "Authentication utilities"},
            {"name": "roles", "description": "Roles catalog"},
            {"name": "competencies", "description": "Competencies catalog"},
            {"name": "mappings", "description": "Role-competency mappings"},
            {"name": "role-cards", "description": "Role card content"},
            {"name": "adjacency", "description": "Role adjacency graph"},
            {"name": "user", "description": "Current user profile"},
            {"name": "user-competencies", "description": "User self-assessments"},
            {"name": "plans", "description": "Plans and goals"},
            {"name": "gap-analysis", "description": "Gap analysis computation"},
            {"name": "admin", "description": "Administrative ingestion and management"},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(roles.router)
    app.include_router(competencies.router)
    app.include_router(mappings.router)
    app.include_router(role_cards.router)
    app.include_router(adjacency.router)
    app.include_router(user_profile.router)
    app.include_router(user_competencies.router)
    app.include_router(plans.router)
    app.include_router(gap_analysis.router)
    app.include_router(admin.router)

    # Optional direct-DB catalog endpoints (Neon via SQLAlchemy)
    from src.routers import catalog_db  # local import to avoid circulars at module import time
    app.include_router(catalog_db.router)

    # Simple DB-backed users endpoints (demo users table)
    from src.routers import users_db  # type: ignore
    app.include_router(users_db.router)

    @app.get("/", tags=["health"], summary="Health Check")
    def health_check() -> dict:
        """
        Health check endpoint.

        Returns:
            dict: Simple health response.
        """
        return {"message": "Healthy"}

    @app.get(
        "/health/db",
        tags=["health"],
        summary="Database Health Check",
        description="Pings the configured PostgreSQL database using DATABASE_URL and returns connectivity status.",
        responses={
            200: {
                "description": "Database connectivity status",
                "content": {"application/json": {}},
            }
        },
    )
    def db_health() -> dict:
        """
        Database health check endpoint.

        Returns:
            dict: Contains ok (bool) and details (str).
        """
        return ping_db()

    @app.on_event("startup")
    async def _verify_db_on_startup() -> None:
        """
        Startup hook to verify database connectivity once the app boots.
        - Pings DB
        - Creates schema if absent
        - Seeds minimal data idempotently
        """
        result = ping_db()
        # We avoid raising to keep app responsive even if DB is temporarily unavailable.
        # This can be enhanced to use proper logging framework.
        import sys
        if not result.get("ok"):
            print(f"[startup] DB ping failed: {result.get('details')}", file=sys.stderr)
            return
        print("[startup] DB ping OK", flush=True)

        try:
            init_db()
            print("[startup] DB schema ensured (create_all).", flush=True)
            seed_result = seed_minimal_data()
            print(f"[startup] Seed: {seed_result}", flush=True)
            # Seed catalog from JSON files if present
            catalog = seed_catalog_from_json()
            print(f"[startup] JSON seed: {catalog}", flush=True)
        except Exception as e:
            print(f"[startup] DB init/seed error: {e}", file=sys.stderr)

    return app


app = create_app()
