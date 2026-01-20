"""
Fast Neo4j entity lookup tool.

Direct Cypher query - no Graphiti embedding overhead.
Target: <50ms
"""

import logging
from typing import Any, Dict

from ..clients.neo4j import get_entities_fuzzy

logger = logging.getLogger(__name__)


# Tool definition for Claude API
GET_ENTITIES_TOOL = {
    "name": "get_entities",
    "description": (
        "Look up entities and their relationships in the knowledge graph. "
        "Use this tool for questions about connections between people, companies, "
        "concepts, or any named entities. Returns entity details and first-hop relationships."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entity_name": {
                "type": "string",
                "description": "Name of the entity to look up (fuzzy matched, case-insensitive)",
            },
        },
        "required": ["entity_name"],
    },
}


async def get_entities_fast(
    entity_name: str,
    org_id: str,
) -> Dict[str, Any]:
    """
    Fast entity lookup - direct Cypher query.

    SKIPPED:
    - Graphiti semantic search (uses embeddings)
    - Multiple hop traversal
    - Community detection

    KEPT:
    - Direct Cypher with fuzzy name matching
    - Single hop relationships

    Args:
        entity_name: Name to search for
        org_id: Organization ID (maps to group_id in Neo4j)

    Returns:
        Dict with content and metadata
    """
    logger.info(f"[FAST ENTITY] Looking up: '{entity_name}'")

    # Direct Cypher query (~50ms)
    entities = await get_entities_fuzzy(
        entity_name=entity_name,
        group_id=org_id,
        limit=5,
    )

    if not entities:
        return {
            "content": f"No entities found matching: '{entity_name}'",
            "found": False,
            "count": 0,
        }

    # Format output
    lines = [f"## Entities matching: {entity_name}\n"]

    for entity in entities:
        name = entity.get("name", "Unknown")
        entity_type = entity.get("type", "unknown")
        summary = entity.get("summary", "")
        relationships = entity.get("relationships", [])

        lines.append(f"### {name} ({entity_type})")

        if summary:
            lines.append(f"{summary}")

        if relationships:
            lines.append("\n**Relationships:**")
            for rel in relationships[:5]:  # Limit to 5 relationships
                target = rel.get("target", "?")
                rel_type = rel.get("relationship", "RELATED_TO")
                target_type = rel.get("target_type", "")
                type_suffix = f" ({target_type})" if target_type else ""
                lines.append(f"- {rel_type}: {target}{type_suffix}")

        lines.append("")

    return {
        "content": "\n".join(lines),
        "found": True,
        "count": len(entities),
    }
