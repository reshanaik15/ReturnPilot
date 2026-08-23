# Mental Model: ReturnPilot Backend

> **⚠️ Status update (2026-08-23):** This document describes the Phase 1 FastAPI + Postgres backend. Note that a parallel viaSocket-native build has also been completed and powers the live Vercel demo, acting as the backend (React → viaSocket webhooks → viaSocket Table).

## Introduction

**The Goal of This Document:**

If you can't explain what the code does in your own words, you're not ready to work with it—no matter how thorough the documentation is. This document forces you to build a **mental model** of how ReturnPilot works, using analogies, visual diagrams, and plain language explanations.

---

## The Big Picture: What Is ReturnPilot?

**ReturnPilot is a smart customer service agent for handling product returns.**

### The Problem It Solves

Imagine you bought shoes online, they don't fit, and you want to return them. Normally:
1. You email customer service
2. Wait for a human to respond
3. They check your order, verify the return policy, and approve/deny
4. You ship the item back
5. Wait for refund

**ReturnPilot automates this** using an AI agent (Gemini) that:
- Understands natural language ("I want to return my blue sneakers")
- Looks up your orders in the database
- Checks if you're eligible based on return policy
- Initiates the return and sends you a shipping label
- Verifies photo evidence of damage
- Routes edge cases to human review

### The Architecture: Three Tiers

```
┌─────────────────────┐
│   React Frontend    │  ← Customer types messages, uploads photos
│   (Thin Client)     │  ← Only UI rendering, no business logic
└──────────┬──────────┘
           │ HTTP Requests (JSON)
           ↓
┌─────────────────────┐
│  FastAPI Backend    │  ← Agent orchestration, tool execution
│  (Business Logic)   │  ← Calls Gemini API (server-side, secure)
└──────────┬──────────┘
           │ SQL Queries
           ↓
┌─────────────────────┐
│  PostgreSQL DB      │  ← Customers, orders, returns, policies
│  (Data Storage)     │  ← Persistent data (survives server restart)
└─────────────────────┘
```

**Analogy: Restaurant**

- **Frontend**: Waiter who takes orders and delivers food (UI only)
- **Backend**: Kitchen that cooks the food (business logic, agent orchestration)
- **Database**: Pantry that stores ingredients (data persistence)

The waiter doesn't cook—they just take requests and deliver results. The kitchen does all the work.

---

## The Database: Understanding the Tables

### Table Relationships

Think of the database as a **filing system** with interconnected folders:

```
Customers Folder
  ├─ Customer 1: Amara Chen
  │   ├─ Orders Folder
  │   │   ├─ ORD-1001: Blue Running Sneakers
  │   │   └─ ORD-1002: Wireless Headphones
  │   └─ Returns Folder
  │       └─ RET-1001: Return for ORD-1001
  │           └─ Evidence Folder
  │               └─ Photo: damaged_shoe.jpg
  │
  ├─ Customer 2: Jordan Reyes
  └─ Customer 3: Priya Nair
```

### The Tables in Plain Language

**1. Customers Table**
- **What it stores**: Basic customer info (name, email, phone)
- **Real-world analogy**: Customer loyalty card (ID card you scan at checkout)
- **Key point**: Each customer has a unique UUID (like a social security number)

**2. Orders Table**
- **What it stores**: Every purchase a customer made
- **Real-world analogy**: Receipt from a store
- **Key fields**:
  - `item_name`: What did they buy? ("Blue Running Sneakers")
  - `purchase_date`: When did they buy it? (Used to check return window)
  - `final_sale`: Can it be returned? (No returns on clearance items)
  - `category`: What type of product? (Footwear, Apparel, Electronics)

**3. Return Policy Table**
- **What it stores**: Rules for returning different product categories
- **Real-world analogy**: Return policy poster on the wall at a store
- **Key fields**:
  - `category`: Footwear, Apparel, Electronics, etc.
  - `window_days`: How many days to return? (30 days for footwear)
  - `exclusions`: What voids the return? ("worn outdoors" for shoes)

**4. Returns Table**
- **What it stores**: All return requests from customers
- **Real-world analogy**: Return slip you fill out when returning an item
- **Key fields**:
  - `status`: Where is the return in the workflow? (initiated → shipped → refunded)
  - `reason`: Why are they returning it? ("Too small", "Damaged")
  - `agent_reasoning_log`: What did the AI agent do? (Tool calls and decisions)
  - `flagged_for_review`: Does a human need to review this? (Suspicious claims)

**5. Return Evidence Table**
- **What it stores**: Photos uploaded by customers to prove damage
- **Real-world analogy**: Photos you send to insurance company after a car accident
- **Key fields**:
  - `photo_url`: Link to the uploaded image
  - `claimed_issue`: What does the customer say is wrong? ("Torn sole")
  - `ai_verdict`: What does the AI think? ({"consistent": true, "confidence": "high"})

**6. Notifications Log Table**
- **What it stores**: Record of all emails/SMS sent to customers
- **Real-world analogy**: Sent items in your email outbox
- **Purpose**: Audit trail (prove we sent the refund notification)

---

## The Agent Loop: How Gemini Makes Decisions

### The Tool-Use Pattern

Gemini doesn't have direct access to your database. Instead, it uses **tools**—functions you expose to it.

**Analogy: Lawyer and Paralegal**

- **Gemini**: Senior lawyer (smart, makes decisions, but no direct access to files)
- **Tools**: Paralegal staff (look up files, check records, file paperwork)
- **Your Backend**: Office manager (coordinates between lawyer and paralegals)

**The conversation looks like this:**

```
Customer: "I want to return my blue sneakers"

Gemini (thinks): "I need to find their order. I'll use search_orders tool."
  ↓ [Gemini's response includes a tool_calls entry]

Backend: "Okay, I'll execute search_orders('blue sneakers')"
  ↓ [Queries database, finds ORD-1001]

Backend (to Gemini): "Tool result: Found order ORD-1001, Blue Running Sneakers, purchased 15 days ago"

Gemini (thinks): "Now I need to check the return policy. I'll use check_policy tool."
  ↓ [Gemini's response includes a tool_calls entry]

Backend: "Okay, I'll execute check_policy(ORD-1001)"
  ↓ [Queries database, joins orders + return_policy tables]

Backend (to Gemini): "Tool result: Eligible. Footwear has 30-day window, only 15 days passed."

Gemini (thinks): "Great! I'll initiate the return. I'll use initiate_return tool."
  ↓ [Gemini's response includes a tool_calls entry]

Backend: "Okay, I'll execute initiate_return(ORD-1001, 'Too small')"
  ↓ [Inserts return record, generates RET-1001 ID, sends notification]

Backend (to Gemini): "Tool result: Return RET-1001 initiated. Shipping label sent to email."

Gemini (thinks): "I have all the info. Time to respond to the customer."
  ↓ [Gemini returns text response, tool_calls is empty]

Gemini (to customer): "I've initiated your return for the Blue Running Sneakers (RET-1001). You'll receive a shipping label via email within 5 minutes. Once we receive the item, your refund will be processed in 3-5 business days."

Backend: "No more tool_calls. Conversation complete."
  ↓ [Returns response to frontend]
```

### The Loop in Code

```python
# Simplified agent loop (orchestrator.py) — Gemini via its OpenAI-compatible
# endpoint, so this is OpenAI-style tool calling, not Anthropic's native
# tool_use/tool_result content blocks.

history = [
    {"role": "user", "content": [{"type": "text", "text": "I want to return my blue sneakers"}]}
]

for iteration in range(6):  # Max 6 tool-use cycles
    # Step 1: Ask Gemini what to do next
    llm_response = await call_llm(
        system=system_prompt,
        messages=history,
        tools=TOOLS,  # OpenAI-style function definitions
    )
    assistant_message = llm_response["choices"][0]["message"]
    history.append(assistant_message)

    tool_calls = assistant_message.get("tool_calls") or []

    # Step 2: Check if Gemini wants to use tools or respond
    if tool_calls:
        # Gemini wants to use tools
        tool_results = []
        for call in tool_calls:
            name = call["function"]["name"]
            # arguments arrives as a JSON *string* — must be parsed
            args = json.loads(call["function"]["arguments"])
            result = await execute_tool(name, args)

            # Each tool result is its own message with role "tool",
            # not nested inside a "user" message like Anthropic's format
            tool_results.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            })
        history.extend(tool_results)
        # Continue loop (ask Gemini again with tool results)
    else:
        # Gemini returned text response (no tools) — we're done!
        return assistant_message.get("content") or ""
```

**Mental Model: Ping-Pong Game**

```
You → Gemini: "I want to return my blue sneakers"
Gemini → You: [tool_calls: search_orders]
You → Gemini: [role: tool, content: Found ORD-1001]
Gemini → You: [tool_calls: check_policy]
You → Gemini: [role: tool, content: Eligible]
Gemini → You: [tool_calls: initiate_return]
You → Gemini: [role: tool, content: RET-1001 created]
Gemini → You: [text: "Return initiated! Shipping label sent."]
DONE ✅
```

---

## The Database Connection Pool: How It Works

### The Problem: Limited Connections

**Imagine a bank with 10 teller windows.**

- Each customer (request) needs a teller (database connection) to process their transaction
- Bank has 10 tellers available (pool_size=10)
- If all 10 tellers are busy, customers wait in line
- Bank can call in 20 backup tellers during rush hour (max_overflow=20)
- After 30 minutes of waiting, customers give up and leave (pool_timeout=30)

### The Solution: Connection Pooling

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,         # 10 tellers always on duty
    max_overflow=20,      # 20 backup tellers available
    pool_timeout=30,      # Wait 30 seconds, then give up
    pool_pre_ping=True,   # Check teller is awake before assigning customer
    pool_recycle=3600,    # Tellers take a break after 1 hour
)
```

### Request Handling

**Scenario 1: Low Traffic (1-10 requests)**
```
Request arrives
  ↓
Pool has available connection
  ↓
Request uses connection (teller serves customer)
  ↓
Request completes
  ↓
Connection returned to pool (teller available again)
```

**Scenario 2: High Traffic (11-30 requests)**
```
Request arrives
  ↓
Pool has no available connections (all 10 tellers busy)
  ↓
Create overflow connection (call in backup teller)
  ↓
Request uses overflow connection (backup teller serves customer)
  ↓
Request completes
  ↓
Overflow connection closed (backup teller goes home)
```

**Scenario 3: Overload (31+ requests)**
```
Request arrives
  ↓
Pool exhausted (10 base + 20 overflow = 30 connections in use)
  ↓
Request waits for available connection (customer waits in line)
  ↓
After pool_timeout (30 seconds): TimeoutError (customer gives up and leaves)
```

### Why pool_pre_ping=True?

**Problem:** Database connections can "go stale" (server restarts, network issues)

**Without pre-ping:**
```
Request takes connection from pool
  ↓
Tries to execute query
  ↓
ERROR: Connection closed by server
  ↓
Request fails (customer sees 500 error)
```

**With pre-ping:**
```
Request takes connection from pool
  ↓
Pre-ping: Send "SELECT 1" to check if connection alive
  ↓
Connection is stale (no response)
  ↓
Discard stale connection, create new one
  ↓
Execute actual query with fresh connection
  ↓
SUCCESS (customer never knows there was a problem)
```

**Analogy:** Knocking on the door before entering a room to check if it's locked.

---

## The Migration System: Version Control for Databases

### The Problem: Coordinating Schema Changes

**Imagine you're building a house with a team:**

- **Developer A** adds a bedroom (new table)
- **Developer B** adds plumbing (foreign keys)
- **Developer C** installs windows (indexes)

**Without migrations:**
- How do you know what order to do these in?
- If Developer B's plumbing goes in before A's bedroom, pipes go nowhere!
- If you need to undo the bedroom, how do you know what to remove?

**With migrations:**
- Each change is a numbered blueprint (001, 002, 003)
- Alembic tracks which blueprints have been applied (`alembic_version` table)
- You can undo blueprints in reverse order (downgrade)

### Migration Files

**001_initial_schema.py: Build the foundation**
```python
def upgrade():
    # Build customers table
    op.create_table('customers', ...)
    # Build orders table
    op.create_table('orders', ...)
    # Add indexes
    op.create_index('idx_orders_customer_id', ...)

def downgrade():
    # Undo in reverse order
    op.drop_index('idx_orders_customer_id')
    op.drop_table('orders')
    op.drop_table('customers')
```

**002_seed_customers.py: Add initial data**
```python
def upgrade():
    # Insert 3 demo customers
    op.bulk_insert(customers, [
        {'name': 'Amara Chen', 'email': 'amara@demo.dev'},
        {'name': 'Jordan Reyes', 'email': 'jordan@demo.dev'},
        {'name': 'Priya Nair', 'email': 'priya@demo.dev'},
    ])

def downgrade():
    # Remove demo customers
    op.execute("DELETE FROM customers WHERE email LIKE '%@demo.dev'")
```

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head
```

**What happens:**

```
1. Alembic reads alembic.ini (finds database connection)
2. Alembic connects to database
3. Alembic checks alembic_version table
   - Table says: "Last applied: None (empty database)"
4. Alembic finds migrations in versions/ folder
   - 001_initial_schema.py
   - 002_seed_customers.py
   - 003_seed_return_policies.py
   - 004_seed_orders.py
5. Alembic runs 001_initial_schema.py:
   - Executes upgrade() function
   - Creates customers, orders, returns tables
   - Inserts "001_initial_schema" into alembic_version
6. Alembic runs 002_seed_customers.py:
   - Executes upgrade() function
   - Inserts 3 demo customers
   - Updates alembic_version to "002_seed_customers"
7. Continues for 003 and 004...
8. Done! Database ready.
```

### Rollback

```bash
# Undo last migration
alembic downgrade -1
```

**What happens:**

```
1. Alembic checks alembic_version: "004_seed_orders"
2. Alembic runs 004_seed_orders.py downgrade() function
   - Executes: DELETE FROM orders WHERE id LIKE 'ORD-%'
3. Alembic updates alembic_version to "003_seed_return_policies"
4. Done! Orders removed, database at version 003.
```

---

## Request Lifecycle: From Browser to Database

### Scenario: Customer Checks Health of API

**Step-by-Step Trace:**

```
1. Browser sends HTTP GET request
   URL: http://localhost:8000/api/health
   ↓

2. Request arrives at uvicorn HTTP server
   (uvicorn is listening on port 8000)
   ↓

3. uvicorn hands request to FastAPI
   ↓

4. FastAPI CORS middleware checks request
   Origin: http://localhost:5173 (frontend)
   Is this origin in CORS_ORIGINS? YES ✓
   Allow request to proceed
   ↓

5. FastAPI router matches request to endpoint
   Route: @app.get("/api/health")
   Function: health_check()
   ↓

6. health_check() function executes
   Code: db_health = await check_database_health()
   ↓

7. check_database_health() function executes
   Code: async with AsyncSessionLocal() as session:
   ↓

8. AsyncSessionLocal creates database session
   - Checks connection pool for available connection
   - Pool has 10 connections, 0 in use
   - Takes connection #1 from pool
   - Validates connection is alive (pool_pre_ping)
   - Returns AsyncSession object
   ↓

9. check_database_health() executes test query
   Code: await session.execute(text("SELECT 1"))
   SQL sent: SELECT 1 as health_check
   ↓

10. PostgreSQL database receives SQL query
    - Parses query
    - Executes query
    - Returns result: 1
    ↓

11. check_database_health() receives result
    Code: result.scalar() → 1
    ↓

12. check_database_health() gets pool stats
    Code: pool.size() → 10
          pool.checkedout() → 1
    ↓

13. check_database_health() returns dict
    Return value: {
        "connected": True,
        "database": "postgresql",
        "pool_size": 10,
        "pool_checkedout": 1
    }
    ↓

14. AsyncSession context manager exits
    - Commits transaction (no changes, so no-op)
    - Closes session
    - Returns connection #1 to pool
    - Pool: 10 available, 0 in use
    ↓

15. health_check() receives db_health dict
    Code: return {
        "status": "ok",
        "timestamp": "2024-01-20T10:30:45.123456",
        "database": db_health
    }
    ↓

16. FastAPI serializes response to JSON
    JSON: {"status":"ok","timestamp":"...","database":{...}}
    ↓

17. FastAPI adds CORS headers to response
    Headers: Access-Control-Allow-Origin: http://localhost:5173
    ↓

18. uvicorn sends HTTP response
    Status: 200 OK
    Body: {"status":"ok",...}
    ↓

19. Browser receives response
    JavaScript: const data = await response.json()
    Console: {status: "ok", database: {connected: true}}
    ↓

20. Frontend displays result
    UI: ✓ API is healthy
```

**Total time: ~15-30ms** (mostly database query time)

---

## Security: Why This Architecture Is Secure

### Problem: Exposed API Keys in Prototype

**Prototype (INSECURE):**

```javascript
// ReturnPilot.jsx (runs in browser)
const GOOGLE_API_KEY = "AIzaSyC...-your-secret-key";  // ← EXPOSED!

fetch("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", {
  headers: {
    "Authorization": "Bearer " + GOOGLE_API_KEY  // ← Anyone can see this in browser DevTools!
  }
});
```

**Attack scenario:**
1. Malicious user opens browser DevTools (F12)
2. Views network requests
3. Copies `x-api-key` header value
4. Uses stolen key to make unlimited Claude API calls (charged to your account)

**Result:** Your API key is compromised. Bill could be $1000s.

### Solution: Server-Side API Calls

**New Architecture (SECURE):**

```
Frontend (browser):
  - ZERO API keys
  - Only makes requests to YOUR backend
  - Backend URL is public (http://localhost:8000), but that's fine

Backend (server):
  - Stores API key in environment variable (.env file)
  - .env file is NEVER committed to Git (.gitignore blocks it)
  - API key is NEVER sent to frontend
  - Backend makes Gemini API calls on frontend's behalf

Gemini API (Google AI Studio):
  - Only sees requests from YOUR backend IP address
  - Frontend never talks directly to Gemini
```

**Code flow:**

```javascript
// Frontend (SAFE)
fetch("http://localhost:8000/api/agent/message", {
  method: "POST",
  body: JSON.stringify({
    customer_id: "amara@demo.dev",
    message: "I want to return my shoes"
  })
});
// ↑ No API key here! Just regular JSON.
```

```python
# Backend (SECURE)
@app.post("/api/agent/message")
async def agent_message(request: AgentMessageRequest):
    # API key is stored server-side (in environment variable)
    response = await call_llm(
        system="...",
        messages=[{"role": "user", "content": request.message}]
    )
    return response
    # Frontend never sees the API key!
```

**Security boundaries:**

```
┌──────────────────────────────────────┐
│  Browser (Untrusted)                 │
│  - Can view all JavaScript code      │
│  - Can inspect network requests      │
│  - ZERO access to API keys           │
└────────────┬─────────────────────────┘
             │ HTTP (JSON only)
             │ No sensitive data
             ↓
┌──────────────────────────────────────┐
│  Backend Server (Trusted)            │
│  - API keys in .env (not in code)    │
│  - .env blocked by .gitignore        │
│  - Only server has access            │
└────────────┬─────────────────────────┘
             │ HTTPS (with API key)
             │ Server-to-server
             ↓
┌──────────────────────────────────────┐
│  Gemini API (Google AI Studio)       │
│  - Only accepts requests from        │
│    backend server IP                 │
└──────────────────────────────────────┘
```

---

## The Data Flow: From User Input to Database

### Scenario: Initiating a Return

**User journey:**

```
1. Customer types: "I want to return my blue sneakers"
2. Clicks "Send" button
3. Sees "Processing..." spinner
4. Sees AI response: "I've initiated your return RET-1001..."
5. Dashboard shows new return record
```

**What happens behind the scenes:**

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                            │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 1. User clicks "Send"
    │    - handleSend() function triggers
    │    - Calls: fetch("POST /api/agent/message", {
    │        body: {customer_id, message, conversation_history}
    │      })
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ NETWORK (HTTP)                                              │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 2. HTTP POST request sent over network
    │    - Headers: Content-Type: application/json
    │    - Body: {"customer_id": "...", "message": "..."}
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI) - agent.py router                         │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 3. Request received at agent_message() endpoint
    │    - Pydantic validates request body
    │    - Extracts: customer_id, message
    │    - Calls: await agent_turn(customer_id, message, ...)
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ AGENT LOOP (orchestrator.py)                                │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 4. agent_turn() starts orchestration loop
    │    - Iteration 1:
    │      - Calls Gemini API with message + tool definitions
    │      - Gemini returns: [tool_calls: search_orders, query="blue sneakers"]
    │      - Executes: await search_orders(customer_id, "blue sneakers")
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - search_orders                            │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 5. search_orders() function executes
    │    - Gets database session: async with get_db()
    │    - Extracts whole-word keywords from the query ("blue", "sneakers"),
    │      filtering out conversational filler first (extract_keywords())
    │    - Queries: SELECT * FROM orders 
    │               WHERE customer_id = :id
    │               AND (item_name ~* '\yblue\y' 
    │                    OR item_name ~* '\ysneakers\y')
    │      (word-boundary regex match, not raw substring LIKE — LIKE '%all%'
    │      would wrongly match "Wallet"; ~* '\yall\y' won't)
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL)                                        │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 6. Database processes query
    │    - Scans orders table (uses idx_orders_customer_id index)
    │    - Finds match: ORD-1001, Blue Running Sneakers, $89.99
    │    - Returns row to backend
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - search_orders (continued)                │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 7. search_orders() returns result
    │    - Returns: [{
    │        "order_id": "ORD-1001",
    │        "item_name": "Blue Running Sneakers",
    │        "purchase_date": "2024-01-05",
    │        "days_since_purchase": 15
    │      }]
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ AGENT LOOP (orchestrator.py) (continued)                    │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 8. agent_turn() receives tool result
    │    - Appends result to conversation history
    │    - Iteration 2:
    │      - Sends result to Gemini: [role: tool, content: found ORD-1001]
    │      - Gemini returns: [tool_calls: check_policy, order_id="ORD-1001"]
    │      - Executes: await check_policy("ORD-1001")
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - check_policy                             │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 9. check_policy() function executes
    │    - Queries: SELECT o.*, p.window_days, p.exclusions
    │               FROM orders o
    │               JOIN return_policy p ON o.category = p.category
    │               WHERE o.id = 'ORD-1001'
    │    - Calculates: days_since_purchase = today - purchase_date = 15
    │    - Checks: 15 < 30 (window_days) → ELIGIBLE
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL)                                        │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 10. Database processes JOIN query
    │     - Finds order ORD-1001 (category: Footwear)
    │     - Joins return_policy (Footwear: 30 day window)
    │     - Returns combined result
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - check_policy (continued)                 │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 11. check_policy() returns result
    │     - Returns: {
    │         "eligible": true,
    │         "reason": "Within 30-day return window (15 days)",
    │         "window_days": 30,
    │         "days_since_purchase": 15
    │       }
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ AGENT LOOP (orchestrator.py) (continued)                    │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 12. agent_turn() receives tool result
    │     - Appends result to conversation
    │     - Iteration 3:
    │       - Sends result to Gemini: [role: tool, content: eligible=true]
    │       - Gemini returns: [tool_calls: initiate_return, 
    │                          order_id="ORD-1001", 
    │                          reason="Too small"]
    │       - Executes: await initiate_return("ORD-1001", "Too small")
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - initiate_return                          │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 13. initiate_return() function executes
    │     - Generates return ID: RET-1001
    │     - Inserts: INSERT INTO returns (
    │                 id, order_id, customer_id, status, reason
    │               ) VALUES (
    │                 'RET-1001', 'ORD-1001', :customer_id,
    │                 'initiated', 'Too small'
    │               )
    │     - Triggers: send_notification(RET-1001, "Return approved")
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL)                                        │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 14. Database inserts return record
    │     - Creates new row in returns table
    │     - Returns success confirmation
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ TOOLS (tools.py) - initiate_return (continued)              │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 15. initiate_return() returns result
    │     - Returns: {
    │         "return_id": "RET-1001",
    │         "status": "initiated",
    │         "label_reference": "SHIP-123456"
    │       }
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ AGENT LOOP (orchestrator.py) (continued)                    │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 16. agent_turn() receives tool result
    │     - Appends result to conversation
    │     - Iteration 4:
    │       - Sends result to Gemini: [role: tool, content: RET-1001 created]
    │       - Gemini returns: [text: "I've initiated your return..."]
    │       - NO TOOL_USE BLOCKS → Loop complete
    │     - Returns: {
    │         "response": "I've initiated your return...",
    │         "reasoning_trace": [...],
    │         "iterations": 4
    │       }
    │
    ↑
┌───┴─────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI) - agent.py router (continued)             │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 17. agent_message() endpoint receives response
    │     - Returns: AgentMessageResponse(
    │         response="...",
    │         reasoning_trace=[...],
    │         iterations=4
    │       )
    │     - FastAPI serializes to JSON
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ NETWORK (HTTP)                                              │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 18. HTTP 200 OK response sent
    │     - Headers: Content-Type: application/json
    │     - Body: {"response": "...", "reasoning_trace": [...]}
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                            │
└───┬─────────────────────────────────────────────────────────┘
    │
    │ 19. Frontend receives response
    │     - Hides "Processing..." spinner
    │     - Displays AI response in chat
    │     - Updates reasoning trace panel
    │     - Polls /api/dashboard/returns to refresh dashboard
    │
    ↓
┌─────────────────────────────────────────────────────────────┐
│ USER SEES:                                                   │
│ "I've initiated your return for the Blue Running Sneakers   │
│  (RET-1001). Shipping label sent to email."                 │
└─────────────────────────────────────────────────────────────┘
```

**Total time: ~2-4 seconds** (mostly Gemini API calls)

---

## Quiz: Test Your Mental Model

Answer these questions to verify you understand the architecture:

### Beginner Questions

1. **What are the three tiers of the architecture?**
2. **Why can't Claude access the database directly?**
3. **What is a "tool" in the context of the agent loop?**
4. **What does the connection pool do?**
5. **Why do we store API keys in environment variables?**

### Intermediate Questions

6. **Explain the agent loop in your own words (no code).**
7. **What happens if all database connections are in use?**
8. **Why do migrations have both upgrade() and downgrade() functions?**
9. **What is the difference between pool_size and max_overflow?**
10. **How does FastAPI know to call get_db() before the endpoint function runs?**

### Advanced Questions

11. **Trace a request from "POST /api/agent/message" to database insertion and back to the frontend.**
12. **Why do we use async/await instead of synchronous database calls?**
13. **Explain how the relationship between Order and Customer works in SQLAlchemy.**
14. **What security vulnerabilities exist if we skip CORS configuration?**
15. **Design a new tool for the agent. What would it do? How would it query the database?**

---

## Common Misconceptions

### Misconception 1: "Claude has access to the database"

**WRONG:** Claude is just an API. It has ZERO access to your database. It can only see:
- The messages you send it
- The tool definitions you provide
- The tool results you send back

**CORRECT:** Your backend is the intermediary. Claude says "use search_orders tool", your backend executes it and sends results back.

### Misconception 2: "The connection pool creates 10 connections at startup"

**WRONG:** The pool is created at startup, but connections are created **lazily** (on-demand) when first query runs.

**CORRECT:** Pool is a container with 10 slots. Connections are created as needed and stored in those slots.

### Misconception 3: "Migrations modify the database directly"

**WRONG:** Migrations generate SQL that modifies the database. Alembic tracks which migrations ran.

**CORRECT:** Migration files contain Python code that generates SQL (`op.create_table()` → `CREATE TABLE`). Alembic executes that SQL against the database.

### Misconception 4: "Relationships load all related data automatically"

**WRONG:** By default, relationships are **lazy-loaded** (separate query when accessed).

**CORRECT:** `customer.orders` triggers a separate query unless you use `selectinload()` for eager loading.

### Misconception 5: "The frontend needs database credentials"

**WRONG:** The frontend is a **thin client**. It has ZERO database access.

**CORRECT:** Frontend only talks to the backend API. Backend talks to the database.

---

## Summary: The Five Key Concepts

If you remember nothing else, remember these five things:

### 1. Three-Tier Architecture
- **Frontend**: UI rendering only (React)
- **Backend**: Business logic, agent orchestration (FastAPI)
- **Database**: Data persistence (PostgreSQL)

### 2. Tool-Use Pattern
- Claude doesn't execute code—it requests tools
- Backend executes tools and sends results back
- Loop continues until Claude returns text response

### 3. Connection Pooling
- Limited connections available (10 base + 20 overflow)
- Connections are reused (returned to pool after request)
- Requests wait if pool exhausted (up to 30 seconds)

### 4. Migrations for Version Control
- Each schema change is a numbered migration file
- Alembic tracks which migrations ran
- Can upgrade (forward) or downgrade (rollback)

### 5. Security Through Separation
- API keys stored server-side (never in frontend)
- Frontend is untrusted (anyone can view code)
- Backend is trusted (only server has access to secrets)

---

## Next Steps: Building Your Understanding

1. **Read the code**: Start with `main.py`, then `database.py`, then `models/__init__.py`
2. **Run the health check**: `curl http://localhost:8000/api/health` and trace execution
3. **Experiment with migrations**: Run `alembic downgrade -1` and `alembic upgrade +1`
4. **Modify a model**: Add a field to Customer, create a migration, apply it
5. **Build a new tool**: Implement a simple tool (e.g., `get_customer_info`)

**Remember:** If you can explain it in your own words, you understand it. If you can't, re-read this document and trace the code execution yourself.

