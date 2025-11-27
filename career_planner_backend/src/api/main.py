from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.settings import settings
from ..core.db import ping_db, init_db
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


@app.on_event("startup")
async def startup_non_blocking_db_init() -> None:
    """
    Attempt a short DB initialization on startup with retry/backoff, but do not fail app if DB is unavailable.
    This ensures uvicorn can serve '/' and '/health/*' endpoints even if the database is still initializing.
    """
    # Try a modest retry budget; keep delays short so startup isn't blocked for long
    res = init_db(retries=2, backoff_seconds=0.5)
    if not res.get("ok"):
        print(f"[startup] WARN: DB not ready at startup: {res.get('error')}. "
              f"Service will start and expose /health endpoints; DB-backed routes may fail until ready.")


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["health"],
    summary="Health Check (liveness)",
    description="Liveness probe; does not require database. Returns service-level ok.",
)
def health_check():
    """
    PUBLIC_INTERFACE
    Basic liveness response indicating the API process is running.

    Returns:
        dict: {"status": "ok", "service": "alive"}
    """
    return {"status": "ok", "service": "alive"}


# PUBLIC_INTERFACE
@app.get(
    "/health/ready",
    tags=["health"],
    summary="Readiness Check",
    description="Readiness probe; includes database connectivity check with a quick ping.",
)
def readiness_check():
    """
    PUBLIC_INTERFACE
    Return readiness info including DB reachability.

    Returns:
        dict: {"status": "ready" | "not_ready", "db": <ping result dict>}
    """
    db = ping_db(max_retries=0)
    return {
        "status": "ready" if db.get("ok") else "not_ready",
        "db": db,
    }


# PUBLIC_INTERFACE
@app.get(
    "/health/db",
    tags=["health"],
    summary="Database Health Check",
    description="Pings the configured PostgreSQL database using DATABASE_URL and returns connectivity status.",
)
def db_health():
    """
    PUBLIC_INTERFACE
    Return database connectivity status.

    Returns:
        dict: {"ok": bool, "result": 1} or {"ok": False, "error": "<message>"}
    """
    return ping_db(max_retries=0)


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
