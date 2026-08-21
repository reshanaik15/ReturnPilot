# Design Document: Backend Architecture Migration

## Overview

This design transforms the ReturnPilot single-file React prototype into a production-ready full-stack application following a three-tier architecture pattern. The migration separates concerns into: a React frontend for the user interface, a FastAPI backend for business logic and agent orchestration, and a Supabase PostgreSQL database for data persistence.

The current prototype exposes API keys in the browser and maintains all state in memory, making it unsuitable for production use. The new architecture addresses these limitations by implementing proper security boundaries, data persistence, multi-user support, and deployment-ready infrastructure.

### Key Design Principles

1. **Security by Architecture**: Credentials never leave the server boundary
2. **Statelessness**: Backend derives state from database, enabling horizontal scaling
3. **Database-First Authorization**: Customer data isolation enforced at the database layer through WHERE clauses
4. **API Contract Stability**: Existing UI components remain unchanged; only API integration layer is modified
5. **Production Readiness**: Deployable to Vercel (frontend) and Render (backend) with environment-based configuration

### Technology Stack Selection

**Backend Framework: FastAPI (Python)**
- Native async/await support for Claude API orchestration loops (per [official FastAPI docs](https://fastapi.tiangolo.com/async/))
- Automatic OpenAPI schema generation for frontend client generation
- Pydantic v2 validation reduces boilerplate for request/response schemas
- Rich ecosystem for database (SQLAlchemy 2.0) and async HTTP (httpx)
- Python aligns with ML/AI tooling if future features require model integration

**Database: Supabase PostgreSQL**
- Managed PostgreSQL with built-in authentication and storage ([Supabase Auth architecture](https://supabase.com/docs/guides/auth/architecture))
- Row Level Security (RLS) policies for multi-tenant data isolation ([RLS documentation](https://supabase.com/docs/guides/database/postgres/row-level-security))
- Supabase Storage for photo evidence with CDN-backed public URLs
- Database connection pooling and automatic backups included in managed service

**Deployment Targets**
- Frontend: Vercel (automatic builds from Git, edge network distribution)
- Backend: Render (managed containers with health checks and automatic deploys)
- Both platforms support environment variable injection for secrets management

## Architecture

### High-Level Architecture Diagram

```mermaid
graph TB
    Browser[React Frontend<br/>Vercel]
    API[FastAPI Backend<br/>Render]
    DB[(Supabase PostgreSQL)]
    Storage[Supabase Storage<br/>Photo Evidence]
    Claude[Claude API<br/>Anthropic]
    Notify[Notification Service<br/>viaSocket/Twilio/SendGrid]
    
    Browser -->|HTTPS REST| API
    API -->|SQL via psycopg| DB
    API -->|HTTP PUT/GET| Storage
    API -->|HTTP POST| Claude
    API -->|HTTP POST| Notify
    Storage -.->|Public URL| Browser
    
    style Browser fill:#e1f5ff
    style API fill:#fff4e1
    style DB fill:#e8f5e9
    style Claude fill:#f3e5f5
    style Storage fill:#e8f5e9
    style Notify fill:#fff3e0
```

### Component Interactions

**Customer Return Flow**:
1. Customer sends message via React chat interface
2. Frontend POST /api/agent/message with customer_id, text, optional image
3. Backend enters tool-use orchestration loop:
   - Sends message + tool definitions to Claude API
   - Receives tool_use blocks or final text response
   - Executes tools against database (search_orders, check_policy, etc.)
   - Sends tool results back to Claude API
   - Repeats until Claude returns text without tool_use (max 6 iterations)
4. Backend returns final response with reasoning trace to frontend
5. Frontend displays assistant message and updates trace panel

**Business Dashboard Flow**:
1. Business user opens dashboard view
2. Frontend GET /api/dashboard/returns
3. Backend queries returns table with joins to orders, customers
4. Returns all records without customer_id filtering (business-wide view)
5. Frontend polls endpoint every 5 seconds for real-time updates
6. Business user can advance status or resolve flagged reviews via POST endpoints

### Security Boundaries

**API Key Management**: Claude API key stored in backend environment variable (ANTHROPIC_API_KEY). Frontend never receives or transmits API keys.

**Customer Data Isolation**: All customer-scoped endpoints (orders, returns) filter queries by customer_id from request. Business dashboard endpoints omit customer_id filter to show all records.

**Database Connection Security**: PostgreSQL connection string stored in backend environment (DATABASE_URL). Frontend has no direct database access.

**Request Validation**: Pydantic schemas validate all incoming requests. Invalid requests return 400 status with error details before reaching business logic.

## Components and Interfaces

### Frontend Components (React)

**Preserved Components** (no changes to UI logic):
- `LoginScreen`: Customer selection interface
- `ChatView`: Message display, input, trace panel
- `Dashboard`: Return records table with status controls
- `StatusPill`: Return status visual indicators
- `TraceStep`: Reasoning step display

**Modified Component** (API integration only):
- `App`: Replace direct Claude API calls with backend endpoint calls
  - `callClaude()` → `fetch('/api/agent/message')`
  - Tool execution logic moves to backend
  - State management remains in React (messages, trace, returns)

**New API Client Module** (`api.ts`):
```typescript
// Centralized API client with error handling
export const api = {
  sendMessage: (customerId: string, message: string, image?: File) => 
    fetch(`${API_BASE_URL}/api/agent/message`, { method: 'POST', ... }),
  searchOrders: (customerId: string, query: string) => 
    fetch(`${API_BASE_URL}/api/orders/search?customer_id=${customerId}&q=${query}`),
  getReturn: (returnId: string) => 
    fetch(`${API_BASE_URL}/api/returns/${returnId}`),
  // ... additional endpoints
}
```

### Backend Components (FastAPI)

**Application Structure**:
```
backend/
├── main.py                 # FastAPI app, CORS, health check
├── routers/
│   ├── agent.py            # POST /api/agent/message
│   ├── orders.py           # GET /api/orders/search
│   ├── returns.py          # POST /api/returns/initiate, GET /api/returns/:id, etc.
│   ├── dashboard.py        # GET /api/dashboard/returns
│   └── policy.py           # GET /api/policy/check
├── models/
│   ├── database.py         # SQLAlchemy models (Customer, Order, Return, etc.)
│   └── schemas.py          # Pydantic request/response schemas
├── services/
│   ├── agent_loop.py       # Claude tool-use orchestration loop
│   ├── tools.py            # Tool implementations (search_orders, check_policy, etc.)
│   └── notifications.py    # Notification service integration
├── database.py             # Database connection, session management
└── config.py               # Environment variable configuration
```

**Key Service: Agent Orchestration Loop** (`services/agent_loop.py`):
```python
async def agent_turn(
    customer_id: str,
    message: str,
    conversation_history: List[dict],
    image_base64: Optional[str] = None
) -> dict:
    """
    Orchestrates Claude tool-use loop until text response is returned.
    Returns: {
        "response": str,
        "reasoning_trace": List[dict],  # Tool calls and results
        "iterations": int
    }
    """
    trace = []
    history = conversation_history.copy()
    
    # Build user message with optional image
    user_content = [{"type": "text", "text": message}]
    if image_base64:
        user_content.insert(0, {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}
        })
    history.append({"role": "user", "content": user_content})
    
    for iteration in range(6):  # Max 6 iterations per requirement
        response = await call_claude_api(
            system=SYSTEM_PROMPT.format(customer_id=customer_id),
            messages=history,
            tools=TOOL_DEFINITIONS
        )
        
        history.append({"role": "assistant", "content": response["content"]})
        
        tool_uses = [block for block in response["content"] if block["type"] == "tool_use"]
        
        if not tool_uses:
            # Final text response
            text_blocks = [block for block in response["content"] if block["type"] == "text"]
            return {
                "response": " ".join(b["text"] for b in text_blocks),
                "reasoning_trace": trace,
                "iterations": iteration + 1
            }
        
        # Execute tools and build results
        tool_results = []
        for tool_call in tool_uses:
            result = await execute_tool(tool_call["name"], tool_call["input"], customer_id)
            trace.append({
                "tool": tool_call["name"],
                "input": tool_call["input"],
                "result": result
            })
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call["id"],
                "content": json.dumps(result)
            })
        
        history.append({"role": "user", "content": tool_results})
    
    # Exceeded iteration limit
    return {
        "response": "I've gathered information but need to continue this conversation. Could you clarify your request?",
        "reasoning_trace": trace,
        "iterations": 6
    }
```

**Tool Implementations** (`services/tools.py`):
- `search_orders(customer_id, query)`: Query orders table with text matching and date heuristics
- `check_policy(order_id)`: Join orders and return_policy tables, calculate days since purchase
- `initiate_return(order_id, reason, customer_id)`: Insert return record, trigger notification
- `verify_damage_photo(return_id, consistent, confidence, notes)`: Update return_evidence table, set flagged_for_review or fast_tracked

### API Endpoints

**Agent Interaction**:
- `POST /api/agent/message`
  - Request: `{ customer_id, message, image_base64?, conversation_history? }`
  - Response: `{ response, reasoning_trace, iterations }`
  - Handles multipart/form-data for image uploads

**Order Operations**:
- `GET /api/orders/search?customer_id={id}&q={query}`
  - Response: `{ matches: [{ order_id, item_name, category, price, purchase_date, days_since_purchase }] }`

**Policy Operations**:
- `GET /api/policy/check?order_id={id}`
  - Response: `{ order_id, eligible, reason, category, window_days, days_since_purchase, exclusions }`

**Return Operations**:
- `POST /api/returns/initiate`
  - Request: `{ order_id, reason, customer_id }`
  - Response: `{ return_id, status, label_reference }`
- `GET /api/returns/:id`
  - Response: `{ id, order_id, status, reason, created_at, ai_verdict, flagged_for_review }`
- `POST /api/returns/:id/advance`
  - Request: `{ action: "advance" }`
  - Updates status: initiated → shipped → refunded
- `POST /api/returns/:id/review`
  - Request: `{ action: "approve" | "decline" }`
  - Business user resolves flagged returns
- `POST /api/returns/verify-photo`
  - Request: `multipart/form-data` with return_id, photo, claimed_issue
  - Uploads to Supabase Storage, passes base64 to Claude for AI analysis
  - Response: `{ recorded: true, routing: "fast_track" | "human_review" }`

**Dashboard Operations**:
- `GET /api/dashboard/returns`
  - Response: `{ returns: [{ id, customer_name, item_name, reason, status, ai_verdict, flagged_for_review, created_at }] }`
  - Joins returns, orders, customers tables
  - No customer_id filtering (business-wide view)

**Health Check**:
- `GET /api/health`
  - Response: `{ status: "ok", database: "connected", timestamp }`
  - Used by Render for health monitoring

## Data Models

### Database Schema

```mermaid
erDiagram
    customers ||--o{ orders : "places"
    customers ||--o{ returns : "initiates"
    orders ||--o{ returns : "subject_of"
    returns ||--o{ return_evidence : "includes"
    returns ||--o{ notifications_log : "triggers"
    return_policy ||--o{ orders : "governs"

    customers {
        uuid id PK
        varchar name
        varchar email
        varchar contact
        timestamp created_at
    }

    orders {
        varchar id PK
        uuid customer_id FK
        varchar item_name
        varchar category FK
        decimal price
        date purchase_date
        boolean final_sale
        timestamp created_at
    }

    return_policy {
        varchar category PK
        int window_days
        text exclusions
        text notes
    }

    returns {
        varchar id PK
        varchar order_id FK
        uuid customer_id FK
        varchar status
        text reason
        jsonb agent_reasoning_log
        boolean flagged_for_review
        boolean fast_tracked
        timestamp created_at
        timestamp updated_at
    }

    return_evidence {
        uuid id PK
        varchar return_id FK
        varchar photo_url
        text claimed_issue
        jsonb ai_verdict
        boolean reviewed_by_human
        timestamp created_at
    }

    notifications_log {
        uuid id PK
        varchar return_id FK
        text message
        varchar trigger_reason
        timestamp sent_at
    }
```

### SQLAlchemy Models (`models/database.py`)

**Customer**:
```python
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    contact = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    orders = relationship("Order", back_populates="customer")
    returns = relationship("Return", back_populates="customer")
```

**Order**:
```python
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(50), primary_key=True)  # ORD-1001 format
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    category = Column(String(50), ForeignKey("return_policy.category"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    purchase_date = Column(Date, nullable=False)
    final_sale = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    customer = relationship("Customer", back_populates="orders")
    policy = relationship("ReturnPolicy")
    returns = relationship("Return", back_populates="order")
```

**Return**:
```python
class Return(Base):
    __tablename__ = "returns"
    
    id = Column(String(50), primary_key=True)  # RET-1001 format
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    status = Column(Enum("initiated", "shipped", "refunded", "declined", name="return_status"), nullable=False)
    reason = Column(Text, nullable=False)
    agent_reasoning_log = Column(JSONB)  # List of tool calls and results
    flagged_for_review = Column(Boolean, default=False)
    fast_tracked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    order = relationship("Order", back_populates="returns")
    customer = relationship("Customer", back_populates="returns")
    evidence = relationship("ReturnEvidence", back_populates="return_record")
    notifications = relationship("NotificationLog", back_populates="return_record")
```

**ReturnEvidence**:
```python
class ReturnEvidence(Base):
    __tablename__ = "return_evidence"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id = Column(String(50), ForeignKey("returns.id"), nullable=False)
    photo_url = Column(String(500), nullable=False)  # Supabase Storage URL
    claimed_issue = Column(Text, nullable=False)
    ai_verdict = Column(JSONB)  # {consistent: bool, confidence: str, notes: str, reviewed_by_human: bool}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    return_record = relationship("Return", back_populates="evidence")
```

**ReturnPolicy**:
```python
class ReturnPolicy(Base):
    __tablename__ = "return_policy"
    
    category = Column(String(50), primary_key=True)
    window_days = Column(Integer, nullable=False)
    exclusions = Column(Text)
    notes = Column(Text)
```

**NotificationLog**:
```python
class NotificationLog(Base):
    __tablename__ = "notifications_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_id = Column(String(50), ForeignKey("returns.id"), nullable=False)
    message = Column(Text, nullable=False)
    trigger_reason = Column(String(100))  # "return_initiated", "refund_issued", "flagged_for_review"
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    
    return_record = relationship("Return", back_populates="notifications")
```

### Pydantic Schemas (`models/schemas.py`)

**Request/Response DTOs**:
```python
class AgentMessageRequest(BaseModel):
    customer_id: str
    message: str
    image_base64: Optional[str] = None
    conversation_history: List[dict] = []

class AgentMessageResponse(BaseModel):
    response: str
    reasoning_trace: List[dict]
    iterations: int

class OrderMatch(BaseModel):
    order_id: str
    item_name: str
    category: str
    price: Decimal
    purchase_date: date
    days_since_purchase: int

class PolicyCheckResponse(BaseModel):
    order_id: str
    eligible: bool
    reason: str
    category: str
    window_days: int
    days_since_purchase: int
    exclusions: str

class ReturnInitiateRequest(BaseModel):
    order_id: str
    reason: str
    customer_id: str

class ReturnResponse(BaseModel):
    id: str
    order_id: str
    status: str
    reason: str
    created_at: datetime
    ai_verdict: Optional[dict]
    flagged_for_review: bool
```

## Error Handling

### Error Categories and Responses

**Client Errors (4xx)**:
- `400 Bad Request`: Invalid request schema, missing required fields
  - Response: `{ "error": "validation_error", "details": [...] }`
- `404 Not Found`: Resource does not exist (order_id, return_id)
  - Response: `{ "error": "not_found", "resource": "order", "id": "ORD-9999" }`

**Server Errors (5xx)**:
- `500 Internal Server Error`: Unhandled exceptions in business logic
  - Response: `{ "error": "internal_error", "message": "An unexpected error occurred" }`
- `503 Service Unavailable`: Database connection failure, external API timeout
  - Response: `{ "error": "service_unavailable", "message": "Database connection failed. Please retry." }`

### Backend Error Handling Strategy

**Global Exception Handler** (`main.py`):
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "An unexpected error occurred"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "details": exc.errors()}
    )
```

**Database Error Handling** (`services/tools.py`):
```python
async def search_orders(customer_id: str, query: str) -> dict:
    try:
        async with get_db_session() as session:
            result = await session.execute(...)
            return {"matches": [...]}
    except OperationalError as e:
        logger.error(f"Database error in search_orders: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    except Exception as e:
        logger.error(f"Unexpected error in search_orders: {e}")
        raise HTTPException(status_code=500, detail="Search failed")
```

**Claude API Error Handling** (`services/agent_loop.py`):
```python
async def call_claude_api(system: str, messages: List[dict], tools: List[dict]) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, ...},
                json={...}
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Claude API timeout")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry.")
        raise HTTPException(status_code=502, detail="Claude API error")
```

### Frontend Error Display

**Chat Interface Error Messages**:
- Network errors: Display retry button with error message in chat
- Validation errors: Show inline validation message below input field
- API errors: Display assistant message with error explanation

**Dashboard Error Handling**:
- Failed polling: Show banner "Unable to fetch updates. Retrying..."
- Action failures: Display toast notification with error message

## Testing Strategy

### Unit Testing

**Backend Unit Tests** (pytest):
- **Tool Implementations**: Test each tool function with mocked database
  - `test_search_orders_matches_by_keyword()`
  - `test_check_policy_calculates_eligibility()`
  - `test_initiate_return_creates_record()`
- **Business Logic**: Test state transitions, validation rules
  - `test_advance_status_transitions()`
  - `test_review_approval_clears_flag()`
- **Request Validation**: Test Pydantic schema validation
  - `test_agent_message_requires_customer_id()`
  - `test_invalid_status_returns_400()`

**Frontend Unit Tests** (Jest + React Testing Library):
- **Component Rendering**: Test UI components render correctly
  - `test_status_pill_displays_correct_style()`
  - `test_trace_step_shows_tool_name()`
- **API Integration**: Test API client with mocked fetch
  - `test_send_message_posts_to_backend()`
  - `test_error_response_displays_message()`

### Integration Testing

**Backend Integration Tests**:
- **Database Operations**: Test against ephemeral PostgreSQL instance
  - `test_return_flow_end_to_end()`: Create customer → search order → check policy → initiate return
  - `test_photo_upload_stores_evidence()`: Upload photo → verify Supabase Storage URL → check database record
- **Agent Loop**: Test orchestration with mocked Claude API
  - `test_agent_loop_stops_after_text_response()`
  - `test_agent_loop_enforces_max_iterations()`

**End-to-End Tests** (Playwright):
- **Customer Return Flow**: Navigate UI, submit return, verify status
- **Dashboard Operations**: Advance status, resolve flagged return
- Run against staging environment with seeded test data

### Test Coverage Requirements

- Backend: Minimum 80% code coverage
- Frontend: Minimum 70% code coverage (UI components harder to test comprehensively)
- Critical paths (agent loop, tool execution) require 100% coverage

## Migration and Deployment

### Database Migration Strategy

**Initial Migration** (`migrations/001_initial_schema.sql`):
```sql
-- Create tables in dependency order
CREATE TABLE customers (...);
CREATE TABLE return_policy (...);
CREATE TABLE orders (...);
CREATE TABLE returns (...);
CREATE TABLE return_evidence (...);
CREATE TABLE notifications_log (...);

-- Add indexes for common queries
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_purchase_date ON orders(purchase_date);
CREATE INDEX idx_returns_customer_id ON returns(customer_id);
CREATE INDEX idx_returns_status ON returns(status);
```

**Seed Data Migration** (`migrations/002_seed_demo_data.sql`):
```sql
-- Insert 3 demo customers (Amara, Jordan, Priya)
INSERT INTO customers (id, name, email) VALUES (...);

-- Insert 24 orders from prototype
INSERT INTO orders (id, customer_id, item_name, category, price, purchase_date, final_sale) VALUES (...);

-- Insert return policy rules for 6 categories
INSERT INTO return_policy (category, window_days, exclusions) VALUES
  ('Footwear', 30, 'worn outdoors or visible outsole wear'),
  ('Apparel', 20, 'tags removed or item worn beyond trying on'),
  ...;
```

**Migration Execution**:
- Use Alembic (SQLAlchemy migration tool) for version control
- Run migrations automatically on first backend deployment via `alembic upgrade head`
- For production, require explicit migration approval before schema changes

### Deployment Configuration

**Frontend Environment Variables** (`.env.production`):
```
VITE_API_BASE_URL=https://returnpilot-api.onrender.com
```

**Backend Environment Variables** (Render):
```
DATABASE_URL=postgresql://user:pass@aws-0-us-east-1.pooler.supabase.com:5432/postgres
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NOTIFICATION_SERVICE_URL=https://api.viasocket.com/webhook/...
CORS_ORIGINS=https://returnpilot.vercel.app,http://localhost:5173
```

**Deployment Steps**:
1. **Database Setup**:
   - Create Supabase project
   - Create storage bucket `returns-evidence` with public read policy
   - Copy connection string to backend environment
2. **Backend Deployment** (Render):
   - Connect GitHub repository
   - Set environment variables
   - Deploy branch: main
   - Health check path: `/api/health`
   - Auto-deploy on push: enabled
3. **Frontend Deployment** (Vercel):
   - Connect GitHub repository
   - Set `VITE_API_BASE_URL` to Render backend URL
   - Build command: `npm run build`
   - Output directory: `dist`
   - Deploy branch: main

### Rollback Strategy

- **Database**: Keep previous migration version in Alembic history, run `alembic downgrade -1`
- **Backend**: Render provides instant rollback to previous deployment
- **Frontend**: Vercel provides instant rollback to previous deployment via dashboard

---

## Design Rationale

### Why FastAPI Over Node.js?

While the prototype uses JavaScript (React), FastAPI provides stronger benefits for this architecture:

1. **Type Safety**: Pydantic v2 validates requests/responses automatically; Node.js requires manual validation libraries (Zod, class-validator)
2. **Async Clarity**: Native async/await without callback complexity; Node.js async can be more error-prone with mixed callback/promise patterns
3. **OpenAPI Generation**: FastAPI auto-generates OpenAPI schemas from type hints; Express requires manual spec maintenance
4. **Ecosystem Fit**: Python aligns with ML/AI ecosystem if future features need embeddings, classification, or model integration

Per [FastAPI vs Express comparison](https://keyholesoftware.com/express-vs-fastapi-api-framework-comparison/), FastAPI provides better developer experience for API-first applications with strict contracts.

### Why Not Row Level Security (RLS)?

Supabase supports [Row Level Security policies](https://supabase.com/docs/guides/database/postgres/row-level-security) that enforce authorization at the database layer. However, this design uses application-layer filtering (WHERE customer_id = $1) for the following reasons:

1. **Complexity**: RLS policies require learning PostgreSQL policy syntax and debugging policy logic separate from application code
2. **Backend-Only Access**: The frontend never directly queries the database; all queries go through FastAPI, making application-layer filtering sufficient
3. **Flexibility**: Business dashboard requires both filtered (customer) and unfiltered (business-wide) views; RLS policies would require role-switching logic
4. **Migration Simplicity**: Adding WHERE clauses to existing queries is straightforward; RLS requires policy definitions, testing, and potential policy conflicts

If the frontend were to use Supabase's JavaScript client for direct database access, RLS would be essential. For backend-only database access, application-layer filtering is simpler and equally secure.

### Why Maximum 6 Tool-Use Iterations?

The Claude tool-use loop enforces a maximum of 6 iterations per message to prevent:

1. **Infinite Loops**: Malformed tool responses or circular reasoning could cause endless iterations
2. **Latency**: Each Claude API call adds ~1-2 seconds; 6 iterations ≈ 6-12 seconds max response time
3. **Cost**: Claude API charges per token; unbounded iterations could accumulate excessive costs
4. **User Experience**: Long waits degrade UX; 6 iterations provides enough reasoning depth for complex multi-step returns

Per [Claude tool-use documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/build-a-tool-using-agent), most tool-use sequences complete in 2-4 iterations. The 6-iteration limit provides headroom while preventing runaway loops.

