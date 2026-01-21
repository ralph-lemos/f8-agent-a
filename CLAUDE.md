# CLAUDE.md - Agent A Project Context

## Project Overview

**Agent A** - Lightning-fast RAG agent for knowledge base Q&A. Uses Gemini 2.5 Flash-Lite with hybrid search (vector + knowledge graph) for ~2 second responses.

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
│   ├── agent.py         # Gemini agent logic, classification, hybrid search
│   ├── config.py        # Environment config (Google, Supabase, OpenAI, Neo4j)
│   ├── clients/
│   │   ├── supabase.py  # Vector search client (hybrid_search RPC)
│   │   └── neo4j.py     # Knowledge graph client (entity lookups)
│   └── tools/
│       ├── fast_search.py   # KB search tool (embeddings + Supabase)
│       └── get_entities.py  # Entity lookup tool (Neo4j)
├── scripts/
│   └── battle_test.py   # Performance testing script (23 queries)
├── ui/                   # Streamlit UI (separate Fly.io app)
│   ├── app.py           # Chat interface (Agent A)
│   ├── Dockerfile
│   ├── fly.toml         # Fly.io config (app: fast-agent-ui)
│   └── requirements.txt
├── Dockerfile           # API container
├── fly.toml             # API Fly.io config (app: claude-code-dev)
├── pyproject.toml       # Python dependencies
├── battle_test_results.md  # Latest test results
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

# Run battle test
python scripts/battle_test.py
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
# API secrets (required)
flyctl secrets set GOOGLE_API_KEY=xxx --app claude-code-dev
flyctl secrets set OPENAI_API_KEY=xxx --app claude-code-dev
flyctl secrets set SUPABASE_URL=xxx --app claude-code-dev
flyctl secrets set SUPABASE_KEY=xxx --app claude-code-dev
flyctl secrets set API_KEY=xxx --app claude-code-dev

# Neo4j secrets (for knowledge graph)
flyctl secrets set NEO4J_URI=xxx --app claude-code-dev
flyctl secrets set NEO4J_USER=neo4j --app claude-code-dev
flyctl secrets set NEO4J_PASSWORD=xxx --app claude-code-dev

# UI secrets
flyctl secrets set API_KEY=xxx --app fast-agent-ui

# List current secrets
flyctl secrets list --app claude-code-dev
```

## Architecture

```
User → UI (Streamlit) → API (FastAPI) → Gemini 2.5 Flash-Lite
                              ↓
                    ┌────────┴────────┐
                    ↓                 ↓
            Supabase (pgvector)   Neo4j (graph)
                    ↓                 ↓
            OpenAI Embeddings    Entity Lookup
                    └────────┬────────┘
                             ↓
                    Combined Context
```

**Flow:**
1. User sends message via UI
2. API classifies: SEARCH (needs KB) or CHAT (direct response)
3. If SEARCH:
   - Extract entity names from query
   - Run vector search (Supabase) AND entity lookup (Neo4j) **in parallel**
   - Combine results into context
   - Generate answer with Gemini
4. Stream response back via SSE

## Agent Behavior

- **Temperature**: 0.3 (consistent, deterministic responses)
- **KB-only**: Only answers from knowledge base content, declines off-topic questions
- **No meta-references**: Never says "based on search results" or "according to documents"
- **Direct answers**: Responds confidently as if knowledge is known firsthand
- **Sources**: Always ends with source citations

**Off-topic response:**
> "I can only answer questions about our knowledge base. This topic isn't covered in our documentation. Is there something else I can help you with?"

## Required Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | agent.py |
| `OPENAI_API_KEY` | Embeddings | fast_search.py |
| `SUPABASE_URL` | Vector DB URL | supabase.py |
| `SUPABASE_KEY` | Supabase service key | supabase.py |
| `API_KEY` | Request authentication | main.py, ui/app.py |
| `NEO4J_URI` | Knowledge graph URL | neo4j.py |
| `NEO4J_USER` | Neo4j username | neo4j.py |
| `NEO4J_PASSWORD` | Neo4j password | neo4j.py |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/chat/stream` | POST | Streaming chat (SSE) |

**Chat request:**
```json
{
  "message": "What services does Lean Labs offer?",
  "org_id": "00000000-0000-0000-0000-000000000001",
  "session_id": "optional-session-id"
}
```

**Headers:** `X-API-Key: your-api-key`

## Battle Testing

Run the battle test to evaluate agent performance:

```bash
python scripts/battle_test.py
```

**Test categories:**
- Factual (basic company info)
- Specificity (pricing, numbers, metrics)
- Reasoning (comparisons, differences)
- Process (how-to, methodology)
- Edge cases (refunds, contact info, off-topic)
- Ambiguous queries
- Consistency (same question, different wording)
- Stress tests (greetings, long queries)

**Current performance (23 queries):**
- Average: ~2 seconds
- Fastest: ~600ms (greetings)
- Slowest: ~3.7s (complex queries)
- Success rate: 100%

## Common Tasks

### Add a new feature
1. Edit code in `fast_agent/`
2. Test locally: `uvicorn fast_agent.main:app --port 8003`
3. Run battle test: `python scripts/battle_test.py`
4. Commit: `git add -A && git commit -m "message" && git push`
5. Deploy: `flyctl deploy --app claude-code-dev`

### Debug production issues
1. Check logs: `flyctl logs --app claude-code-dev`
2. Check status: `flyctl status --app claude-code-dev`
3. SSH in: `flyctl ssh console --app claude-code-dev`

### Update UI
1. Edit `ui/app.py`
2. Deploy: `cd ui && flyctl deploy --app fast-agent-ui`

### Modify agent prompt
1. Edit `fast_agent/agent.py` - look for `answer_prompt` variable
2. Test with battle test
3. Deploy API

## Tech Stack

- **LLM**: Gemini 2.5 Flash-Lite (fast, cheap)
- **Embeddings**: OpenAI text-embedding-3-large (1536 dims)
- **Vector DB**: Supabase with pgvector
- **Knowledge Graph**: Neo4j (entity relationships)
- **API**: FastAPI with SSE streaming
- **UI**: Streamlit (Agent A)
- **Hosting**: Fly.io (São Paulo region - gru)
