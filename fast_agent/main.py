"""
Fast Agent API - single SSE streaming endpoint.

Target: <10ms overhead before agent processing.
"""

import json
import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent import fast_chat_stream
from .config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fast Agent API",
    description="Lightning-fast agent for 4-second responses",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    """Minimal chat request model."""

    message: str = Field(..., description="User message")
    org_id: str = Field(..., description="Organization ID for multi-tenant filtering")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation history")


def verify_api_key(x_api_key: str = Header(...)) -> bool:
    """Verify API key from header."""
    config = get_config()
    if x_api_key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    x_api_key: str = Header(...),
):
    """
    Streaming chat endpoint with SSE.

    Event types:
    - status: Progress update
    - tool_use: Tool being called (includes name and input)
    - answer: Final answer with metadata
    - error: Error message

    Target: <4 seconds total response time
    """
    verify_api_key(x_api_key)

    logger.info(f"[API] Request: '{request.message[:50]}...' org_id={request.org_id}")

    async def generate():
        async for chunk in fast_chat_stream(
            message=request.message,
            org_id=request.org_id,
            session_id=request.session_id,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Fast Agent API",
        "version": "0.1.0",
        "description": "Lightning-fast agent for 4-second responses",
        "endpoints": {
            "/chat/stream": "POST - Streaming chat (SSE)",
            "/health": "GET - Health check",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
