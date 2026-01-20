"""
Fast KB search tool - NO enhancement, NO reranking, NO CRAG, NO compression.

Target: <500ms total (300ms embedding + 150ms search)
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from ..config import get_config
from ..clients.supabase import FastSupabaseClient

logger = logging.getLogger(__name__)


def _clean_document_title(raw_title: str) -> str:
    """Clean ingestion artifact names to human-readable titles."""
    title = raw_title

    # If title already looks clean (has proper spaces and capitalization), return it
    if " " in title and any(c.isupper() for c in title[1:]):
        return title

    # Remove URL artifacts
    title = title.replace("www.", "").replace("__cleaned", "").replace("_cleaned", "")
    title = title.replace(".com", "").replace(".io", "").replace(".co", "").replace(".org", "")

    # Replace path separators with readable format
    title = title.replace("_blog_", " Blog: ")
    title = title.replace("_solutions_", " ")
    title = title.replace("_approach_", " ")

    # Replace underscores and hyphens with spaces
    title = title.replace("_", " ").replace("-", " ")

    # Clean up and capitalize
    words = [w.capitalize() for w in title.split() if w and len(w) > 1]
    title = " ".join(words)

    # If still looks like a domain, extract meaningful part
    if not title or title.lower() in ["leanlabs", "lean labs"]:
        return "Lean Labs"

    return title.strip() if title.strip() else "Unknown Document"


# Cached clients
_openai_client: Optional[AsyncOpenAI] = None
_supabase_client: Optional[FastSupabaseClient] = None
_embedding_cache: Dict[str, List[float]] = {}


def get_openai_client() -> AsyncOpenAI:
    """Get singleton OpenAI client."""
    global _openai_client
    if _openai_client is None:
        config = get_config()
        _openai_client = AsyncOpenAI(api_key=config.openai_api_key)
    return _openai_client


def get_fast_supabase() -> FastSupabaseClient:
    """Get singleton fast Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = FastSupabaseClient()
    return _supabase_client


async def generate_embedding(text: str) -> List[float]:
    """
    Generate single embedding - ~300ms (0ms if cached).

    Uses in-memory cache for repeated queries.
    """
    # Check cache first
    cache_key = hashlib.md5(text.encode()).hexdigest()[:16]
    if cache_key in _embedding_cache:
        logger.info("[FAST SEARCH] Embedding cache hit")
        return _embedding_cache[cache_key]

    config = get_config()
    client = get_openai_client()

    response = await client.embeddings.create(
        input=text,
        model=config.embedding_model,
        dimensions=config.embedding_dimensions,
    )
    embedding = response.data[0].embedding

    # Store in cache
    _embedding_cache[cache_key] = embedding
    return embedding


# Tool definition for Claude API
FAST_SEARCH_TOOL = {
    "name": "search_kb",
    "description": (
        "Search the knowledge base for relevant documents and content. "
        "Use this tool for ANY question about documents, articles, internal knowledge, "
        "or factual information stored in the system. Returns the most relevant text chunks."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query - use specific keywords for best results",
            },
        },
        "required": ["query"],
    },
}


async def fast_search_kb(
    query: str,
    org_id: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Fast KB search - skips ALL enhancement for speed.

    SKIPPED (saves ~50+ seconds):
    - HyDE (hypothetical document generation)
    - Query expansion (multiple query variations)
    - Multi-query parallel search
    - Cross-encoder reranking
    - CRAG evaluation and correction
    - Contextual compression

    KEPT:
    - Single embedding generation (~300ms)
    - Hybrid search via Supabase RPC (~150ms)

    Args:
        query: Search query
        org_id: Organization ID for filtering
        limit: Max results (default 5)

    Returns:
        Dict with content and metadata
    """
    logger.info(f"[FAST SEARCH] Query: '{query[:50]}...'")

    # Step 1: Generate single embedding (~300ms)
    embedding = await generate_embedding(query)

    # Step 2: Direct hybrid search (~150ms)
    supabase = get_fast_supabase()
    chunks = await supabase.search_chunks_hybrid(
        org_id=org_id,
        query_embedding=embedding,
        query_text=query,
        limit=limit,
        similarity_threshold=0.25,  # Slightly lower for better recall
        keyword_weight=0.4,
    )

    # Step 3: Format results (no compression - just truncate)
    if not chunks:
        return {
            "content": f"No results found for: '{query}'",
            "results_count": 0,
        }

    # Simple formatting - keep it fast
    result_lines = [f"## Search Results for: {query}\n"]
    doc_titles = []  # Track unique document titles

    for i, chunk in enumerate(chunks, 1):
        doc_title = _clean_document_title(chunk.get("document_title", "Unknown"))
        if doc_title not in doc_titles:
            doc_titles.append(doc_title)
        score = chunk.get("combined_score", chunk.get("similarity", 0))
        content = chunk.get("content", "")

        # Truncate long content (no compression LLM call)
        if len(content) > 1200:
            content = content[:1200] + "..."

        # Add relevance indicator
        if score >= 0.7:
            relevance = "HIGH"
        elif score >= 0.5:
            relevance = "MEDIUM"
        else:
            relevance = "LOW"

        result_lines.append(f"### [{i}] {doc_title}")
        result_lines.append(f"Relevance: {relevance} ({score:.2f})")
        result_lines.append(content)
        result_lines.append("")

    return {
        "content": "\n".join(result_lines),
        "results_count": len(chunks),
        "top_score": max((c.get("combined_score", 0) for c in chunks), default=0),
        "source_documents": doc_titles,
    }
