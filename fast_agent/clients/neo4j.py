"""
Thin Neo4j client for fast agent.

Provides direct Cypher queries without Graphiti overhead.
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver

from ..config import get_config

logger = logging.getLogger(__name__)

# Singleton driver
_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """Get singleton Neo4j driver."""
    global _driver
    if _driver is None:
        config = get_config()
        _driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
        )
        logger.info("Neo4j driver initialized")
    return _driver


async def get_entities_fuzzy(
    entity_name: str,
    group_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Fast entity lookup with fuzzy matching.

    Direct Cypher query - no Graphiti embedding overhead.

    Args:
        entity_name: Name to search for (case-insensitive fuzzy match)
        group_id: Organization ID (maps to Neo4j group_id)
        limit: Max entities to return

    Returns:
        List of entities with relationships
    """
    driver = get_neo4j_driver()

    query = """
    MATCH (e:Entity)
    WHERE toLower(e.name) CONTAINS toLower($entity_name)
      AND e.group_id = $group_id
    WITH e LIMIT $limit
    OPTIONAL MATCH (e)-[r]-(related:Entity {group_id: $group_id})
    RETURN e.name AS name,
           e.entity_type AS type,
           e.summary AS summary,
           collect(DISTINCT {
               target: related.name,
               relationship: type(r),
               target_type: related.entity_type
           })[0..5] AS relationships
    """

    try:
        with driver.session() as session:
            result = session.run(
                query,
                entity_name=entity_name,
                group_id=group_id,
                limit=limit,
            )

            entities = []
            for record in result:
                # Filter out null relationships
                relationships = [
                    r for r in (record.get("relationships") or [])
                    if r.get("target") is not None
                ]
                entities.append({
                    "name": record["name"],
                    "type": record.get("type") or "unknown",
                    "summary": record.get("summary") or "",
                    "relationships": relationships,
                })

            logger.info(f"Entity search returned {len(entities)} results")
            return entities

    except Exception as e:
        logger.error(f"Entity search failed: {e}")
        return []
