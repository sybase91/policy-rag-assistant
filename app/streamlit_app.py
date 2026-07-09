"""Streamlit UI for PolicyOps Agent and the NIST Policy RAG Assistant.

When Agent Mode is OFF, the app preserves the original RAG chat behavior.
When Agent Mode is ON, queries run through the PolicyOps Agent workflow.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import run_policy_agent
from src.config import CHAT_MODEL, CHROMA_PERSIST_DIR
from src.generate import answer_question

_PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "replace_this_with_your_real_key_locally",
    "your_real_key_here",
}

RAG_EXAMPLE_QUESTIONS = [
    "What is prompt injection?",
    "What are the core functions of the NIST AI RMF?",
    "What risks are specific to generative AI systems?",
    "How does cybersecurity governance connect to AI governance?",
    "What is my company's refund policy?",
]

AGENT_EXAMPLE_QUESTIONS = [
    "Can I reimburse a client dinner for INR 18,000 if two external guests attended and I paid with my own card?",
    "Am I allowed to work from home for two weeks because of a medical reason?",
    "Can I accept a INR 12,000 gift from a vendor?",
    "What is the travel reimbursement policy?",
    "Can I book a hotel upgrade during a business trip?",
    "Can I share customer data with an external vendor for analysis?",
]


def init_session_state() -> None:
    """Create session state defaults on first load."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_mode" not in st.session_state:
        st.session_state.agent_mode = False


def get_setup_error() -> str | None:
    """Return a setup error message, or None if the backend looks ready."""
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


def render_sidebar() -> bool:
    """Render sidebar content and return whether Agent Mode is enabled."""
    with st.sidebar:
        agent_mode = st.toggle(
            "Agent Mode",
            value=st.session_state.agent_mode,
            help="Run the PolicyOps Agent workflow for Acme Corp policy scenarios.",
        )
        st.session_state.agent_mode = agent_mode

        if agent_mode:
            st.header("Knowledge base")
            st.markdown(
                "- Acme Corp Travel and Expense Policy\n"
                "- Acme Corp Reimbursement Policy\n"
                "- Acme Corp Gifts and Hospitality Policy\n"
                "- Acme Corp Remote Work Policy\n"
                "- Acme Corp Approval Matrix\n"
                "- Acme Corp Data Access Policy"
            )
            st.header("Current project phase")
            st.markdown("PolicyOps Agent - Phase 1 foundation")
            st.header("Workflow")
            st.markdown(
                "Intent -> Scenario facts -> Retrieval -> Missing info -> "
                "Decision -> Next steps -> Final answer"
            )
            examples = AGENT_EXAMPLE_QUESTIONS
        else:
            st.header("Knowledge base")
            st.markdown(
                "- NIST AI Risk Management Framework 1.0\n"
                "- NIST AI 600-1 Generative AI Profile\n"
                "- OWASP Top 10 for LLM Applications 2025\n"
                "- NIST Cybersecurity Framework 2.0"
            )
            st.header("Current project phase")
            st.markdown("NIST Policy RAG Assistant")
            st.header("Architecture flow")
            st.markdown(
                "PDFs -> Chunks -> Embeddings -> Chroma -> "
                "Retrieval -> Grounded Answer -> UI"
            )
            examples = RAG_EXAMPLE_QUESTIONS

        st.header("Example questions")
        for example in examples:
            st.markdown(f"- {example}")

        st.divider()
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    return agent_mode


def render_rag_extras(result: dict, message_index: int) -> None:
    """Show RAG sources, debug info, and feedback placeholders."""
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
        if st.button("Helpful", key=f"helpful_{message_index}"):
            st.info("Feedback capture will be added in a later phase.")
    with col_needs_work:
        if st.button("Needs improvement", key=f"needs_work_{message_index}"):
            st.info("Feedback capture will be added in a later phase.")


def render_agent_extras(agent_state: dict, message_index: int) -> None:
    """Show decision card, sources, trace, and state JSON for agent replies."""
    st.subheader("Decision Card")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Intent", agent_state.get("intent", "unknown"))
    col2.metric("Decision", agent_state.get("policy_decision", "Unknown"))
    col3.metric("Risk Level", agent_state.get("risk_level", "Unknown"))
    col4.metric("Confidence", f"{agent_state.get('confidence', 0.0):.2f}")

    with st.expander("Retrieved Sources"):
        chunks = agent_state.get("retrieved_chunks", [])
        if not chunks:
            st.write("(none)")
        else:
            for index, chunk in enumerate(chunks, start=1):
                st.markdown(
                    f"{index}. **{chunk.get('source')}** | "
                    f"{chunk.get('section')} | score={chunk.get('score')}"
                )
                st.caption(chunk.get("text", "")[:240] + "...")

    with st.expander("Agent Trace"):
        trace = agent_state.get("trace", [])
        if not trace:
            st.write("(empty)")
        else:
            for step in trace:
                st.markdown(
                    f"**{step.get('step_name')}** ({step.get('status')}) - "
                    f"{step.get('message')}"
                )

    with st.expander("Agent State JSON"):
        st.json(agent_state)


def render_message(msg: dict, message_index: int) -> None:
    """Render one stored chat message."""
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("mode") == "agent" and msg.get("agent_state"):
                render_agent_extras(msg["agent_state"], message_index)
            else:
                render_rag_extras(
                    {
                        "sources": msg.get("sources", []),
                        "retrieved_context_count": msg.get("retrieved_context_count", 0),
                    },
                    message_index,
                )


def handle_new_rag_question(question: str) -> None:
    """Process a question with the original RAG answer flow."""
    st.session_state.messages.append({"role": "user", "content": question, "mode": "rag"})

    with st.chat_message("user"):
        st.markdown(question)

    setup_error = get_setup_error()
    if setup_error:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": setup_error,
                "mode": "rag",
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
            render_rag_extras(result, len(st.session_state.messages))

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "mode": "rag",
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
                    "mode": "rag",
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
                    "mode": "rag",
                    "sources": [],
                    "retrieved_context_count": 0,
                }
            )

    st.rerun()


def handle_new_agent_question(question: str) -> None:
    """Process a question with the PolicyOps Agent workflow."""
    st.session_state.messages.append({"role": "user", "content": question, "mode": "agent"})

    with st.chat_message("user"):
        st.markdown(question)

    setup_error = get_setup_error()
    if setup_error:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": setup_error,
                "mode": "agent",
                "agent_state": {},
            }
        )
        st.rerun()

    with st.chat_message("assistant"):
        try:
            with st.spinner("Running PolicyOps Agent workflow..."):
                agent_state = run_policy_agent(question)

            st.markdown(agent_state["final_answer"])
            render_agent_extras(agent_state, len(st.session_state.messages))

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": agent_state["final_answer"],
                    "mode": "agent",
                    "agent_state": agent_state,
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
                    "mode": "agent",
                    "agent_state": {},
                }
            )
        except Exception as exc:
            error_text = f"PolicyOps Agent failed for this request: {exc}"
            st.error(error_text)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": error_text,
                    "mode": "agent",
                    "agent_state": {},
                }
            )

    st.rerun()


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="PolicyOps Agent",
        page_icon="🧠",
        layout="wide",
    )

    init_session_state()
    agent_mode = render_sidebar()

    if agent_mode:
        st.title("PolicyOps Agent")
        st.markdown(
            "Ask **Acme Corp workplace policy** questions and inspect the agent "
            "workflow: intent, retrieval, decision, next steps, and trace."
        )
        chat_placeholder = "Ask an Acme Corp policy scenario..."
    else:
        st.title("Enterprise AI Policy RAG Assistant")
        st.markdown(
            "Ask questions about **public AI governance and LLM security documents**. "
            "Answers are grounded in NIST and OWASP policy PDFs with source citations."
        )
        chat_placeholder = "Ask a question about AI governance or LLM security..."

    setup_error = get_setup_error()
    if setup_error:
        st.error(setup_error)
        if agent_mode:
            st.info(
                "For Acme Corp policies, also run: python scripts/ingest_mock_policies.py"
            )

    for index, msg in enumerate(st.session_state.messages):
        render_message(msg, index)

    question = st.chat_input(chat_placeholder)
    if question:
        if agent_mode:
            handle_new_agent_question(question)
        else:
            handle_new_rag_question(question)


if __name__ == "__main__":
    main()
