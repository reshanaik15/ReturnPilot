# ReturnPilot Frontend

React frontend for ReturnPilot agent-driven return management system.

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and set your backend API URL:

```bash
cp .env.example .env
```

Required variables:
- `VITE_API_BASE_URL`: Backend API base URL (e.g., `http://localhost:8000` for local development)

### 3. Run Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Build for Production

```bash
npm run build
```

Build output will be in the `dist/` directory.

## Project Structure

```
frontend/
├── package.json          # NPM dependencies and scripts
├── vite.config.js        # Vite configuration
├── index.html            # HTML entry point
├── .env.example          # Environment variable template
├── src/
│   ├── main.jsx          # React entry point
│   ├── App.jsx           # Main application component
│   ├── api.js            # Backend API client
│   └── components/       # React components
│       ├── LoginScreen.jsx
│       ├── ChatView.jsx
│       ├── Dashboard.jsx
│       ├── StatusPill.jsx
│       └── TraceStep.jsx
```

## Deployment

### Vercel

1. Connect your GitHub repository
2. Set framework preset to "Vite"
3. Configure environment variable: `VITE_API_BASE_URL` (your production backend URL)
4. Deploy branch: `main`

Build settings:
- Build command: `npm run build`
- Output directory: `dist`
- Install command: `npm install`

## Environment Variables

- `VITE_API_BASE_URL`: Backend API base URL
  - Development: `http://localhost:8000`
  - Production: `https://your-backend.onrender.com`

All Vite environment variables must be prefixed with `VITE_` to be exposed to the client.
