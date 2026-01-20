"""
Streamlit Chat UI for Fast Agent.

Usage:
    1. Start FastAPI backend: uvicorn fast_agent.main:app --port 8003
    2. Run this UI: streamlit run ui/app.py
"""
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
    page_title="Fast Agent",
    page_icon="lightning",
    layout="wide"
)

# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    /* Fix chat input at bottom */
    .stChatInput {
        position: fixed;
        bottom: 0;
        width: calc(100% - 350px);
        background: var(--background-color);
        padding: 1rem 0;
        z-index: 999;
    }

    /* Add padding at bottom */
    .main .block-container {
        padding-bottom: 100px;
    }

    /* Metrics styling */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8003"

if "api_key" not in st.session_state:
    st.session_state.api_key = "your-api-key-for-authentication"

if "org_id" not in st.session_state:
    st.session_state.org_id = "00000000-0000-0000-0000-000000000001"

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
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("Fast Agent")
    st.caption("Lightning-fast responses powered by Gemini 2.5 Flash")

    st.divider()

    st.subheader("Settings")

    api_url = st.text_input(
        "API URL",
        value=st.session_state.api_url,
        help="URL of the Fast Agent API"
    )
    if api_url != st.session_state.api_url:
        st.session_state.api_url = api_url

    api_key = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        help="Your API authentication key"
    )
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key

    org_id = st.text_input(
        "Organization ID",
        value=st.session_state.org_id,
        help="Your organization UUID"
    )
    if org_id != st.session_state.org_id:
        st.session_state.org_id = org_id

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()

    st.divider()

    # Performance stats
    st.subheader("Performance")
    if st.session_state.messages:
        # Calculate average response time
        times = [m.get("metadata", {}).get("duration_ms", 0)
                 for m in st.session_state.messages
                 if m.get("role") == "assistant" and m.get("metadata")]
        if times:
            avg_time = sum(times) / len(times) / 1000
            st.metric("Avg Response", f"{avg_time:.2f}s")
            st.caption(f"Based on {len(times)} responses")

    # Status
    st.divider()
    if st.session_state.api_key:
        st.success("Ready")
    else:
        st.warning("Enter API Key")


# ============================================================
# MAIN CONTENT
# ============================================================

st.title("Fast Agent Chat")
st.caption("Ask questions about your knowledge base - responses in ~3 seconds")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show metrics for assistant messages
        if msg["role"] == "assistant" and msg.get("metadata"):
            metadata = msg["metadata"]
            duration_ms = metadata.get("duration_ms", 0)
            model = metadata.get("model", "unknown")

            st.caption(f"{duration_ms/1000:.2f}s | {model}")

# Chat input
if prompt := st.chat_input("Ask about your knowledge base..."):
    if not st.session_state.api_key:
        st.error("Please enter your API key in the sidebar.")
    else:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Stream assistant response
        with st.chat_message("assistant"):
            with st.status("Thinking...", expanded=True) as status:
                response_placeholder = st.empty()

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
                                response_placeholder.markdown(full_response)

                            elif chunk["type"] == "error":
                                full_response = f"Error: {chunk['content']}"
                                response_placeholder.markdown(full_response)

                        return full_response, metadata

                    full_response, metadata = run_async(collect_response())

                    # Update status
                    duration_ms = metadata.get("duration_ms", 0)
                    status.update(
                        label=f"Done in {duration_ms/1000:.2f}s",
                        state="complete",
                        expanded=False
                    )

                except Exception as e:
                    status.update(label=f"Error: {str(e)}", state="error")
                    full_response = f"Error: {str(e)}"
                    metadata = {}

            # Display final response
            response_placeholder.markdown(full_response)

            # Show metrics
            if metadata:
                duration_ms = metadata.get("duration_ms", 0)
                model = metadata.get("model", "gemini-2.5-flash")
                tools = metadata.get("tools_used", [])

                cols = st.columns(3)
                cols[0].metric("Response Time", f"{duration_ms/1000:.2f}s")
                cols[1].metric("Model", model.split("-")[-1].title())
                cols[2].metric("Tools", len(tools))

            # Save assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
                "metadata": metadata
            })
