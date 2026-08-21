"""
ReturnPilot Backend - FastAPI Application
Main application entry point with CORS configuration and health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager
import os
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

# CORS configuration - allow frontend to access backend
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
