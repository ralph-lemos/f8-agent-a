"""
Thin Supabase client for fast agent.

Provides direct access to hybrid search without RAG pipeline overhead.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from ..config import get_config

logger = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 2
RETRY_DELAY = 0.5  # seconds

# Singleton client
_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get singleton Supabase client."""
    global _client
    if _client is None:
        config = get_config()
        _client = create_client(config.supabase_url, config.supabase_key)
        logger.info("Supabase client initialized")
    return _client


class FastSupabaseClient:
    """Fast Supabase client for direct hybrid search."""

    def __init__(self):
        self.client = get_supabase_client()

    async def search_chunks_hybrid(
        self,
        org_id: str,
        query_embedding: List[float],
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.25,
        keyword_weight: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """
        Direct hybrid search via SQL RPC.

        Combines vector similarity + keyword matching in a single query.
        Much faster than the full RAG pipeline.

        Args:
            org_id: Organization ID for multi-tenant filtering
            query_embedding: 1536-dim embedding vector
            query_text: Raw text query for keyword matching
            limit: Max results to return
            similarity_threshold: Min similarity score (0-1)
            keyword_weight: Weight for keyword vs vector (0-1)

        Returns:
            List of chunks with scores and metadata
        """
        for attempt in range(MAX_RETRIES + 1):
            try:
                result = self.client.rpc(
                    "match_chunks_hybrid",
                    {
                        "query_embedding": query_embedding,
                        "query_text": query_text,
                        "match_org_id": org_id,
                        "match_count": limit,
                        "match_threshold": similarity_threshold,
                        "keyword_weight": keyword_weight,
                    },
                ).execute()

                if result.data:
                    logger.info(f"Hybrid search returned {len(result.data)} results")
                    return result.data
                return []

            except Exception as e:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Hybrid search failed (attempt {attempt + 1}), retrying: {e}")
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Hybrid search failed after {MAX_RETRIES + 1} attempts: {e}")
                    return []

        return []
