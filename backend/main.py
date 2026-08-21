"""
ReturnPilot Backend - FastAPI Application
Main application entry point with CORS configuration and health check.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
from contextlib import asynccontextmanager
from config import settings
from database import check_database_health, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    Handles graceful database connection cleanup on shutdown.
    """
    # Startup: Log application start
    print("ReturnPilot API starting up...")
    yield
    # Shutdown: Close database connections
    await close_db()
    print("ReturnPilot API shut down gracefully")


app = FastAPI(
    title="ReturnPilot API",
    description="Backend API for ReturnPilot agent-driven return management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - reads from config.py (which loads from .env)
CORS_ORIGINS = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global Exception Handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic/FastAPI request validation errors.
    Returns a structured 422 response with field-level error details.
    Requirements: 16.1, 16.2
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Request body or parameters failed validation.",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for any unhandled exceptions.
    Returns a generic 500 response to avoid leaking internal details.
    Requirements: 16.1, 16.2
    """
    import traceback
    traceback.print_exc()  # Log full traceback server-side
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring and deployment verification.
    Used by Render and other deployment platforms for health checks.

    Returns service status and database connectivity information.
    """
    db_health = await check_database_health()

    return {
        "status": "ok" if db_health.get("connected") else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "returnpilot-api",
        "database": db_health
    }

# TODO: Import and include routers when implemented
# from routers import agent, orders, returns, dashboard, policy
# app.include_router(agent.router, prefix="/api")
# app.include_router(orders.router, prefix="/api")
# app.include_router(returns.router, prefix="/api")
# app.include_router(dashboard.router, prefix="/api")
# app.include_router(policy.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
