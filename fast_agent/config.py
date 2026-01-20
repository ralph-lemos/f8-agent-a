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

    # Required fields (no defaults)
    anthropic_api_key: str
    google_api_key: str
    openrouter_api_key: str
    supabase_url: str
    supabase_key: str
    neo4j_uri: str
    neo4j_password: str
    openai_api_key: str
    api_key: str

    # Optional fields (with defaults)
    claude_model: str = "claude-3-5-haiku-20241022"
    neo4j_user: str = "neo4j"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536


@lru_cache()
def get_config() -> Config:
    """Get cached config from environment."""
    return Config(
        # Anthropic
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        # Google
        google_api_key=os.environ.get("GOOGLE_API_KEY", ""),
        # OpenRouter
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        # Supabase
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_key=os.environ["SUPABASE_KEY"],
        # Neo4j
        neo4j_uri=os.environ["NEO4J_URI"],
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.environ["NEO4J_PASSWORD"],
        # OpenAI
        openai_api_key=os.environ["OPENAI_API_KEY"],
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-large"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
        # API
        api_key=os.environ["API_KEY"],
    )
