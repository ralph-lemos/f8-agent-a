# CLAUDE.md - Fast Agent Project Context

## Project Overview

**Fast Agent** - Lightning-fast RAG agent for Factorate Knowledge Hub. Uses Gemini 2.5 Flash-Lite for <4 second responses.

## Locations

| What | Where |
|------|-------|
| Local code | `C:\Users\Sistemas\Nova pasta\fast_agent` |
| GitHub repo | https://github.com/ralph-lemos/f8-agent-a.git |
| API (Fly.io) | https://claude-code-dev.fly.dev |
| UI (Fly.io) | https://fast-agent-ui.fly.dev |
| Fly.io dashboard | https://fly.io/apps/claude-code-dev |
| Fly.io org | `lean-labs` |

## Project Structure

```
fast_agent/
├── fast_agent/           # Main Python package
│   ├── main.py          # FastAPI app, endpoints (/chat/stream, /health)
│   ├── agent.py         # Gemini agent logic, classification, KB search
│   ├── config.py        # Environment config (Google, Supabase, OpenAI, API_KEY)
│   ├── clients/
│   │   ├── supabase.py  # Vector search client (hybrid_search RPC)
│   │   └── neo4j.py     # Entity graph client (optional)
│   └── tools/
│       ├── fast_search.py   # KB search tool (embeddings + Supabase)
│       └── get_entities.py  # Entity lookup tool (Neo4j)
├── ui/                   # Streamlit UI (separate Fly.io app)
│   ├── app.py           # Chat interface
│   ├── Dockerfile
│   ├── fly.toml         # Fly.io config (app: fast-agent-ui)
│   └── requirements.txt
├── Dockerfile           # API container
├── fly.toml             # API Fly.io config (app: claude-code-dev)
├── pyproject.toml       # Python dependencies
└── .env                 # Local secrets (not in git)
```

## Key Commands

### Local Development
```bash
cd "C:\Users\Sistemas\Nova pasta\fast_agent"

# Run API locally
uvicorn fast_agent.main:app --port 8003 --reload

# Run UI locally
streamlit run ui/app.py --server.port 8502
```

### Deploy to Fly.io
```bash
cd "C:\Users\Sistemas\Nova pasta\fast_agent"

# Deploy API
flyctl deploy --app claude-code-dev

# Deploy UI
cd ui && flyctl deploy --app fast-agent-ui

# View logs
flyctl logs --app claude-code-dev
flyctl logs --app fast-agent-ui

# Check status
flyctl status --app claude-code-dev
```

### Git/GitHub
```bash
cd "C:\Users\Sistemas\Nova pasta\fast_agent"

# Commit and push
git add -A
git commit -m "Your message"
git push

# Pull latest
git pull
```

### Fly.io Secrets
```bash
# Set secrets (API needs these)
flyctl secrets set GOOGLE_API_KEY=xxx --app claude-code-dev
flyctl secrets set OPENAI_API_KEY=xxx --app claude-code-dev
flyctl secrets set SUPABASE_URL=xxx --app claude-code-dev
flyctl secrets set SUPABASE_KEY=xxx --app claude-code-dev
flyctl secrets set API_KEY=xxx --app claude-code-dev

# List current secrets
flyctl secrets list --app claude-code-dev
```

## Architecture

```
User → UI (Streamlit) → API (FastAPI) → Gemini 2.5 Flash-Lite
                              ↓
                        Supabase (pgvector)
                              ↓
                        OpenAI Embeddings
```

**Flow:**
1. User sends message via UI
2. API classifies: SEARCH (needs KB) or CHAT (direct response)
3. If SEARCH: Generate embedding → Query Supabase → Get chunks → Generate answer
4. Stream response back via SSE

## Required Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | agent.py |
| `OPENAI_API_KEY` | Embeddings | fast_search.py |
| `SUPABASE_URL` | Vector DB URL | supabase.py |
| `SUPABASE_KEY` | Supabase service key | supabase.py |
| `API_KEY` | Request authentication | main.py |

Optional: `NEO4J_URI`, `NEO4J_PASSWORD` (for entity graph)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/chat/stream` | POST | Streaming chat (SSE) |

**Chat request:**
```json
{
  "message": "What is Lean Labs?",
  "org_id": "factorate",
  "session_id": "optional-session-id"
}
```

**Headers:** `X-API-Key: your-api-key`

## Common Tasks

### Add a new feature
1. Edit code in `fast_agent/`
2. Test locally: `uvicorn fast_agent.main:app --port 8003`
3. Commit: `git add -A && git commit -m "message" && git push`
4. Deploy: `flyctl deploy --app claude-code-dev`

### Debug production issues
1. Check logs: `flyctl logs --app claude-code-dev`
2. Check status: `flyctl status --app claude-code-dev`
3. SSH in: `flyctl ssh console --app claude-code-dev`

### Update UI
1. Edit `ui/app.py`
2. Deploy: `cd ui && flyctl deploy --app fast-agent-ui`

## Tech Stack

- **LLM**: Gemini 2.5 Flash-Lite (fast, cheap)
- **Embeddings**: OpenAI text-embedding-3-large (1536 dims)
- **Vector DB**: Supabase with pgvector
- **API**: FastAPI with SSE streaming
- **UI**: Streamlit
- **Hosting**: Fly.io (São Paulo region - gru)
