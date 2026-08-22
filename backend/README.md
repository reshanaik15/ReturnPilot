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
- `GOOGLE_API_KEY`: Google AI Studio API key (https://aistudio.google.com/apikey — free, no credit card)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/service key

Optional variables:
- `GOOGLE_MODEL`: model used for agent orchestration, NLP classification, and photo verification (default `gemini-3.5-flash-lite`)

Note: free-tier request quotas are per-model and per-day. If you see a 429 with `GenerateRequestsPerDayPerProjectPerModel` in the error, switch `GOOGLE_MODEL` to a different Gemini model rather than waiting for the daily reset — quotas are tracked separately per model. The heavier non-lite "flash" models have much smaller free daily quotas and add an internal "thinking" token overhead that flash-lite doesn't.

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
│   ├── __init__.py         # SQLAlchemy models
│   └── schemas.py          # Pydantic request/response schemas
└── services/
    ├── tools.py            # Tool implementations (search_orders, check_policy, etc.)
    ├── notifications.py    # Notification service integration (viaSocket)
    ├── storage.py           # Supabase Storage (return-evidence photo uploads)
    ├── nlp_analyzer.py      # Gemini-based reason/sentiment classification
    ├── photo_analyzer.py    # Gemini vision-based damage verification
    └── agents/
        └── orchestrator.py  # Gemini tool-use orchestration loop
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
