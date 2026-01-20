# Fast Agent

Lightning-fast RAG agent for Factorate Knowledge Hub. Targets <4 second response times.

## Local Development

```bash
# Install dependencies
pip install -e .

# Set environment variables (copy .env.example to .env)
cp .env.example .env
# Edit .env with your API keys

# Run the API server
uvicorn fast_agent.main:app --port 8003

# Run the Streamlit UI (optional)
streamlit run ui/app.py --server.port 8502
```

## Deploy to Fly.io

```bash
# Install Fly CLI
# https://fly.io/docs/flyctl/install/

# Login to Fly
fly auth login

# Create the app (first time only)
fly apps create fast-agent

# Set secrets (API keys)
fly secrets set \
  GOOGLE_API_KEY=your-google-api-key \
  OPENAI_API_KEY=your-openai-api-key \
  SUPABASE_URL=your-supabase-url \
  SUPABASE_KEY=your-supabase-key \
  API_KEY=your-api-key-for-auth

# Deploy
fly deploy

# Check status
fly status
fly logs
```

## API Endpoints

- `POST /chat/stream` - Streaming chat (SSE)
- `GET /health` - Health check
- `GET /` - API info

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Google AI API key for Gemini |
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `API_KEY` | API key for request authentication |
