# Architecture Decision Record (ADR)

## Overview

This document captures **every significant decision** made during the ReturnPilot backend architecture migration. Each decision includes the rationale, alternatives considered, and trade-offs.

---

## Decision 1: FastAPI over Node.js/Express for Backend

**Decision:** Use FastAPI (Python) as the backend framework instead of Node.js/Express

**Why This Approach?**

1. **Native Async/Await**: Python's async/await is cleaner than Node.js callback chains. FastAPI supports async database operations and HTTP calls natively.

2. **Automatic API Documentation**: FastAPI auto-generates OpenAPI/Swagger docs from type hints. Express requires manual documentation or additional libraries (swagger-jsdoc).

3. **Type Safety with Pydantic**: Request/response validation happens automatically via Pydantic v2. In Node.js, you need separate validation libraries (Zod, class-validator, Joi).

4. **Better for AI/ML Ecosystem**: Python aligns with machine learning libraries if we need embeddings, classification, or model integration in the future.

**Alternatives Considered:**
- **Node.js/Express**: Would match the frontend (React/JavaScript) but lacks built-in validation and type safety
- **Django**: Too heavy for an API-only backend; includes unnecessary ORM features and templating

**Trade-offs:**
- ✅ **Pro**: Stronger type safety, better developer experience, automatic docs
- ❌ **Con**: Separate language from frontend (but frontend is thin client, so minimal impact)

**References:**
- [FastAPI vs Express Comparison](https://keyholesoftware.com/express-vs-fastapi-api-framework-comparison/)
- [FastAPI Async Documentation](https://fastapi.tiangolo.com/async/)

---

## Decision 2: SQLAlchemy ORM over Raw SQL

**Decision:** Use SQLAlchemy 2.0 ORM for database operations instead of raw SQL queries

**Why This Approach?**

1. **Type-Safe Query Building**: SQLAlchemy provides IDE autocomplete and compile-time checking for queries
2. **Relationship Management**: Automatic handling of foreign key relationships and lazy/eager loading
3. **Migration Support**: Alembic (SQLAlchemy's migration tool) provides version-controlled schema changes
4. **Protection Against SQL Injection**: Parameterized queries are automatic with ORM

**Why Not Raw SQL?**
- Raw SQL is faster to write initially but becomes unmaintainable as relationships grow
- No compile-time safety—typos in column names only discovered at runtime
- Manual parameter escaping required to prevent SQL injection

**Trade-offs:**
- ✅ **Pro**: Type safety, maintainability, automatic relationship handling
- ❌ **Con**: Slight performance overhead compared to raw SQL (negligible for this scale)

**Code Evidence:**
```python
# SQLAlchemy approach (type-safe, relationship-aware)
order = await session.get(Order, order_id)
policy = order.policy  # Automatic relationship traversal
customer_name = order.customer.name

# Raw SQL equivalent (error-prone, verbose)
result = await conn.execute(
    "SELECT o.*, c.name, p.window_days FROM orders o "
    "JOIN customers c ON o.customer_id = c.id "
    "JOIN return_policy p ON o.category = p.category "
    "WHERE o.id = %s", (order_id,)
)
```

---

## Decision 3: Async SQLAlchemy with asyncpg Driver

**Decision:** Use async SQLAlchemy with asyncpg driver instead of sync psycopg2

**Why This Approach?**

1. **Non-Blocking I/O**: Async database queries don't block the event loop, allowing FastAPI to handle other requests while waiting for database responses
2. **Better Concurrency**: Supports hundreds of concurrent requests without thread overhead
3. **Consistent with FastAPI**: FastAPI is async-native; using sync DB would block the event loop and degrade performance

**Why Not Sync psycopg2?**
- Sync drivers block the entire event loop during database queries
- Would require running DB queries in thread pools (adds complexity)
- Contradicts FastAPI's async design philosophy

**Trade-offs:**
- ✅ **Pro**: True async concurrency, no thread blocking
- ❌ **Con**: Slightly more complex setup (must use `async with` and `await`)

**Code Evidence:**
```python
# Async approach (non-blocking)
async with AsyncSessionLocal() as session:
    result = await session.execute(select(Order))  # Other requests can run during this wait
    orders = result.scalars().all()

# Sync approach (blocks event loop)
with SessionLocal() as session:
    result = session.execute(select(Order))  # Entire app blocked here
    orders = result.scalars().all()
```

---

## Decision 4: Connection Pooling Configuration

**Decision:** Configure production-ready connection pool with these settings:
- `pool_size=10` (base connections)
- `max_overflow=20` (additional connections under load)
- `pool_recycle=3600` (recycle after 1 hour)
- `pool_pre_ping=True` (validate before use)

**Why These Numbers?**

1. **pool_size=10**: Based on expected concurrent requests. Render/production can handle ~50 requests/sec; 10 connections with avg 100ms query time = 100 requests/sec capacity.

2. **max_overflow=20**: Allows bursts up to 30 total connections during traffic spikes without rejecting requests.

3. **pool_recycle=3600**: PostgreSQL closes idle connections after a timeout. Recycling every hour prevents stale connection errors.

4. **pool_pre_ping=True**: Validates connection is alive before using it. Prevents "connection closed" errors after database restarts.

**Why Not Unlimited Connections?**
- Databases have connection limits (Supabase free tier: 60 connections)
- Too many connections degrade database performance (context switching overhead)

**Trade-offs:**
- ✅ **Pro**: Handles production load without exhausting database connections
- ❌ **Con**: Requests wait up to 30 seconds (`pool_timeout`) if all connections are busy

**Code Evidence:**
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # Base connections always available
    max_overflow=20,     # Extra connections during bursts
    pool_recycle=3600,   # Prevent stale connections
    pool_timeout=30,     # Max wait time for connection
    pool_pre_ping=True,  # Validate before use
)
```

---

## Decision 5: Dependency Injection for Database Sessions

**Decision:** Use FastAPI's `Depends(get_db)` for database session injection instead of global session

**Why This Approach?**

1. **Automatic Lifecycle Management**: Session is created per-request and automatically closed after response
2. **Transaction Safety**: Automatic commit on success, rollback on exception
3. **Testability**: Easy to mock database sessions in tests by overriding the dependency
4. **No Manual Cleanup**: FastAPI's context manager ensures sessions are always closed

**Why Not Global Session?**
- Global sessions risk connection leaks if not manually closed
- Hard to test (global state makes mocking difficult)
- Not thread-safe or async-safe

**Trade-offs:**
- ✅ **Pro**: Automatic cleanup, testable, no connection leaks
- ❌ **Con**: Slightly more verbose (must inject `db: AsyncSession = Depends(get_db)`)

**Code Evidence:**
```python
# Dependency injection approach (automatic cleanup)
@app.get("/api/orders")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order))
    return result.scalars().all()
    # Session automatically closed here, even if exception occurs

# Global session approach (manual cleanup, error-prone)
@app.get("/api/orders")
async def get_orders():
    session = AsyncSessionLocal()
    try:
        result = await session.execute(select(Order))
        return result.scalars().all()
    finally:
        await session.close()  # Must remember to close manually
```

---

## Decision 6: Alembic for Database Migrations

**Decision:** Use Alembic for database schema versioning instead of raw SQL scripts

**Why This Approach?**

1. **Version Control**: Each migration is tracked with revision IDs, allowing forward/backward migration
2. **Automatic Schema Diffing**: Alembic can detect differences between models and database schema
3. **Rollback Support**: Can revert to previous schema versions with `alembic downgrade`
4. **Production Safety**: Migrations run in order, preventing schema inconsistencies

**Why Not Raw SQL Scripts?**
- No version tracking—hard to know which scripts have run
- No rollback support—manual SQL required to undo changes
- Error-prone in team environments (conflicting scripts)

**Trade-offs:**
- ✅ **Pro**: Version control, rollback support, team collaboration
- ❌ **Con**: Learning curve for Alembic syntax

**Code Evidence:**
```python
# Alembic migration (version controlled, reversible)
def upgrade() -> None:
    op.create_table('customers', ...)

def downgrade() -> None:
    op.drop_table('customers')  # Automatic rollback

# Raw SQL approach (no version control, no rollback)
CREATE TABLE customers (...);  # How to undo? Manual DROP TABLE
```

---

## Decision 7: UUID for Primary Keys (Customers)

**Decision:** Use UUID for `customers.id` instead of auto-incrementing integers

**Why This Approach?**

1. **Globally Unique**: UUIDs are unique across databases, enabling multi-region replication without ID conflicts
2. **Security**: No enumeration attacks (can't guess next customer ID by incrementing)
3. **Distributed Systems**: Works in distributed systems where central ID generation is impractical

**Why Not Auto-Increment Integers?**
- Exposes business metrics (customer count via ID)
- Vulnerable to enumeration attacks
- Requires coordination in distributed systems

**Trade-offs:**
- ✅ **Pro**: Security, distributed system support, no enumeration attacks
- ❌ **Con**: Slightly larger storage (16 bytes vs 4-8 bytes)

**Code Evidence:**
```python
class Customer(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Auto-generates globally unique ID on insert
```

---

## Decision 8: Human-Readable IDs for Orders and Returns

**Decision:** Use human-readable string IDs (ORD-1001, RET-1001) instead of UUIDs

**Why This Approach?**

1. **Customer Communication**: Easier for customers to reference in support calls ("My order is ORD-1042")
2. **Debugging**: Developers can quickly identify order/return records in logs
3. **Sequential Ordering**: Implicit chronological ordering (ORD-1001 came before ORD-1002)

**Why Not UUIDs?**
- UUIDs are hard for humans to remember and communicate
- No inherent ordering (can't tell which came first)

**Trade-offs:**
- ✅ **Pro**: Human-friendly, debuggable, sequential
- ❌ **Con**: Requires ID generation logic (manual or trigger-based)

**Implementation Note:**
IDs are generated in application code (Python) during insertion:
```python
async def initiate_return(order_id: str, reason: str) -> str:
    # Get max return ID and increment
    result = await session.execute(select(func.max(Return.id)))
    max_id = result.scalar()
    next_num = int(max_id.split('-')[1]) + 1 if max_id else 1
    return_id = f"RET-{next_num:04d}"
    return return_id
```

---

## Decision 9: JSONB for agent_reasoning_log

**Decision:** Store agent reasoning traces as JSONB instead of separate `tool_executions` table

**Why This Approach?**

1. **Flexibility**: JSONB allows variable structure (different tools have different parameters)
2. **Performance**: Single JSONB column is faster to query than JOIN across multiple tables
3. **Atomicity**: Reasoning trace is always consistent with return record (no orphaned tool execution records)

**Why Not Separate Table?**
- Requires complex JOINs to reconstruct reasoning trace
- Over-normalization adds query complexity without benefit
- Tool parameters vary widely (no fixed schema)

**Trade-offs:**
- ✅ **Pro**: Flexible schema, atomic updates, fast queries
- ❌ **Con**: Can't easily query individual tool executions (but we don't need that)

**Data Example:**
```json
{
  "agent_reasoning_log": [
    {
      "tool": "search_orders",
      "input": {"query": "blue sneakers"},
      "result": [{"order_id": "ORD-1001", "item_name": "Blue Running Sneakers"}]
    },
    {
      "tool": "check_policy",
      "input": {"order_id": "ORD-1001"},
      "result": {"eligible": true, "window_days": 30}
    }
  ]
}
```

---

## Decision 10: Pydantic Settings for Configuration

**Decision:** Use Pydantic Settings for environment variable management instead of manual `os.getenv()`

**Why This Approach?**

1. **Type Safety**: Environment variables are typed and validated on startup
2. **Validation**: Pydantic validates required variables exist (fails fast if missing)
3. **IDE Support**: Autocomplete for `settings.database_url` vs `os.getenv("DATABASE_URL")`
4. **.env File Support**: Automatically loads from `.env` file in development

**Why Not `os.getenv()`?**
- No type safety (always returns string or None)
- No validation (missing vars only discovered at runtime when used)
- No IDE autocomplete

**Trade-offs:**
- ✅ **Pro**: Type safety, fail-fast validation, better developer experience
- ❌ **Con**: Requires Pydantic dependency (but we're already using it for request/response validation)

**Code Evidence:**
```python
# Pydantic Settings (type-safe, validated)
class Settings(BaseSettings):
    database_url: str  # Fails at startup if missing
    anthropic_api_key: str

settings = Settings()
engine = create_async_engine(settings.database_url)  # IDE autocomplete

# os.getenv (no validation, no types)
DATABASE_URL = os.getenv("DATABASE_URL")  # Could be None, only fails when used
engine = create_async_engine(DATABASE_URL)  # Runtime error if None
```

---

## Decision 11: CORS Middleware Configuration

**Decision:** Use environment-based CORS origins instead of allowing all origins (`*`)

**Why This Approach?**

1. **Security**: Prevents malicious websites from making requests to the API
2. **Production Safety**: Only whitelisted origins (frontend domain) can access the API
3. **Flexibility**: Can add multiple origins (local dev, staging, production)

**Why Not Allow All (`*`)?**
- Security risk: any website could make requests to the API
- CORS exists to prevent cross-site attacks; allowing all defeats the purpose

**Trade-offs:**
- ✅ **Pro**: Secure, production-ready, prevents unauthorized access
- ❌ **Con**: Must update CORS_ORIGINS when deploying to new domains

**Code Evidence:**
```python
# Environment-based CORS (secure)
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Only whitelisted origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Allow all (insecure)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Any website can access API
)
```

---

## Decision 12: Health Check Endpoint Design

**Decision:** Implement `/api/health` endpoint with database connectivity check

**Why This Approach?**

1. **Deployment Monitoring**: Render/Vercel use health checks to verify service is running
2. **Database Verification**: Checks both application and database health
3. **Graceful Degradation**: Returns "degraded" status if database is down (instead of 500 error)

**Why Not Simple "OK" Response?**
- Doesn't verify database connectivity
- Can't distinguish between app and database failures

**Trade-offs:**
- ✅ **Pro**: Comprehensive health monitoring, catches database issues
- ❌ **Con**: Adds latency to health checks (but only ~10ms)

**Code Evidence:**
```python
@app.get("/api/health")
async def health_check():
    db_health = await check_database_health()  # Verifies DB connection
    
    return {
        "status": "ok" if db_health.get("connected") else "degraded",
        "database": db_health,
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Decision 13: Lifespan Context Manager for Cleanup

**Decision:** Use FastAPI's lifespan context manager for database cleanup instead of `@app.on_event`

**Why This Approach?**

1. **Modern FastAPI Pattern**: `@app.on_event` is deprecated in FastAPI 0.109+
2. **Context Safety**: Lifespan ensures cleanup runs even if startup fails
3. **Better Resource Management**: Single location for all startup/shutdown logic

**Why Not `@app.on_event("shutdown")`?**
- Deprecated in newer FastAPI versions
- Less explicit about lifecycle dependencies

**Trade-offs:**
- ✅ **Pro**: Modern pattern, safer resource management
- ❌ **Con**: Slightly more verbose than decorator pattern

**Code Evidence:**
```python
# Lifespan context manager (modern)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Startup...")
    yield
    await close_db()  # Always runs, even if startup failed

app = FastAPI(lifespan=lifespan)

# Old pattern (deprecated)
@app.on_event("shutdown")
async def shutdown():
    await close_db()  # May not run if startup failed
```

---

## Decision 14: Database URL Conversion for Async Driver

**Decision:** Automatically convert `postgres://` to `postgresql+asyncpg://` in connection string

**Why This Approach?**

1. **Supabase Compatibility**: Supabase provides URLs in `postgres://` format
2. **Asyncpg Requirement**: Async SQLAlchemy requires explicit `+asyncpg` driver specification
3. **Zero Configuration**: Works with Supabase URLs without manual editing

**Why Not Require Manual Editing?**
- Error-prone (easy to forget `+asyncpg`)
- Developer friction (must remember to edit URL)

**Trade-offs:**
- ✅ **Pro**: Works with Supabase URLs out of the box
- ❌ **Con**: Magic string replacement (but documented in comments)

**Code Evidence:**
```python
# Automatic conversion (zero config)
DATABASE_URL = settings.database_url.replace("postgres://", "postgresql://", 1)
if "postgresql://" in DATABASE_URL and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Manual approach (requires editing .env)
# User must remember: DATABASE_URL=postgresql+asyncpg://...
```

---

## Decision 15: Indexes on Frequently Queried Columns

**Decision:** Create indexes on `customer_id`, `purchase_date`, and `status` columns

**Why These Columns?**

1. **customer_id**: Every order and return query filters by customer (multi-user support)
2. **purchase_date**: Used for calculating eligibility windows and date-based searches
3. **status**: Dashboard queries filter by return status (initiated, refunded, etc.)

**Performance Impact:**
- Without indexes: O(n) table scan for every query
- With indexes: O(log n) lookup (100x faster for 10,000+ records)

**Trade-offs:**
- ✅ **Pro**: Dramatically faster queries as data grows
- ❌ **Con**: Slight insert/update overhead (must update indexes)

**Code Evidence:**
```python
# Indexes created in migration
op.create_index('idx_orders_customer_id', 'orders', ['customer_id'])
op.create_index('idx_orders_purchase_date', 'orders', ['purchase_date'])
op.create_index('idx_returns_status', 'returns', ['status'])
```

---

## Decision 16: Separate Migration Files for Schema and Seed Data

**Decision:** Split database setup into 4 migrations:
1. `001_initial_schema.py` - Create all tables
2. `002_seed_customers.py` - Seed demo customers
3. `003_seed_return_policies.py` - Seed return policies
4. `004_seed_orders.py` - Seed demo orders

**Why This Approach?**

1. **Separation of Concerns**: Schema changes are separate from data changes
2. **Reusability**: Can run schema migration without seed data in production
3. **Rollback Granularity**: Can revert seed data without affecting schema
4. **Clarity**: Each migration has a single, clear purpose

**Why Not Single Migration?**
- Mixing schema and data makes migrations harder to understand
- Can't selectively apply schema without seed data
- Rollbacks become all-or-nothing

**Trade-offs:**
- ✅ **Pro**: Clear purpose per migration, selective application, better rollback
- ❌ **Con**: More files to manage (but better organization)

---

## Decision 17: Google AI Studio (Gemini) over Anthropic Claude for Orchestration & Vision

**Decision:** Migrate the multi-agent orchestrator, NLP classification layer, and photo damage verification from direct Anthropic Claude API to Google AI Studio's OpenAI-compatible endpoint (using `gemini-3.5-flash-lite` as the primary model).

**Why This Approach?**

1. **Free Tier & Quota Separation**: Google AI Studio provides a free tier without a credit card, tracked separately *per model* — confirmed empirically during development when `gemini-3.6-flash`'s free tier turned out to cap at just 20 requests/day (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, visible in the 429 error body), which a single chat turn can exceed on its own (NLP classification + multiple orchestrator tool-loop calls). Switching `GOOGLE_MODEL` to `gemini-3.5-flash-lite` picked up a separate, much larger daily quota untouched by the first model's usage — the per-model quota isolation is what makes that failover work, but don't assume any specific number without checking https://ai.dev/rate-limit, since these change and vary a lot by model.
2. **Unified Vision Capabilities**: A single API key and endpoint covers text reasoning AND visual inspection (photo verification), simplifying our service layer.
3. **OpenAI Compatibility**: Using the OpenAI-compatible chat completions endpoint allows us to standardise tool definitions, base64 payloads, and reasoning parameters using standard formats.
4. **Empirical Performance**: Flash-lite is fast (under 2 seconds latency) and cheap, making it highly responsive for interactive user demos.

**Alternatives Considered:**
- **Anthropic Claude direct API**: Highly capable but requires upfront payment and has strict rate limits during development.
- **OpenRouter**: Good failover option, but direct Google AI Studio endpoint offers better latency and zero intermediary fees.

---

## Decision 18: CLI Chat Interface for Development and Offline Demonstration

**Decision:** Build a standalone, interactive Python CLI chat tool (`cli_chat.py`) that executes in the virtual environment.

**Why This Approach?**

1. **Bypass Browser/CORS Security Policies**: Local files opened directly via `file://` protocol are blocked by browsers because the origin is evaluated as `null`. A CLI bypasses this, making testing straightforward.
2. **Real-time Terminal Tracing**: The CLI automatically prints out the multi-agent logic flow (`nlp_analyzer` classification, tool invocation names, etc.) in a human-readable trace immediately below each response.
3. **Reliable Demo Fallback**: Eliminates UI rendering and network connection errors during live mentor judging.

---

## Decision 19: FastAPI/Gemini Backend as the Submission, Not the Parallel viaSocket Build

**Decision:** This repository's FastAPI + Gemini backend (`backend/`) is the system submitted for judging. A parallel viaSocket-native build made by a teammate on a separate machine, using the same problem statement, was evaluated as a possible alternative or bonus demo and rejected for that role after direct testing.

**Why This Approach?**

1. **Verifiability**: viaSocket's "implementation" is no-code workflow configuration inside a third-party UI with no traditional source code — it cannot be verified from a git repository the way the judging methodology expects (see `VIASOCKET_ARCHITECTURE.md`).
2. **Reliability under live testing**: Direct testing against the viaSocket build's production endpoints (both via browser and via `curl`) found a hard 58-second platform execution timeout on multi-step turns, at least one case of a write silently succeeding behind a shown error, weak duplicate-return handling, and — most seriously — a reproduced instance of the agent fabricating a complete, plausible transaction confirmation (reasoning trace, policy justification, claimed database write, claimed email) in 2.2 seconds with zero real tool execution behind it. Full detail and reproduction evidence in `VIASOCKET_ARCHITECTURE.md`.
3. **No equivalent failure found in the actual backend**: The same category of end-to-end flow (order lookup → policy check → return creation → notification) has been extensively live-tested against `backend/` via `cli_chat.py` without finding an analogous silent-failure or fabrication case.

**Alternatives Considered:**
- **Lead with the viaSocket build as the main demo**: rejected — a live audience cannot distinguish a fabricated "success" response from a real one, which is disqualifying for a live demo regardless of how compelling the no-code pitch is.
- **Present both builds as co-equal**: rejected for the write path specifically; a read-only walkthrough of viaSocket's tool-calling/reasoning-trace behavior remains a defensible talking point, documented as an alternative explored, not as a working product.

**Trade-offs:**
- ✅ **Pro**: The submitted system is the one that's actually been verified end-to-end, and is inspectable via source code as the judging methodology expects.
- ❌ **Con**: The viaSocket track's sponsorship angle isn't showcased as the headline, only as a documented exploration.

**References:** `VIASOCKET_ARCHITECTURE.md`

---

## Summary of Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Type safety, async support, auto docs |
| Database ORM | SQLAlchemy 2.0 | Type-safe queries, relationship management |
| Database Driver | asyncpg | Non-blocking I/O, true async support |
| Customer IDs | UUID | Security, distributed systems, no enumeration |
| Order/Return IDs | String (ORD-1001) | Human-readable, debuggable, sequential |
| Reasoning Log Storage | JSONB | Flexible schema, atomic updates, fast queries |
| Configuration | Pydantic Settings | Type safety, validation, fail-fast |
| Migrations | Alembic | Version control, rollback support |
| Session Management | Dependency Injection | Automatic cleanup, testable, no leaks |
| Connection Pooling | 10 base, 20 overflow | Production-ready, handles burst traffic |
| AI Orchestrator | Gemini (Google AI Studio) | OpenAI-compatible, free-tier, unified vision/text |
| Developer Testing | Python CLI Chat | Bypasses browser CORS constraints, prints live trace |

---

## Future Decision Points

**When Feature X is Needed:**
- **Real-time Dashboard Updates**: Consider WebSockets vs Server-Sent Events vs polling
- **Image Processing**: Add image compression service vs client-side compression
- **Multi-Region Deployment**: Consider connection pooling per region vs global pool
- **Audit Logging**: Add separate audit table vs extend existing tables with audit fields


