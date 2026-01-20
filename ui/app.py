"""
Streamlit Chat UI for Factor8 Fast Agent.

Usage:
    streamlit run ui/app.py
"""
import os
import streamlit as st
import httpx
import json
import asyncio
import sys

# Fix for Windows asyncio
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Agent A",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar completely
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}

    /* Chat input styling */
    .stChatInput {
        position: fixed;
        bottom: 0;
        width: 100%;
        max-width: 730px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--background-color);
        padding: 1rem 0;
        z-index: 999;
    }

    /* Add padding at bottom for chat input */
    .main .block-container {
        padding-bottom: 100px;
        max-width: 800px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_url" not in st.session_state:
    st.session_state.api_url = "https://claude-code-dev.fly.dev"

if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("API_KEY", "")

if "org_id" not in st.session_state:
    st.session_state.org_id = os.environ.get("ORG_ID", "00000000-0000-0000-0000-000000000001")

if "session_id" not in st.session_state:
    st.session_state.session_id = None

# ============================================================
# API CLIENT
# ============================================================

async def stream_chat(message: str):
    """Stream chat response from Fast Agent API."""
    headers = {"X-API-Key": st.session_state.api_key}

    payload = {
        "message": message,
        "org_id": st.session_state.org_id,
        "session_id": st.session_state.session_id,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{st.session_state.api_url}/chat/stream",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"API error {response.status_code}: {error_text.decode()}")

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")
                        event_data = data.get("data", "")
                        metadata = data.get("metadata", {})

                        if event_type == "status":
                            yield {"type": "status", "detail": event_data}

                        elif event_type == "tool_use":
                            tool_name = event_data.get("name", "tool") if isinstance(event_data, dict) else "tool"
                            tool_input = event_data.get("input", {}) if isinstance(event_data, dict) else {}
                            query = tool_input.get("query", "")[:50] if tool_input else ""
                            yield {"type": "status", "detail": f"Searching: {query}..."}

                        elif event_type == "answer":
                            yield {
                                "type": "answer",
                                "content": event_data,
                                "metadata": metadata
                            }

                        elif event_type == "error":
                            yield {"type": "error", "content": event_data}

                    except json.JSONDecodeError:
                        pass


def run_async(coro):
    """Run async coroutine in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================
# MAIN CONTENT
# ============================================================

st.title("⚡ Agent A")
st.caption("Ask questions about your knowledge base")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show metrics for assistant messages
        if msg["role"] == "assistant" and msg.get("metadata"):
            metadata = msg["metadata"]
            duration_ms = metadata.get("duration_ms", 0)
            st.caption(f"⚡ {duration_ms/1000:.2f}s")

# Chat input
if prompt := st.chat_input("Ask anything..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        # Status box for streaming updates only
        with st.status("Thinking...", expanded=True) as status:
            try:
                async def collect_response():
                    full_response = ""
                    metadata = {}

                    async for chunk in stream_chat(prompt):
                        if chunk["type"] == "status":
                            status.update(label=chunk.get("detail", "Processing..."))

                        elif chunk["type"] == "answer":
                            full_response = chunk["content"]
                            metadata = chunk.get("metadata", {})

                        elif chunk["type"] == "error":
                            full_response = f"Error: {chunk['content']}"

                    return full_response, metadata

                full_response, metadata = run_async(collect_response())

                # Update status to complete and collapse
                duration_ms = metadata.get("duration_ms", 0)
                status.update(
                    label=f"⚡ {duration_ms/1000:.2f}s",
                    state="complete",
                    expanded=False
                )

            except Exception as e:
                status.update(label=f"Error: {str(e)}", state="error")
                full_response = f"Error: {str(e)}"
                metadata = {}

        # Display final response OUTSIDE the status box (always visible)
        st.markdown(full_response)

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "metadata": metadata
        })
