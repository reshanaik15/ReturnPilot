# ReturnPilot Backend

FastAPI backend for ReturnPilot agent-driven return management system.

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: Supabase PostgreSQL connection string
- `ANTHROPIC_API_KEY`: Claude API key
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/service key

### 5. Run Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Project Structure

```
backend/
├── main.py                 # FastAPI app, CORS, health check
├── config.py               # Environment variable configuration
├── database.py             # Database connection and session management
├── requirements.txt        # Python dependencies
├── routers/                # API endpoint routers
│   ├── agent.py            # POST /api/agent/message
│   ├── orders.py           # GET /api/orders/search
│   ├── returns.py          # Return management endpoints
│   ├── dashboard.py        # GET /api/dashboard/returns
│   └── policy.py           # GET /api/policy/check
├── models/
│   ├── database.py         # SQLAlchemy models
│   └── schemas.py          # Pydantic request/response schemas
└── services/
    ├── agent_loop.py       # Claude tool-use orchestration
    ├── tools.py            # Tool implementations
    └── notifications.py    # Notification service integration
```

## Deployment

### Render

1. Connect your GitHub repository
2. Create a new Web Service
3. Set environment variables in Render dashboard
4. Deploy branch: `main`
5. Health check path: `/api/health`

Build command: `pip install -r requirements.txt`
Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Health Check

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "service": "returnpilot-api"
}
```
