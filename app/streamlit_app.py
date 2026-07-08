"""Streamlit chat UI for the Enterprise AI Policy RAG Assistant.

Streamlit turns Python scripts into local web apps with minimal frontend code.
A chat UI lets users type questions and see assistant replies in a thread.
st.chat_input is the text box at the bottom; st.chat_message renders each bubble.
st.session_state keeps chat history across reruns while the app is open.
The UI calls answer_question() from src.generate instead of duplicating RAG logic.
Sources are shown separately so users can verify claims apart from the answer text.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# Streamlit runs this file directly, so add the project root for src imports.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import CHAT_MODEL, CHROMA_PERSIST_DIR
from src.generate import answer_question

_PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "replace_this_with_your_real_key_locally",
    "your_real_key_here",
}

EXAMPLE_QUESTIONS = [
    "What is prompt injection?",
    "What are the core functions of the NIST AI RMF?",
    "What risks are specific to generative AI systems?",
    "How does cybersecurity governance connect to AI governance?",
    "What is my company's refund policy?",
]


def init_session_state() -> None:
    """Create the messages list in session state if this is the first load."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def get_setup_error() -> str | None:
    """Return a user-friendly setup error, or None if the backend looks ready."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return (
            "No .env file found. Copy .env.example to .env and add your "
            "OpenAI API key, then restart the app."
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key in _PLACEHOLDER_API_KEYS:
        return (
            "OpenAI API key is missing or still set to a placeholder. "
            "Edit your local .env file and restart the app."
        )

    chroma_db_file = CHROMA_PERSIST_DIR / "chroma.sqlite3"
    if not CHROMA_PERSIST_DIR.exists() or not chroma_db_file.exists():
        return (
            "No Chroma index found. Run python -m src.embed --rebuild first."
        )

    return None


def render_sidebar() -> None:
    """Render sidebar with corpus info, examples, and Clear chat button."""
    with st.sidebar:
        st.header("Knowledge base")
        st.markdown(
            "- NIST AI Risk Management Framework 1.0\n"
            "- NIST AI 600-1 Generative AI Profile\n"
            "- OWASP Top 10 for LLM Applications 2025\n"
            "- NIST Cybersecurity Framework 2.0"
        )

        st.header("Current project phase")
        st.markdown("Phase 5 — Streamlit Chat UI")

        st.header("Architecture flow")
        st.markdown(
            "PDFs → Chunks → Embeddings → Chroma → "
            "Retrieval → Grounded Answer → UI"
        )

        st.header("Example questions")
        for example in EXAMPLE_QUESTIONS:
            st.markdown(f"- {example}")

        st.divider()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


def render_assistant_extras(result: dict, message_index: int) -> None:
    """Show sources, debug info, and feedback placeholders for one assistant reply."""
    sources = result.get("sources", [])

    with st.expander("Sources used"):
        if not sources:
            st.write("(none)")
        else:
            for index, source in enumerate(sources, start=1):
                st.markdown(
                    f"{index}. **{source['source_file']}** | "
                    f"page {source['page']} | "
                    f"chunk_id={source['chunk_id']}"
                )

    with st.expander("Debug info"):
        st.markdown(
            f"- **Retrieved context count:** {result.get('retrieved_context_count', 0)}\n"
            f"- **Model:** {CHAT_MODEL}\n"
            f"- **Note:** This is a local prototype."
        )

    col_helpful, col_needs_work = st.columns(2)
    with col_helpful:
        if st.button("👍 Helpful", key=f"helpful_{message_index}"):
            st.info("Feedback capture will be added in a later phase.")
    with col_needs_work:
        if st.button("👎 Needs improvement", key=f"needs_work_{message_index}"):
            st.info("Feedback capture will be added in a later phase.")


def render_message(msg: dict, message_index: int) -> None:
    """Render one chat message from session state history."""
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_assistant_extras(
                {
                    "sources": msg.get("sources", []),
                    "retrieved_context_count": msg.get("retrieved_context_count", 0),
                },
                message_index,
            )


def handle_new_question(question: str) -> None:
    """Process a new user question and append user/assistant messages."""
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.markdown(question)

    setup_error = get_setup_error()
    if setup_error:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": setup_error,
                "sources": [],
                "retrieved_context_count": 0,
            }
        )
        st.rerun()

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching documents and generating answer..."):
                result = answer_question(question)

            st.markdown(result["answer"])
            render_assistant_extras(result, len(st.session_state.messages))

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result.get("sources", []),
                    "retrieved_context_count": result.get("retrieved_context_count", 0),
                }
            )
        except SystemExit:
            error_text = (
                "Backend setup error. Check your API key and Chroma index, "
                "then restart the app."
            )
            st.error(error_text)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_text,
                    "sources": [],
                    "retrieved_context_count": 0,
                }
            )
        except Exception as exc:
            error_text = f"Something went wrong while generating the answer: {exc}"
            st.error(error_text)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_text,
                    "sources": [],
                    "retrieved_context_count": 0,
                }
            )

    st.rerun()


def main() -> None:
    """Run the Streamlit chat application."""
    st.set_page_config(
        page_title="Enterprise AI Policy RAG Assistant",
        page_icon="🧠",
        layout="wide",
    )

    init_session_state()
    render_sidebar()

    st.title("Enterprise AI Policy RAG Assistant")
    st.markdown(
        "Ask questions about **public AI governance and LLM security documents**. "
        "Answers are grounded in NIST and OWASP policy PDFs with source citations."
    )

    setup_error = get_setup_error()
    if setup_error:
        st.error(setup_error)

    # Step 1: Re-render chat history from session state.
    for index, msg in enumerate(st.session_state.messages):
        render_message(msg, index)

    # Step 2: Accept a new question from the chat input box.
    question = st.chat_input("Ask a question about AI governance or LLM security...")
    if question:
        handle_new_question(question)


if __name__ == "__main__":
    main()
