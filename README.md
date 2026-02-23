# AI Real Estate Assistant

An AI-powered assistant for real estate agent Harry. Upload call transcripts, extract structured buyer requirements via LLM, and run them through a property matching pipeline.

**Pipeline:** CALL → AI Agent → SEARCH → RANK → REVIEW → SEND

Steps 1-2 (Call Ingestion + Requirements Extraction) are fully implemented. Steps 3-6 (Search, Rank, Review, Send) are scaffolded with mock data.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** TypeScript, React, Vite, Tailwind CSS
- **LLM:** Claude (Anthropic) or OpenAI — configurable

## Prerequisites

- Python 3.9+
- Node.js 18+
- An API key for [Anthropic](https://console.anthropic.com/) and/or [OpenAI](https://platform.openai.com/)

## Setup

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API key(s):
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
#   LLM_PROVIDER=claude   (or "openai")
```

### Frontend

```bash
cd frontend
npm install
```

## Running

Start both servers in separate terminals:

```bash
# Terminal 1 — Backend (port 8000)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2 — Frontend (port 5173)
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

The frontend dev server proxies `/api` requests to the backend automatically.

## Usage

1. **Upload a transcript** — Go to "Upload Transcript" in the sidebar. Either drag-and-drop a `.txt`/`.md` file or paste the call text directly.
2. **Extract requirements** — Click "Upload & Extract" to run AI extraction immediately, or "Upload Only" to extract later.
3. **Review extracted data** — View structured buyer requirements (must-haves, nice-to-haves, budget, timeline, etc.). Edit any field if the AI got something wrong.
4. **Run the pipeline** — Click "Run Pipeline" from the transcript detail page to step through Search → Rank → Review → Send (mock data for now).

## API Documentation

With the backend running, visit **http://localhost:8000/docs** for the interactive Swagger UI.

## Project Structure

```
backend/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── config.py          # Environment-based settings
│   ├── database.py        # SQLAlchemy setup
│   ├── models/            # ORM models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── routers/           # API endpoint handlers
│   ├── services/          # Business logic
│   ├── llm/               # LLM provider abstraction
│   │   ├── base.py        # Abstract provider interface
│   │   ├── claude_provider.py
│   │   ├── openai_provider.py
│   │   ├── factory.py     # Provider selection
│   │   └── prompts/       # Prompt templates
│   └── utils/
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── api/               # Typed API client layer
│   ├── pages/             # Route pages
│   ├── components/        # Reusable UI components
│   ├── types/             # TypeScript interfaces
│   └── App.tsx            # Router setup
├── package.json
└── vite.config.ts
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude` or `openai` |
| `ANTHROPIC_API_KEY` | — | Required if using Claude |
| `OPENAI_API_KEY` | — | Required if using OpenAI |
| `DATABASE_URL` | `sqlite:///./real_estate.db` | SQLite connection string |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `DEBUG` | `false` | Enable SQLAlchemy query logging |
