"""
Database connection and session management.
Provides async SQLAlchemy session factory and health check for database operations.
Implements connection pooling for production use.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from config import settings
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# Convert postgres:// to postgresql:// for SQLAlchemy (required for async driver)
DATABASE_URL = settings.database_url.replace("postgres://", "postgresql://", 1) if settings.database_url.startswith("postgres://") else settings.database_url

# Add asyncpg driver if not present
if DATABASE_URL and "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Fallback for missing DATABASE_URL (development/testing without .env)
if not DATABASE_URL:
    logger.warning("DATABASE_URL not set. Using placeholder. Set DATABASE_URL environment variable for actual database connection.")
    DATABASE_URL = "postgresql+asyncpg://localhost/returnpilot"

# Production-ready connection pool configuration
# Pool size based on expected concurrent request load
# pool_pre_ping ensures connections are valid before use
# pool_recycle prevents stale connections in long-running services
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.environment == "development",  # Log SQL queries in dev
    pool_pre_ping=True,  # Validate connections before use
    pool_size=10,  # Base pool size (increased for production load)
    max_overflow=20,  # Additional connections under high load
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Wait 30 seconds for connection before timeout
)

# Async session factory
# expire_on_commit=False allows access to objects after commit
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency function for database session injection.
    
    Provides async context-managed database sessions with automatic
    commit/rollback and cleanup. Use with FastAPI's Depends():
    
    Example:
        @app.get("/api/orders")
        async def get_orders(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Order))
            return result.scalars().all()
    
    Validates: Requirements 15.4, 15.5
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def check_database_health() -> dict:
    """
    Database health check function for monitoring and deployment verification.
    
    Returns connection status and basic metrics. Used by health check endpoint
    and deployment platforms (e.g., Render) to verify database connectivity.
    
    Returns:
        dict: {
            "connected": bool,
            "database": str,
            "pool_size": int,
            "pool_overflow": int,
            "error": str (optional)
        }
    
    Validates: Requirements 15.5
    """
    try:
        async with AsyncSessionLocal() as session:
            # Execute simple query to verify connection
            result = await session.execute(text("SELECT 1 as health_check"))
            result.scalar()
            
            # Get pool statistics
            pool = engine.pool
            
            return {
                "connected": True,
                "database": "postgresql",
                "pool_size": pool.size(),
                "pool_checkedout": pool.checkedout(),
                "pool_overflow": pool.overflow(),
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "connected": False,
            "database": "postgresql",
            "error": str(e),
        }


async def init_db():
    """
    Initialize database tables (for development/testing).
    
    Creates all tables defined in SQLAlchemy models. In production,
    use Alembic migrations instead for proper version control.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db():
    """
    Close database connections and dispose of connection pool.
    
    Should be called on application shutdown to gracefully close
    all database connections.
    """
    await engine.dispose()
    logger.info("Database connections closed")
