"""
Minimal agentic loop for fast agent.

Uses Gemini 2.5 Flash-Lite for fast responses.
Target: ~1000ms base overhead + tool time.
"""

import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import google.generativeai as genai

from .config import get_config
from .tools.fast_search import FAST_SEARCH_TOOL, fast_search_kb
from .tools.get_entities import GET_ENTITIES_TOOL, get_entities_fast

logger = logging.getLogger(__name__)

# Simple in-memory session store
_sessions: Dict[str, List[Dict[str, Any]]] = {}
MAX_HISTORY = 5  # Keep last 5 message pairs for better context

# Cached Gemini model
_gemini_model = None


def get_gemini_model():
    """Get singleton Gemini model."""
    global _gemini_model
    if _gemini_model is None:
        config = get_config()
        genai.configure(api_key=config.google_api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")
        logger.info("Gemini 2.5 Flash-Lite model initialized")
    return _gemini_model


async def should_search_kb(message: str, model) -> bool:
    """Quick classification: does this message need a KB search?"""
    classify_prompt = f"""Classify this message. Reply with ONLY "SEARCH" or "CHAT".

SEARCH: Questions about facts, products, services, pricing, companies, documents
CHAT: Greetings, thanks, acknowledgments, casual conversation

Message: "{message}"
Reply:"""

    try:
        response = model.generate_content(
            classify_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.0,
            ),
        )
        result = response.text.strip().upper()
        return "SEARCH" in result
    except Exception:
        # Default to search if classification fails
        return True


SYSTEM_PROMPT = """Fast assistant for Factor8 Knowledge Hub. Be BRIEF (2-3 sentences max).

Tools: search_kb (documents), get_entities (relationships)

Rules:
- Greetings: respond directly, no tools
- Questions: use ONE tool only, then answer immediately
- Keep answers under 50 words
- Cite source document name

Org: {org_id}
"""

# Tools for Claude API
TOOLS = [FAST_SEARCH_TOOL, GET_ENTITIES_TOOL]


async def execute_tool(name: str, args: Dict[str, Any], org_id: str) -> str:
    """Execute a tool and return result as string."""
    logger.info(f"[AGENT] Executing tool: {name}")

    if name == "search_kb":
        result = await fast_search_kb(
            query=args.get("query", ""),
            org_id=org_id,
            limit=5,
        )
        return result.get("content", "No results")

    elif name == "get_entities":
        result = await get_entities_fast(
            entity_name=args.get("entity_name", ""),
            org_id=org_id,
        )
        return result.get("content", "No entities found")

    return f"Unknown tool: {name}"


def get_session_history(session_id: Optional[str]) -> List[Dict[str, Any]]:
    """Get session history (max 3 message pairs)."""
    if not session_id:
        return []
    return _sessions.get(session_id, [])[-MAX_HISTORY * 2:]  # user + assistant pairs


def add_to_session(session_id: Optional[str], role: str, content: str):
    """Add message to session history."""
    if not session_id:
        return
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].append({"role": role, "content": content})
    # Trim to max history (pairs of messages)
    _sessions[session_id] = _sessions[session_id][-MAX_HISTORY * 2:]


def _is_vague_answer(text: str) -> bool:
    """Detect if answer is too vague and needs retry with more context."""
    vague_phrases = [
        "might be", "could be", "i'm not sure", "cannot determine",
        "i don't have enough", "not enough information", "unclear",
        "may vary", "depends on", "contact for more"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in vague_phrases) or len(text) < 80


async def fast_chat_stream(
    message: str,
    org_id: str,
    session_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Fast chat with Gemini 2.5 Flash-Lite.

    Uses quick classification to decide: search KB or respond directly.

    Target: <3 seconds for searches, <1 second for direct responses
    """
    start_time = datetime.now()
    model = get_gemini_model()

    # Add user message to session
    add_to_session(session_id, "user", message)

    try:
        # Step 1: Quick classification - should we search?
        logger.info(f"[AGENT] Processing: '{message[:50]}'")
        needs_search = await should_search_kb(message, model)

        if not needs_search:
            # Direct response for greetings/casual chat
            logger.info("[AGENT] Classified as CHAT - responding directly")

            chat_prompt = f"""You are a friendly assistant for the Factor8 Knowledge Hub.
Respond naturally and briefly (1-2 sentences) to: "{message}"
Be warm and helpful. Offer to help with questions about the knowledge base."""

            response = model.generate_content(
                chat_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=256,
                    temperature=0.3,
                ),
            )

            final_content = response.text
            add_to_session(session_id, "assistant", final_content)

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"[AGENT] Done in {duration_ms:.0f}ms")

            yield {
                "type": "answer",
                "data": final_content,
                "metadata": {
                    "duration_ms": round(duration_ms),
                    "tools_used": [],
                    "iterations": 1,
                    "model": "gemini-2.5-flash-lite",
                },
            }
            return

        # Step 2: Search KB for information queries
        logger.info("[AGENT] Classified as SEARCH - querying KB")
        yield {"type": "status", "data": "Searching..."}
        yield {"type": "tool_use", "data": {"name": "search_kb", "input": {"query": message}}}

        search_result = await fast_search_kb(
            query=message,
            org_id=org_id,
            limit=8,
        )

        search_content = search_result.get("content", "No results found")
        source_docs = search_result.get("source_documents", [])
        sources_list = ", ".join(source_docs[:5]) if source_docs else "Unknown"
        logger.info(f"[AGENT] Search done, {search_result.get('results_count', 0)} results")

        # Build conversation history for context
        history = get_session_history(session_id)
        conversation_context = ""
        if history:
            conversation_context = "\n\n--- PREVIOUS CONVERSATION ---\n"
            for msg in history[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"][:400] + "..." if len(msg["content"]) > 400 else msg["content"]
                conversation_context += f"{role}: {content}\n"
            conversation_context += "--- END PREVIOUS CONVERSATION ---\n"

        # Step 3: Generate answer based on search results
        answer_prompt = f"""You are a knowledgeable assistant for this organization's knowledge base.
{conversation_context}
User question: {message}

Context:
{search_content}

RESPONSE RULES:
- Answer directly and confidently, as if you know this information firsthand
- NEVER mention "search results", "the documents", "based on the provided", "according to", "the context" or similar meta-references
- NEVER say "I don't have information" - give the best answer from context
- Use prose paragraphs only (no bullets or lists)
- Keep to 1-3 paragraphs
- Include specific details, numbers, and facts when available
- Write naturally, like an employee who knows the company well
- End with exactly: "Sources: {sources_list}\""""

        response = model.generate_content(
            answer_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.3,
            ),
        )

        final_content = response.text

        # Retry if vague
        if _is_vague_answer(final_content) and search_result.get("results_count", 0) < 12:
            logger.info("[AGENT] Vague answer, retrying with more results")
            yield {"type": "status", "data": "Getting more context..."}

            search_result = await fast_search_kb(query=message, org_id=org_id, limit=12)
            search_content = search_result.get("content", "No results found")

            retry_response = model.generate_content(
                answer_prompt.replace(search_content, search_result.get("content", "")),
                generation_config=genai.types.GenerationConfig(max_output_tokens=2048, temperature=0.3),
            )
            final_content = retry_response.text

        # Add assistant response to session
        add_to_session(session_id, "assistant", final_content)

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"[AGENT] Done in {duration_ms:.0f}ms")

        yield {
            "type": "answer",
            "data": final_content,
            "metadata": {
                "duration_ms": round(duration_ms),
                "tools_used": ["search_kb"],
                "iterations": 1,
                "model": "gemini-2.5-flash-lite",
            },
        }

    except Exception as e:
        logger.error(f"[AGENT] Error: {e}", exc_info=True)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        yield {
            "type": "error",
            "data": str(e),
            "metadata": {"duration_ms": round(duration_ms)},
        }
