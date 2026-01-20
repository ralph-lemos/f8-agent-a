"""
Minimal configuration for fast agent.

Loads from environment variables (shared .env with poc_agentic_rag).
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load .env from current or parent directory
load_dotenv()
load_dotenv("../.env")
load_dotenv("../../poc_agentic_rag/.env")


@dataclass
class Config:
    """Minimal configuration for fast agent."""

    # Required for fast agent
    google_api_key: str
    supabase_url: str
    supabase_key: str
    openai_api_key: str
    api_key: str

    # Optional fields (with defaults)
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    neo4j_uri: str = ""
    neo4j_password: str = ""
    neo4j_user: str = "neo4j"
    claude_model: str = "claude-3-5-haiku-20241022"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536


@lru_cache()
def get_config() -> Config:
    """Get cached config from environment."""
    return Config(
        # Google (required for Gemini)
        google_api_key=os.environ["GOOGLE_API_KEY"],
        # Supabase (required for vector search)
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_key=os.environ["SUPABASE_KEY"],
        # OpenAI (required for embeddings)
        openai_api_key=os.environ["OPENAI_API_KEY"],
        # API authentication
        api_key=os.environ["API_KEY"],
        # Optional - Anthropic
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        # Optional - OpenRouter
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        # Optional - Neo4j (for entity graph)
        neo4j_uri=os.getenv("NEO4J_URI", ""),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        # Embedding settings
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
    )
