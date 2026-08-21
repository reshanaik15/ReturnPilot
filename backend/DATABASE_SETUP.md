# Database Connection and Session Management

## Overview

This module provides production-ready database connection management for the ReturnPilot backend using SQLAlchemy 2.0 async capabilities with PostgreSQL.

## Features Implemented (Task 2.2)

### ✅ 1. SQLAlchemy Engine Setup
- Async engine with `asyncpg` driver for PostgreSQL
- Automatic URL conversion from `postgres://` to `postgresql+asyncpg://`
- Development mode SQL query logging
- Graceful handling of missing DATABASE_URL (with warning)

### ✅ 2. Production Connection Pooling
Configured for high-traffic production environments:

```python
pool_size=10          # Base connection pool (10 connections)
max_overflow=20       # Additional connections under load (30 total max)
pool_pre_ping=True    # Validates connections before use
pool_recycle=3600     # Recycles connections after 1 hour
pool_timeout=30       # 30-second timeout for connection requests
```

### ✅ 3. get_db() Dependency Function
FastAPI dependency for automatic session management:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db

@app.get("/api/orders")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order))
    return result.scalars().all()
```

Features:
- Automatic session creation and cleanup
- Automatic commit on success
- Automatic rollback on error
- Proper exception propagation
- Connection cleanup in finally block

### ✅ 4. Database Health Check Function
Monitors database connectivity for deployment platforms:

```python
await check_database_health()
# Returns:
# {
#   "connected": True,
#   "database": "postgresql",
#   "pool_size": 10,
#   "pool_checkedout": 2,
#   "pool_overflow": 0
# }
```

Used by `/api/health` endpoint for:
- Render health checks
- Monitoring systems
- Load balancer health probes
- Deployment verification

### ✅ 5. Lifecycle Management
- `init_db()`: Create all database tables (development/testing)
- `close_db()`: Gracefully close connections on shutdown
- Integrated with FastAPI lifespan events in `main.py`

## Configuration

### Environment Variables (.env)

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
# or for Supabase:
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
```

The module automatically:
1. Converts `postgres://` to `postgresql://` (Heroku/Render compatibility)
2. Adds `+asyncpg` driver suffix
3. Falls back to placeholder if missing (development mode)

## Usage Examples

### 1. Basic Query with Dependency Injection

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.database import Order

router = APIRouter()

@router.get("/api/orders")
async def get_orders(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.customer_id == customer_id)
    )
    orders = result.scalars().all()
    return {"orders": orders}
```

### 2. Creating Records

```python
@router.post("/api/returns")
async def create_return(
    data: ReturnCreate,
    db: AsyncSession = Depends(get_db)
):
    new_return = Return(
        order_id=data.order_id,
        reason=data.reason,
        status="initiated"
    )
    db.add(new_return)
    await db.commit()  # Automatic commit by get_db()
    await db.refresh(new_return)
    return {"return_id": new_return.id}
```

### 3. Manual Session Management (Advanced)

```python
from database import AsyncSessionLocal

async def background_task():
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Order))
            orders = result.scalars().all()
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
```

## Testing

Run the validation script:

```bash
cd backend
python test_database.py
```

This validates:
- ✅ Engine configuration
- ✅ Session factory setup
- ✅ get_db() dependency function
- ✅ Health check functionality
- ✅ Lifecycle management

## Integration with main.py

The `main.py` file integrates database health checks:

```python
@app.get("/api/health")
async def health_check():
    db_health = await check_database_health()
    return {
        "status": "ok" if db_health.get("connected") else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "returnpilot-api",
        "database": db_health
    }
```

Lifespan events handle cleanup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("ReturnPilot API starting up...")
    yield
    # Shutdown: Close database connections
    await close_db()
    print("ReturnPilot API shut down gracefully")
```

## Requirements Validated

✅ **Requirement 15.4**: Database connection strings from environment variables  
✅ **Requirement 15.5**: Health check endpoint for deployment platforms

## Connection Pool Sizing Guide

Adjust pool size based on expected load:

- **Development**: `pool_size=5, max_overflow=5` (10 total)
- **Production (light)**: `pool_size=10, max_overflow=10` (20 total)
- **Production (heavy)**: `pool_size=10, max_overflow=20` (30 total) ✅ Current
- **Production (very heavy)**: `pool_size=20, max_overflow=30` (50 total)

Formula: `pool_size = concurrent_requests / 2`

Example:
- 20 concurrent API requests → pool_size=10
- 50 concurrent API requests → pool_size=25

## Troubleshooting

### "Could not parse SQLAlchemy URL from string ''"
- **Cause**: DATABASE_URL not set in environment
- **Fix**: Create `.env` file with DATABASE_URL or set environment variable

### "password authentication failed"
- **Cause**: Invalid database credentials
- **Fix**: Verify DATABASE_URL credentials match your PostgreSQL instance

### "too many clients"
- **Cause**: Connection pool exhausted
- **Fix**: Increase `pool_size` and `max_overflow` in database.py

### "connection already closed"
- **Cause**: Session used after close
- **Fix**: Ensure all database operations happen within `get_db()` scope

## Next Steps

After database connection is set up, implement:
1. Task 2.3: Define SQLAlchemy ORM models (Customer, Order, Return, etc.)
2. Task 2.4: Create Alembic migrations
3. Task 2.5: Implement database seed scripts

## Files Modified

- ✅ `backend/database.py` - Main implementation
- ✅ `backend/main.py` - Health check integration
- ✅ `backend/requirements.txt` - Added `asyncpg==0.29.0`
- ✅ `backend/test_database.py` - Validation script
- ✅ `backend/DATABASE_SETUP.md` - This documentation
