# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ReturnPilot is an AI-powered return management system. A React chat UI lets a customer describe a return in natural language; a FastAPI backend runs a Claude tool-use agent loop that resolves the order, checks return-policy eligibility, and initiates the return, writing every step to a reasoning trace the UI displays live. An ops dashboard shows all returns with NLP-derived classification/sentiment and lets staff advance status or resolve flagged returns.

`ReturnPilot.jsx` at the repo root is the original single-file prototype, kept only for reference — all real code now lives under `backend/` and `frontend/`.

## Commands

### Backend (`backend/`)

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
cp .env.example .env             # then fill in DATABASE_URL, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY

uvicorn main:app --reload --host 0.0.0.0 --port 8000   # dev server, http://localhost:8000
```

Config validation runs at import time (`config.py`) — the process exits immediately if any required env var is missing, so a broken `.env` fails fast rather than at request time.

Migrations (Alembic, wrapped by `run_migrations.py`):

```bash
python run_migrations.py            # apply all pending migrations
python run_migrations.py --check    # show current version
python run_migrations.py --history  # show migration history
python run_migrations.py --rollback # undo last migration
python run_migrations.py --reset    # drop and reapply everything (destructive)
```

There is no pytest suite. `test_database.py` and `test_checkpoint_3.py` are standalone verification scripts run directly and asserting against a real connected database:

```bash
python test_database.py
python test_checkpoint_3.py
```

### Frontend (`frontend/`)

```bash
npm install
cp .env.example .env   # set VITE_API_BASE_URL (defaults to http://localhost:8000)

npm run dev       # dev server, http://localhost:5173
npm run build     # production build to dist/
npm run lint      # eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0
```

## Architecture

### Three tiers

- **Frontend** (`frontend/src`): React 18 + Vite. `api.js` is the sole client for the backend — no direct DB or Claude access from the browser (API keys and DB credentials live only server-side).
- **Backend** (`backend/`): FastAPI + async SQLAlchemy 2.0, talking to Supabase-hosted PostgreSQL. Routers stay thin (validate, call a service, shape the response); business logic and orchestration live in `services/`.
- **Database**: Supabase PostgreSQL, schema and seed data managed exclusively through Alembic migrations in `backend/migrations/versions/` — never modify the schema by hand.

### The agent orchestration loop

`backend/services/agents/orchestrator.py` is the core of the system. `agent_turn()`:

1. Runs `services/nlp_analyzer.py` on the incoming message first (reason classification + sentiment), independent of the tool loop, and logs it as an `nlp_analyzer` trace step.
2. Enters a Claude tool-use loop (`call_claude`, hardcoded model `claude-3-5-sonnet-20241022`, max 6 iterations) with a fixed `TOOLS` list: `search_orders`, `check_policy`, `initiate_return`, `get_analytics`.
3. Each `tool_use` block Claude emits is dispatched via `execute_tool()` to the matching function in `services/tools.py`, labeled in the trace under a specialist "agent" name (`order_agent`, `policy_agent`, `return_agent`, `analytics_agent`) even though there's a single Claude call per iteration, not separate agent processes — the labels exist purely to make the frontend's reasoning-trace panel legible.
4. Every iteration appends to `reasoning_trace`; the full trace, final response text, and `return_id`/`return_initiated` flags are returned together and echoed to the frontend and stored on the `Return` row's `agent_reasoning_log` JSONB column.
5. The intended tool order is enforced only by the system prompt, not the server: `search_orders` → `check_policy` → `initiate_return`. `check_policy` re-validates eligibility server-side regardless of what Claude has "decided."

The router at `routers/agent.py` (`POST /api/agent/message`) is the sole entry point that drives this loop; other routers (`orders.py`, `returns.py`, `dashboard.py`, `policy.py`) expose direct CRUD/read paths over the same `services/tools.py` functions for the ops dashboard and non-chat flows, bypassing the agent loop entirely.

### Data model (`backend/models/__init__.py`)

`Customer` → `Order` (FK `category` → `ReturnPolicy.category`) → `Return` → `ReturnEvidence` / `NotificationLog`. Order and Return IDs are human-readable strings (`ORD-1001`, `RET-1001`), not UUIDs — only `Customer`, `ReturnEvidence`, and `NotificationLog` use UUID primary keys. `Return.agent_reasoning_log` (JSONB) is the persisted copy of the orchestrator's `reasoning_trace` for that return; `Return.status` follows the state machine `initiated → shipped → refunded`, with `declined` as a terminal branch reachable only through the human-review path (`routers/returns.py`'s `/review` endpoint), not the automatic `/advance` transitions.

### Database session handling

`database.py` builds one process-wide async engine (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) and exposes `get_db()` as a FastAPI dependency — routers must use `Depends(get_db)`, never construct a session directly, since `get_db()` handles commit/rollback/close. `DATABASE_URL` is normalized at import time (`postgres://` → `postgresql://`, then forced to `+asyncpg`), so `.env` can hold a plain Supabase connection string.

### Notifications

`services/notifications.py` posts to an optional external webhook (`NOTIFICATION_SERVICE_URL`, e.g. viaSocket) and logs every send to `NotificationLog`. Triggered from both the agent loop (on `initiate_return` success) and directly from `routers/returns.py` on status transitions (`return_shipped`, `return_refunded`) and approvals.

## Reference docs in this repo

These were written as a learning/teaching aid for this specific codebase and go deeper than this file on execution flow and rationale — worth reading before making non-trivial backend changes:

- `MENTAL_MODEL.md` — plain-language walkthrough of the three-tier architecture, tool-use pattern, connection pooling, and migrations, with a request-lifecycle trace from browser to database.
- `EXECUTION.md` — literal code execution order (import time vs. request time) for `main.py`, `database.py`, `config.py`, and the migration system.
- `DECISIONS.md` — ADR-style log of *why* each architectural choice was made (FastAPI over Node, SQLAlchemy over raw SQL, async driver, connection pool sizing, human-readable IDs, JSONB reasoning log, etc.) — check here before reversing a design choice.
- `.kiro/specs/backend-architecture-migration/` — the spec (`requirements.md`, `design.md`, `tasks.md`) this backend was built against, migrating off the original `ReturnPilot.jsx` prototype. Note: `tasks.md` checkboxes are stale relative to actual code — several tasks marked incomplete there (tools.py, agent orchestration, routers) are already implemented; verify current status against the code, not the checklist.
