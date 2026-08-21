# Code Execution Flow

## Overview

This document explains **exactly how the ReturnPilot backend code executes**, from the entry point through the entire request lifecycle. It shows which functions call which functions, what the execution order is, and traces a complete request through the system.

---

## Entry Point: main.py

**The starting point of the entire application is `backend/main.py`.**

When you run the backend, this is what happens:

```bash
# Command to start the server
python main.py
# OR
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Startup Sequence

```
1. Python imports main.py
   ↓
2. FastAPI app instance created: app = FastAPI(lifespan=lifespan)
   ↓
3. Lifespan context manager starts
   ↓
4. lifespan() function runs "Startup" code
   ↓
5. CORS middleware is added to app
   ↓
6. Routes are registered (@app.get, @app.post decorators)
   ↓
7. uvicorn starts HTTP server listening on port 8000
   ↓
8. Application ready to accept requests
```

**Code Trace:**

```python
# main.py - Entry point

# Step 1: Imports (run at module load time)
from fastapi import FastAPI
from database import check_database_health, close_db  # Imports database.py

# Step 2: Lifespan function definition
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs at startup and shutdown"""
    print("ReturnPilot API starting up...")  # ← Prints at startup
    yield  # ← Application runs here (handles requests)
    await close_db()  # ← Runs at shutdown, closes DB connections
    print("ReturnPilot API shut down gracefully")

# Step 3: Create FastAPI app instance
app = FastAPI(
    title="ReturnPilot API",
    lifespan=lifespan  # ← Registers lifespan manager
)

# Step 4: Add CORS middleware
app.add_middleware(CORSMiddleware, ...)  # ← Allows frontend to make requests

# Step 5: Register routes
@app.get("/api/health")  # ← Route decorator (registers endpoint)
async def health_check():
    """Health check endpoint"""
    # This function doesn't run yet—only registered for later calls
    pass

# Step 6: Start server (only if run directly)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # ← Starts HTTP server
```

---

## Request Lifecycle: Health Check Example

Let's trace a complete request: `GET /api/health`

### Request Flow Diagram

```
Browser/Client
    ↓ HTTP GET /api/health
uvicorn HTTP Server
    ↓
FastAPI CORS Middleware (checks origin)
    ↓
FastAPI Router (matches route: @app.get("/api/health"))
    ↓
health_check() function in main.py
    ↓
check_database_health() function in database.py
    ↓
AsyncSessionLocal() creates database session
    ↓
session.execute(text("SELECT 1")) - Sends SQL to PostgreSQL
    ↓ (waits for database response)
PostgreSQL Database returns result
    ↓
check_database_health() returns dict
    ↓
health_check() returns JSON response
    ↓
FastAPI serializes response to JSON
    ↓
CORS headers added to response
    ↓
uvicorn sends HTTP response
    ↓
Browser/Client receives response
```

### Code Execution Trace

**Step 1: Request arrives at health_check()**

```python
# main.py
@app.get("/api/health")
async def health_check():
    # Step 1.1: Call database health check function
    db_health = await check_database_health()  # ← Jumps to database.py
    
    # Step 1.4: Return response (after check_database_health completes)
    return {
        "status": "ok" if db_health.get("connected") else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_health
    }
```

**Step 2: Execution jumps to check_database_health()**

```python
# database.py
async def check_database_health() -> dict:
    try:
        # Step 2.1: Create async database session
        async with AsyncSessionLocal() as session:  # ← Creates session
            
            # Step 2.2: Execute test query
            result = await session.execute(text("SELECT 1 as health_check"))
            # ↑ This sends SQL to PostgreSQL and waits for response
            
            # Step 2.3: Fetch result (proves connection works)
            result.scalar()
            
            # Step 2.4: Get connection pool stats
            pool = engine.pool
            
            # Step 2.5: Return success data
            return {
                "connected": True,
                "database": "postgresql",
                "pool_size": pool.size(),
                "pool_checkedout": pool.checkedout(),
            }
    except Exception as e:
        # Step 2.6: Return error if database fails
        logger.error(f"Database health check failed: {e}")
        return {
            "connected": False,
            "error": str(e)
        }
```

**Step 3: Session creation (AsyncSessionLocal)**

```python
# database.py (module-level code, runs at import time)

# This code ran during startup (when database.py was imported)
engine = create_async_engine(DATABASE_URL, ...)  # ← Created connection pool
AsyncSessionLocal = async_sessionmaker(engine, ...)  # ← Created session factory

# When health_check() calls AsyncSessionLocal(), this happens:
# 1. Session factory gets connection from pool
# 2. Connection is validated (pool_pre_ping=True)
# 3. AsyncSession object is created
# 4. Context manager (__aenter__) is called
# 5. Session is ready to execute queries
```

**Step 4: Response flows back**

```python
# Execution returns to health_check()
db_health = {
    "connected": True,
    "database": "postgresql",
    "pool_size": 10,
    "pool_checkedout": 1
}

# health_check() returns this dict
return {
    "status": "ok",  # ← Computed from db_health["connected"]
    "timestamp": "2024-01-20T10:30:45.123456",
    "database": db_health
}

# FastAPI automatically converts this dict to JSON:
# {
#   "status": "ok",
#   "timestamp": "2024-01-20T10:30:45.123456",
#   "database": {
#     "connected": true,
#     "database": "postgresql",
#     "pool_size": 10
#   }
# }
```

---

## Database Connection Lifecycle

### Module Import Time (Startup)

When `database.py` is imported, this code runs **once**:

```python
# database.py - Module-level code (runs at import time)

# Step 1: Load DATABASE_URL from environment
DATABASE_URL = settings.database_url  # ← From config.py

# Step 2: Convert URL format for asyncpg driver
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://")

# Step 3: Create connection pool (does NOT connect yet, just creates pool)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,       # ← Creates pool with 10 slots
    max_overflow=20,    # ← Can grow to 30 connections under load
)

# Step 4: Create session factory (template for creating sessions)
AsyncSessionLocal = async_sessionmaker(engine, ...)

# No database connections are made yet!
# Connections are created lazily when first query runs.
```

### Request Time (Connection Acquisition)

When a request needs the database:

```python
# Example: get_orders endpoint
@app.get("/api/orders")
async def get_orders(db: AsyncSession = Depends(get_db)):
    # ← FastAPI calls get_db() before running this function
    result = await db.execute(select(Order))
    return result.scalars().all()
```

**Execution trace of `Depends(get_db)`:**

```python
# database.py
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Step 1: Create session (gets connection from pool)
    async with AsyncSessionLocal() as session:
        # ↑ This line:
        # - Checks if pool has available connection
        # - If yes: reuses existing connection
        # - If no: creates new connection (up to max_overflow limit)
        # - If pool full: waits up to pool_timeout (30 seconds)
        
        try:
            # Step 2: Yield session to endpoint function
            yield session  # ← get_orders() runs here with session
            
            # Step 3: Commit transaction (if no exceptions)
            await session.commit()  # ← Saves all changes to database
            
        except Exception as e:
            # Step 4: Rollback on error
            await session.rollback()  # ← Undoes changes
            logger.error(f"Database session error: {e}")
            raise  # ← Re-raises exception to FastAPI
            
        finally:
            # Step 5: Close session (returns connection to pool)
            await session.close()  # ← Connection goes back to pool
```

**Connection Pool State Changes:**

```
Initial state:
  Pool size: 10
  Available: 10
  In use: 0

Request 1 arrives:
  Pool size: 10
  Available: 9  ← One connection taken
  In use: 1

Request 2-10 arrive:
  Pool size: 10
  Available: 0  ← All base connections taken
  In use: 10

Request 11 arrives:
  Pool size: 11  ← Overflow connection created
  Available: 0
  In use: 11

Request 1 completes:
  Pool size: 11
  Available: 1  ← Connection returned to pool
  In use: 10
```

---

## Function Call Graph

### Startup Phase

```
main.py (module import)
  ├─ import database
  │   ├─ import config
  │   │   └─ Settings() loads .env variables
  │   ├─ create_async_engine() creates connection pool
  │   └─ async_sessionmaker() creates session factory
  │
  ├─ app = FastAPI(lifespan=lifespan)
  │   └─ lifespan() context manager registered
  │
  ├─ app.add_middleware(CORSMiddleware, ...)
  │
  └─ if __name__ == "__main__":
      └─ uvicorn.run(app, ...)
          └─ HTTP server starts listening
```

### Health Check Request Phase

```
HTTP GET /api/health
  ↓
uvicorn
  ↓
FastAPI routing
  ↓
health_check()
  ├─ await check_database_health()
  │   ├─ async with AsyncSessionLocal() as session
  │   │   ├─ engine.pool.connect() ← Get connection from pool
  │   │   └─ AsyncSession created
  │   ├─ await session.execute(text("SELECT 1"))
  │   │   ├─ SQL sent to PostgreSQL
  │   │   ├─ Waits for response (non-blocking)
  │   │   └─ Result returned
  │   ├─ result.scalar() ← Fetch value
  │   ├─ pool.size() ← Get pool stats
  │   └─ return {"connected": True, ...}
  │
  └─ return {"status": "ok", "database": db_health, ...}
      ↓
FastAPI JSON serialization
  ↓
HTTP response sent
```

### Shutdown Phase

```
Ctrl+C or SIGTERM signal
  ↓
uvicorn starts shutdown
  ↓
lifespan context manager exits
  ↓
await close_db()
  ├─ await engine.dispose()
  │   ├─ Close all active connections
  │   └─ Terminate connection pool
  └─ logger.info("Database connections closed")
```

---

## Database Models and Relationships

### Model Definition Phase (Import Time)

```python
# models/__init__.py

# Step 1: Import Base from database.py
from database import Base  # ← Declarative base for ORM models

# Step 2: Define Customer model
class Customer(Base):
    __tablename__ = "customers"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    # ↑ This doesn't create the table yet!
    # Just defines the structure in Python
    
    # Step 3: Define relationships (lazy-loaded by default)
    orders = relationship("Order", back_populates="customer")
    # ↑ This creates a "virtual" property that loads orders when accessed
```

### Relationship Traversal (Request Time)

```python
# Example: Get customer's orders
customer = await session.get(Customer, customer_id)
# ↑ Executes: SELECT * FROM customers WHERE id = :customer_id

# Access orders relationship
orders = customer.orders  # ← Property access
# ↑ Executes: SELECT * FROM orders WHERE customer_id = :customer_id
# This is a "lazy load" (separate query triggered by property access)

# Eager loading alternative (faster, single query with JOIN)
from sqlalchemy.orm import selectinload

customer = await session.execute(
    select(Customer).options(selectinload(Customer.orders))
    .where(Customer.id == customer_id)
)
# ↑ Executes: 
# SELECT * FROM customers WHERE id = :customer_id
# SELECT * FROM orders WHERE customer_id IN (:customer_id)
# (Uses JOIN-like logic but separate queries for async compatibility)
```

---

## Configuration Loading

### Config Loading Sequence

```
1. Python starts
   ↓
2. Import config.py
   ↓
3. Pydantic Settings() class instantiated
   ↓
4. Pydantic looks for .env file
   ↓
5. Pydantic reads environment variables
   ↓
6. Settings() validates all required variables exist
   ↓
7. If missing: raises ValueError (fails fast)
   ↓
8. If valid: settings object created
   ↓
9. Other modules import settings and read values
```

**Code trace:**

```python
# config.py

# Step 1: Import Pydantic
from pydantic_settings import BaseSettings

# Step 2: Define settings schema
class Settings(BaseSettings):
    database_url: str  # ← Required field (no default)
    anthropic_api_key: str
    # ...
    
    class Config:
        env_file = ".env"  # ← Tells Pydantic to look for .env file

# Step 3: Instantiate settings (runs at module import time)
settings = Settings()  # ← This line:
# 1. Reads .env file (if exists)
# 2. Reads environment variables from OS
# 3. Validates all fields have values
# 4. Raises ValidationError if missing required fields

# Other modules can now import and use settings
from config import settings
print(settings.database_url)  # ← Type-safe access with IDE autocomplete
```

---

## Migration Execution Flow

### Running Migrations

```bash
# Command to run migrations
alembic upgrade head
```

**Execution sequence:**

```
1. alembic CLI reads alembic.ini config file
   ↓
2. alembic connects to database (using DATABASE_URL from env)
   ↓
3. alembic checks alembic_version table (tracks which migrations ran)
   ↓
4. alembic finds migrations in versions/ folder
   ↓
5. For each migration not yet run (in order):
   ├─ Load migration file (e.g., 001_initial_schema.py)
   ├─ Execute upgrade() function
   │   ├─ op.create_table("customers", ...)  ← CREATE TABLE SQL
   │   ├─ op.create_table("orders", ...)
   │   └─ op.create_index(...)  ← CREATE INDEX SQL
   ├─ Insert row into alembic_version table (marks as complete)
   └─ Proceed to next migration
   ↓
6. All migrations complete
```

**Migration code execution:**

```python
# migrations/versions/001_initial_schema.py

def upgrade() -> None:
    """Runs when migrating forward"""
    
    # Step 1: Create customers table
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        # ...
    )
    # ↑ Generates SQL: CREATE TABLE customers (id UUID NOT NULL, name VARCHAR(255) NOT NULL, ...);
    # ↑ Executes SQL against database
    
    # Step 2: Create orders table
    op.create_table('orders', ...)
    # ↑ Generates SQL: CREATE TABLE orders (...);
    
    # Step 3: Create indexes
    op.create_index('idx_orders_customer_id', 'orders', ['customer_id'])
    # ↑ Generates SQL: CREATE INDEX idx_orders_customer_id ON orders (customer_id);

def downgrade() -> None:
    """Runs when rolling back"""
    # Reverse order: drop indexes, then tables
    op.drop_index('idx_orders_customer_id')
    op.drop_table('orders')
    op.drop_table('customers')
```

---

## What Changed in This Session

### Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `backend/config.py` | Created | Environment variable management with Pydantic Settings |
| `backend/database.py` | Created | Async database connection, session factory, health check |
| `backend/models/__init__.py` | Created | SQLAlchemy ORM models (Customer, Order, Return, etc.) |
| `backend/main.py` | Created | FastAPI app entry point, CORS, health check endpoint |
| `backend/migrations/versions/001_initial_schema.py` | Created | Alembic migration to create all database tables |
| `backend/migrations/versions/002_seed_customers.py` | Created | Seed 3 demo customers |
| `backend/migrations/versions/003_seed_return_policies.py` | Created | Seed 6 return policy rules |
| `backend/migrations/versions/004_seed_orders.py` | Created | Seed 24 demo orders |

### Architecture Before (Prototype)

```
ReturnPilot.jsx (single file)
  ├─ Claude API calls (EXPOSED API KEY)
  ├─ In-memory database (dbRef.current = {...})
  ├─ Tool implementations (search_orders, check_policy)
  └─ React UI components
  
Problems:
- API key exposed in browser
- No data persistence (lost on refresh)
- No multi-user support
- Not deployable to production
```

### Architecture After (This Session)

```
Frontend (React)
  └─ Makes HTTP requests to backend

Backend (FastAPI)
  ├─ main.py (entry point)
  ├─ config.py (environment variables)
  ├─ database.py (connection management)
  ├─ models/ (database schema)
  └─ migrations/ (schema version control)
  
Database (PostgreSQL)
  ├─ customers table
  ├─ orders table
  ├─ return_policy table
  ├─ returns table (not yet used)
  └─ return_evidence table (not yet used)

Benefits:
- API keys secure on server
- Data persists across sessions
- Multi-user support via customer_id filtering
- Production-ready deployment
```

### Key Execution Changes

**Before (Prototype):**
```
User clicks "Send" in chat
  ↓
React calls callClaude() function
  ↓
fetch("https://api.anthropic.com/v1/messages", {
    headers: { "x-api-key": EXPOSED_KEY }  // ← SECURITY RISK
})
  ↓
Claude response returned to browser
  ↓
Tool execution happens in browser (execTool function)
  ↓
In-memory database updated (dbRef.current)
```

**After (Current Design - Not Yet Implemented):**
```
User clicks "Send" in chat
  ↓
React calls fetch("http://localhost:8000/api/agent/message", {
    body: { customer_id, message }
})
  ↓
Backend receives request at agent.py router
  ↓
agent_loop.py calls Claude API with server-side API key
  ↓
Claude returns tool_use block
  ↓
Backend executes tool (tools.py) against PostgreSQL database
  ↓
Backend sends tool result back to Claude
  ↓
Claude returns final text response
  ↓
Backend returns response to frontend
  ↓
React displays response in chat
```

---

## Mental Model: How Everything Fits Together

### The Big Picture

Think of the backend as a **factory** with different departments:

1. **Reception (main.py)**: Entry point where all requests arrive
2. **Configuration Office (config.py)**: Stores all settings and credentials
3. **Database Warehouse (database.py)**: Manages connections to the data storage
4. **Blueprint Archive (models/)**: Defines structure of data (tables, relationships)
5. **Construction Crew (migrations/)**: Builds and modifies the database structure

### Request Flow Mental Model

Imagine a **customer support workflow**:

1. **Customer** (browser) calls the support line (`GET /api/health`)
2. **Receptionist** (uvicorn) answers and routes to the right department
3. **Security** (CORS middleware) checks if caller is allowed
4. **Support Agent** (health_check function) handles the request
5. **Database Clerk** (check_database_health) checks records in the filing system
6. **Filing System** (PostgreSQL) provides the data
7. **Clerk** formats the response and sends it back
8. **Customer** receives the answer

### Database Connection Mental Model

Think of the database connection pool as a **taxi stand**:

- **Pool Size (10)**: Number of taxis waiting at the stand
- **Max Overflow (20)**: Additional taxis that can be called if stand is full
- **Pool Timeout (30s)**: How long a customer waits before giving up
- **Pre-Ping**: Driver checks taxi works before customer gets in
- **Recycle (1 hour)**: Taxis get serviced after 1 hour of driving

**Request Handling:**
- Customer (request) arrives at taxi stand (pool)
- Takes available taxi (connection)
- Travels to destination (executes query)
- Returns taxi to stand (connection returned to pool)
- Next customer can use the same taxi

### Migration Mental Model

Think of migrations as **architectural blueprints**:

- **Version 001**: Build foundation (create tables)
- **Version 002**: Add plumbing (seed customers)
- **Version 003**: Add electrical (seed policies)
- **Version 004**: Add furniture (seed orders)

Each blueprint builds on the previous one. If you need to undo:
- **Downgrade**: Remove furniture → Remove electrical → Remove plumbing → Demolish foundation

---

## Quiz Yourself

Before moving forward, ensure you can answer these questions:

### Basic Execution Flow
1. What is the entry point file of the backend?
2. What happens when you import `database.py`?
3. When are database connections actually created?
4. What does `async with AsyncSessionLocal() as session` do?
5. What happens when a function calls `await session.commit()`?

### Function Relationships
6. Which function calls `check_database_health()`?
7. What does `get_db()` yield, and who consumes it?
8. What happens when `engine.dispose()` is called?
9. When does the lifespan context manager's "after yield" code run?
10. What triggers a relationship to lazy-load (e.g., `customer.orders`)?

### Configuration and Setup
11. How does `settings.database_url` get its value?
12. What happens if `DATABASE_URL` environment variable is missing?
13. Why do we convert `postgres://` to `postgresql+asyncpg://`?
14. What is the difference between `pool_size` and `max_overflow`?
15. Why does the code use `pool_pre_ping=True`?

### Migrations
16. What command runs all pending migrations?
17. What is stored in the `alembic_version` table?
18. Why are migrations split into separate files (schema vs seed)?
19. What does `op.create_table()` actually do?
20. How would you undo the last migration?

### Changes in This Session
21. What was the main security problem with the prototype?
22. How does the new architecture solve data persistence?
23. What file manages the database connection pool?
24. Which SQLAlchemy models were created in this session?
25. What is the purpose of the health check endpoint?

---

## Next Steps: What Needs to Be Implemented

### Completed (This Session)
- ✅ Database connection and session management
- ✅ SQLAlchemy ORM models for all tables
- ✅ Database migrations and seed scripts
- ✅ Health check endpoint
- ✅ FastAPI app skeleton with CORS

### Not Yet Implemented
- ❌ Router files (agent.py, orders.py, returns.py, etc.)
- ❌ Tool implementations (search_orders, check_policy, initiate_return)
- ❌ Agent orchestration loop (Claude API integration)
- ❌ Pydantic schemas for request/response validation
- ❌ Notification service integration
- ❌ Photo upload to Supabase Storage
- ❌ Frontend API client (api.ts)
- ❌ Frontend migration to use backend endpoints

**Current execution flow ends at health check. The full agent workflow (Tasks 4-18) is still pending implementation.**

