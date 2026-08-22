# ReturnPilot

AI-powered return management system using Gemini agent orchestration.

## Project Structure

```
ReturnPilot/
├── backend/              # FastAPI backend application
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Environment configuration
│   ├── database.py       # Database connection
│   ├── requirements.txt  # Python dependencies
│   ├── models/           # SQLAlchemy and Pydantic models
│   ├── routers/          # API endpoint routers
│   └── services/         # Business logic and agent orchestration
├── frontend/             # React frontend application
│   ├── src/              # React source code
│   ├── package.json      # NPM dependencies
│   └── vite.config.js    # Vite configuration
└── ReturnPilot.jsx       # Original prototype (reference)
```

## Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
```

3. Activate virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

6. Run development server:
```bash
uvicorn main:app --reload
```

Backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env
# Set VITE_API_BASE_URL to your backend URL
```

4. Run development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Architecture

### Technology Stack

- **Frontend**: React 18 + Vite + TypeScript
- **Backend**: FastAPI (Python) + SQLAlchemy 2.0
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage for photo evidence
- **AI**: LLM agent orchestration via Google AI Studio (default model: `gemini-3.5-flash-lite`, free tier)

### Deployment

- **Frontend**: Vercel (configured for automatic deployments)
- **Backend**: Render (containerized deployment with health checks)
- **Database**: Supabase managed PostgreSQL

## Features

- ✅ Secure API key management (server-side only)
- ✅ Multi-user support with data isolation
- ✅ Gemini agent orchestration with tool-use loop
- ✅ Photo evidence upload and AI verification
- ✅ Real-time business dashboard
- ✅ Multi-step return workflow with state machine
- ✅ Notification integration
- ✅ Human review workflow for flagged returns

## Documentation

- [Backend README](./backend/README.md) - Backend setup and API documentation
- [Frontend README](./frontend/README.md) - Frontend setup and deployment
- [viaSocket Investigation](./VIASOCKET_ARCHITECTURE.md) - A parallel no-code build was explored as an alternative/bonus demo; this documents why it isn't the submission (see Decision 19 in `DECISIONS.md`)

## Requirements

- Python 3.11+
- Node.js 18+
- PostgreSQL (via Supabase)
- Google AI Studio API key

## License

Proprietary - All rights reserved
