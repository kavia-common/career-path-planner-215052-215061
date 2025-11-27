from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.settings import settings
from ..core.db import ping_db
from ..routers import (
    roles,
    competencies,
    mappings,
    role_cards,
    adjacency,
    user_competencies,
    plans,
    admin,
    users_db,
    catalog_db,
)

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    openapi_tags=[
        {"name": "health", "description": "Health and diagnostics"},
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

# Configure CORS if origins provided
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["health"],
    summary="Health Check",
    description="Health check endpoint.\n\nReturns:\n    dict: Simple health response.",
)
def health_check():
    """Basic health response."""
    return {"status": "ok"}


# PUBLIC_INTERFACE
@app.get(
    "/health/db",
    tags=["health"],
    summary="Database Health Check",
    description="Pings the configured PostgreSQL database using DATABASE_URL and returns connectivity status.",
)
def db_health():
    """Return database connectivity status."""
    return ping_db()


# Register routers
app.include_router(roles.router)
app.include_router(competencies.router)
app.include_router(mappings.router)
app.include_router(role_cards.router)
app.include_router(adjacency.router)
app.include_router(user_competencies.router)
app.include_router(plans.router)
app.include_router(admin.router)
app.include_router(users_db.router)
app.include_router(catalog_db.router)
