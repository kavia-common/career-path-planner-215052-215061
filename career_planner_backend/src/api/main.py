from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.settings import get_settings, Settings
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

    @app.get("/", tags=["health"], summary="Health Check")
    def health_check() -> dict:
        """
        Health check endpoint.

        Returns:
            dict: Simple health response.
        """
        return {"message": "Healthy"}

    return app


app = create_app()
