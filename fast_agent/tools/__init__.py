"""Fast agent tools."""

from .fast_search import FAST_SEARCH_TOOL, fast_search_kb
from .get_entities import GET_ENTITIES_TOOL, get_entities_fast

__all__ = [
    "FAST_SEARCH_TOOL",
    "fast_search_kb",
    "GET_ENTITIES_TOOL",
    "get_entities_fast",
]
