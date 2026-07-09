"""Streamlit UI for PolicyOps Agent and the NIST Policy RAG Assistant.

Standard RAG Chat and PolicyOps Agent use separate thread stores so histories
never mix when switching modes.
"""

from __future__ import annotations

import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import run_policy_agent
from agent.citation_verifier import clean_excerpt
from src.config import CHAT_MODEL, CHROMA_PERSIST_DIR
from src.generate import answer_question

_PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "replace_this_with_your_real_key_locally",
    "your_real_key_here",
}

MODE_STANDARD = "standard"
MODE_AGENT = "agent"

MODE_OPTIONS = ["Standard RAG Chat", "PolicyOps Agent"]
MODE_LABEL_TO_KEY = {
    "Standard RAG Chat": MODE_STANDARD,
    "PolicyOps Agent": MODE_AGENT,
}
MODE_KEY_TO_LABEL = {v: k for k, v in MODE_LABEL_TO_KEY.items()}

MODE_DESCRIPTIONS = {
    MODE_STANDARD: "Use this for direct questions over the knowledge base.",
    MODE_AGENT: (
        "Use this for scenario-based policy decisions with trace, risk, "
        "citations, and next steps."
    ),
}

RAG_EXAMPLE_QUESTIONS = [
    "What is prompt injection?",
    "What are the core functions of the NIST AI RMF?",
    "What risks are specific to generative AI systems?",
    "How does cybersecurity governance connect to AI governance?",
]

AGENT_EXAMPLE_QUESTIONS = [
    "Can I reimburse a client dinner for INR 18,000 if two external guests attended and I paid with my own card?",
    "Can I accept an INR 12,000 gift from a vendor?",
    "Am I allowed to work from home for two weeks because of a medical reason?",
    "Can I share customer data with an external vendor for analysis?",
    "I lost my receipt for a taxi ride. Can I still claim reimbursement?",
    "Can I book a hotel upgrade during a business trip?",
]

WORKFLOW_PIPELINE = (
    "User Query -> Intent -> Scenario Facts -> Retrieval -> "
    "Missing Info -> Decision -> Citation Verify -> Clarifying Q -> "
    "Next Steps -> Final Answer"
)

RAG_PIPELINE = "PDFs -> Chunks -> Embeddings -> Chroma -> Retrieval -> Answer"

TRACE_STATUS_ICON = {
    "completed": "✓",
    "started": "→",
    "failed": "✕",
}

GOVERNANCE_DOCS = [
    ("NIST AI Risk Management Framework 1.0", "Public AI governance PDF", "NIST RAG corpus"),
    ("NIST AI 600-1 Generative AI Profile", "Public generative AI profile", "NIST RAG corpus"),
    ("OWASP Top 10 for LLM Applications 2025", "Public LLM security guidance", "NIST RAG corpus"),
    ("NIST Cybersecurity Framework 2.0", "Public cybersecurity framework", "NIST RAG corpus"),
]

ACME_POLICY_DOCS = [
    ("Travel and Expense Policy", "Synthetic workplace demo policy", "Acme mock corpus"),
    ("Reimbursement Policy", "Synthetic workplace demo policy", "Acme mock corpus"),
    ("Gifts and Hospitality Policy", "Synthetic workplace demo policy", "Acme mock corpus"),
    ("Remote Work Policy", "Synthetic workplace demo policy", "Acme mock corpus"),
    ("Approval Matrix", "Synthetic workplace demo policy", "Acme mock corpus"),
    ("Data Access Policy", "Synthetic workplace demo policy", "Acme mock corpus"),
]


# ---------------------------------------------------------------------------
# Thread state helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _threads_key(mode: str) -> str:
    return "standard_threads" if mode == MODE_STANDARD else "agent_threads"


def _active_thread_key(mode: str) -> str:
    return (
        "active_standard_thread_id"
        if mode == MODE_STANDARD
        else "active_agent_thread_id"
    )


def _empty_thread(title: str = "New chat") -> dict:
    return {
        "thread_id": str(uuid.uuid4()),
        "title": title,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages": [],
    }


def initialize_thread_state() -> None:
    """Create separated thread stores for each assistant mode."""
    if "standard_threads" not in st.session_state:
        default = _empty_thread()
        st.session_state.standard_threads = {default["thread_id"]: default}
        st.session_state.active_standard_thread_id = default["thread_id"]

    if "agent_threads" not in st.session_state:
        default = _empty_thread()
        st.session_state.agent_threads = {default["thread_id"]: default}
        st.session_state.active_agent_thread_id = default["thread_id"]

    if "assistant_mode" not in st.session_state:
        st.session_state.assistant_mode = MODE_AGENT

    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None

    if "pending_mode" not in st.session_state:
        st.session_state.pending_mode = None


def create_new_thread(mode: str) -> str:
    """Create a new thread for the given mode and make it active."""
    thread = _empty_thread()
    threads = st.session_state[_threads_key(mode)]
    threads[thread["thread_id"]] = thread
    st.session_state[_active_thread_key(mode)] = thread["thread_id"]
    return thread["thread_id"]


def get_active_thread(mode: str) -> dict:
    """Return the active thread dict for a mode."""
    threads = st.session_state[_threads_key(mode)]
    active_id = st.session_state[_active_thread_key(mode)]
    if active_id not in threads:
        create_new_thread(mode)
        active_id = st.session_state[_active_thread_key(mode)]
    return threads[active_id]


def set_active_thread(mode: str, thread_id: str) -> None:
    """Switch the active thread within a mode."""
    threads = st.session_state[_threads_key(mode)]
    if thread_id in threads:
        st.session_state[_active_thread_key(mode)] = thread_id


def clear_active_thread(mode: str) -> None:
    """Clear messages on the active thread without deleting the thread."""
    thread = get_active_thread(mode)
    thread["messages"] = []
    thread["title"] = "New chat"
    thread["updated_at"] = _now_iso()


def list_threads(mode: str) -> list[dict]:
    """Return threads for a mode, most recently updated first."""
    threads = st.session_state[_threads_key(mode)].values()
    return sorted(threads, key=lambda t: t.get("updated_at", ""), reverse=True)


def generate_thread_title(first_user_message: str, max_len: int = 48) -> str:
    """Build a short thread title from the first user message."""
    cleaned = re.sub(r"\s+", " ", first_user_message.strip())
    if not cleaned:
        return "New chat"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def append_message(
    mode: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Append a message to the active thread for the given mode."""
    thread = get_active_thread(mode)
    message: dict = {"role": role, "content": content}
    if metadata:
        message["metadata"] = metadata
    thread["messages"].append(message)
    thread["updated_at"] = _now_iso()

    if role == "user" and thread["title"] == "New chat":
        thread["title"] = generate_thread_title(content)


def init_session_state() -> None:
    """Create session state defaults on first load."""
    initialize_thread_state()


# ---------------------------------------------------------------------------
# Styling and setup
# ---------------------------------------------------------------------------


def inject_custom_css() -> None:
    """Apply lightweight enterprise dashboard styling."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .po-header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            color: #f8fafc;
        }
        .po-header h1 {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .po-header p {
            margin: 0.35rem 0 0.75rem 0;
            color: #cbd5e1;
            font-size: 0.98rem;
        }
        .po-badge {
            display: inline-block;
            background: #1d4ed8;
            color: #eff6ff;
            border-radius: 999px;
            padding: 0.2rem 0.7rem;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }
        .po-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .po-muted {
            color: #64748b;
            font-size: 0.9rem;
        }
        .po-pipeline {
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            border-radius: 10px;
            padding: 0.7rem 0.9rem;
            font-size: 0.86rem;
            color: #334155;
            margin-bottom: 1rem;
        }
        .po-decision-hero {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.75rem;
        }
        .po-decision-hero .label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #475569;
        }
        .po-decision-hero .value {
            font-size: 1.35rem;
            font-weight: 700;
            color: #1d4ed8;
            margin-top: 0.15rem;
        }
        .po-metric {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.75rem 0.85rem;
            min-height: 88px;
        }
        .po-metric .label {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #64748b;
        }
        .po-metric .value {
            font-size: 1.02rem;
            font-weight: 600;
            color: #0f172a;
            margin-top: 0.2rem;
        }
        .po-decision-allowed { border-left: 4px solid #16a34a; background: #f0fdf4; }
        .po-decision-approval { border-left: 4px solid #2563eb; background: #eff6ff; }
        .po-decision-more-info { border-left: 4px solid #d97706; background: #fffbeb; }
        .po-decision-escalate { border-left: 4px solid #dc2626; background: #fef2f2; }
        .po-decision-denied { border-left: 4px solid #b91c1c; background: #fef2f2; }
        .po-risk-low { border-left: 4px solid #16a34a; }
        .po-risk-medium { border-left: 4px solid #d97706; }
        .po-risk-high { border-left: 4px solid #dc2626; }
        .po-risk-unknown { border-left: 4px solid #94a3b8; }
        .po-citation-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.65rem 0.75rem;
            margin-bottom: 0.5rem;
            font-size: 0.88rem;
        }
        .po-source-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.8rem 0.9rem;
            margin-bottom: 0.65rem;
        }
        .po-source-title {
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 0.2rem;
        }
        .po-source-meta {
            color: #64748b;
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }
        .po-source-excerpt {
            color: #334155;
            font-size: 0.88rem;
            line-height: 1.45;
        }
        .po-trace-step {
            border-left: 3px solid #cbd5e1;
            padding: 0.45rem 0 0.45rem 0.85rem;
            margin-bottom: 0.55rem;
        }
        .po-trace-completed { border-left-color: #16a34a; }
        .po-trace-started { border-left-color: #2563eb; }
        .po-trace-failed { border-left-color: #dc2626; }
        .po-trace-title {
            font-weight: 600;
            color: #0f172a;
            font-size: 0.92rem;
        }
        .po-trace-status {
            display: inline-block;
            font-size: 0.74rem;
            font-weight: 600;
            padding: 0.1rem 0.45rem;
            border-radius: 999px;
            margin-left: 0.35rem;
            background: #e2e8f0;
            color: #334155;
        }
        .po-welcome {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }
        div[data-testid="stSidebar"] {
            background-color: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        return "No Chroma index found. Run python -m src.embed --rebuild first."

    return None


def decision_css_class(decision: str) -> str:
    """Map decision label to accent styling."""
    normalized = (decision or "").strip().lower()
    if normalized == "allowed":
        return "po-decision-allowed"
    if normalized == "needs approval":
        return "po-decision-approval"
    if normalized == "needs more information":
        return "po-decision-more-info"
    if normalized == "escalate":
        return "po-decision-escalate"
    if normalized == "not allowed":
        return "po-decision-denied"
    return "po-risk-unknown"


def risk_css_class(risk_level: str) -> str:
    """Map risk level text to a CSS class name."""
    normalized = (risk_level or "").strip().lower()
    if normalized == "low":
        return "po-risk-low"
    if normalized == "medium":
        return "po-risk-medium"
    if normalized == "high":
        return "po-risk-high"
    return "po-risk-unknown"


# ---------------------------------------------------------------------------
# Parsing and rendering (preserved from Phase 2 UI)
# ---------------------------------------------------------------------------


def parse_agent_answer(text: str) -> dict:
    """Parse the deterministic final answer into display sections."""
    parsed = {
        "decision": "",
        "risk_level": "",
        "confidence": None,
        "short_answer": "",
        "summary": "",
        "rationale": [],
        "missing": [],
        "open_questions": [],
        "approvals": [],
        "sources": [],
        "steps": [],
        "clarifying_question": "",
        "disclaimer": "",
    }
    if not text:
        return parsed

    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("Decision:"):
            parsed["decision"] = line.split(":", 1)[1].strip()
            current = None
            continue
        if line.startswith("Risk level:"):
            parsed["risk_level"] = line.split(":", 1)[1].strip()
            current = None
            continue
        if line.startswith("Confidence:"):
            try:
                raw_conf = line.split(":", 1)[1].strip().replace("%", "")
                value = float(raw_conf)
                parsed["confidence"] = value / 100.0 if value > 1 else value
            except ValueError:
                parsed["confidence"] = None
            current = None
            continue
        if line == "Short answer:":
            current = "short_answer"
            continue
        if line == "Summary:":
            current = "summary"
            continue
        if line == "Why this decision:":
            current = "rationale"
            continue
        if line in {"Missing information:", "Blocking information needed:"}:
            current = "missing"
            continue
        if line == "Open questions:":
            current = "open_questions"
            continue
        if line in {"Relevant policy sources:", "Relevant policy citations:", "Citations:"}:
            current = "sources"
            continue
        if line == "Required approvals:":
            current = "approvals"
            continue
        if line == "Recommended next steps:":
            current = "steps"
            continue
        if line == "Clarifying question:":
            current = "clarifying_question"
            continue
        if line == "Disclaimer:":
            current = "disclaimer"
            continue

        if current == "short_answer":
            parsed["short_answer"] += (line + " ")
        elif current == "summary":
            parsed["summary"] += (line + " ")
        elif current == "rationale" and line.startswith("- "):
            parsed["rationale"].append(line[2:].strip())
        elif current == "missing" and line.startswith("- "):
            parsed["missing"].append(line[2:].strip())
        elif current == "open_questions" and line.startswith("- "):
            parsed["open_questions"].append(line[2:].strip())
        elif current == "approvals" and line.startswith("- "):
            parsed["approvals"].append(line[2:].strip())
        elif current == "sources" and line.startswith("- "):
            parsed["sources"].append(line[2:].strip())
        elif current == "steps":
            cleaned = re.sub(r"^\d+\.\s*", "", line)
            if cleaned:
                parsed["steps"].append(cleaned)
        elif current == "clarifying_question":
            parsed["clarifying_question"] += (line + " ")
        elif current == "disclaimer":
            parsed["disclaimer"] += (line + " ")

    parsed["short_answer"] = parsed["short_answer"].strip()
    parsed["summary"] = parsed["summary"].strip()
    parsed["clarifying_question"] = parsed["clarifying_question"].strip()
    parsed["disclaimer"] = parsed["disclaimer"].strip()
    return parsed


def render_mode_header(mode: str) -> None:
    """Render the main header for the active assistant mode."""
    if mode == MODE_AGENT:
        st.markdown(
            """
            <div class="po-header">
                <span class="po-badge">Phase 2.5 — Answer Quality</span>
                <h1>PolicyOps Agent</h1>
                <p>Use this mode for scenario-based policy decisions with citations, risk, and workflow trace.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="po-pipeline">{WORKFLOW_PIPELINE}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="po-header">
                <span class="po-badge">Standard RAG Chat</span>
                <h1>Standard RAG Chat</h1>
                <p>Ask direct questions over the knowledge base.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Answers are grounded in NIST and OWASP public AI governance documents "
            "with source citations."
        )


def render_empty_thread_examples(mode: str) -> None:
    """Show clickable example questions when the active thread is empty."""
    examples = RAG_EXAMPLE_QUESTIONS if mode == MODE_STANDARD else AGENT_EXAMPLE_QUESTIONS
    title = (
        "Try a knowledge-base question"
        if mode == MODE_STANDARD
        else "Try a policy scenario"
    )

    st.markdown(
        f"""
        <div class="po-welcome">
            <h3 style="margin-top:0;">{title}</h3>
            <p class="po-muted" style="margin-bottom:0;">
                Pick an example below or type your own question in the chat input.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if mode == MODE_AGENT:
        st.caption(
            "Acme Corp policies are fictional demo documents — not legal, HR, "
            "finance, or compliance advice."
        )

    cols = st.columns(2)
    for index, example in enumerate(examples):
        with cols[index % 2]:
            if st.button(
                example,
                key=f"example_{mode}_{index}",
                use_container_width=True,
            ):
                st.session_state.pending_question = example
                st.session_state.pending_mode = mode
                st.rerun()


def render_decision_metrics(agent_state: dict) -> None:
    """Render prominent decision metrics with risk styling and confidence bar."""
    decision = agent_state.get("policy_decision", "Unknown")
    intent = agent_state.get("intent", "unknown")
    risk_level = agent_state.get("risk_level", "Unknown")
    confidence = float(agent_state.get("confidence", 0.0) or 0.0)
    risk_class = risk_css_class(risk_level)
    decision_class = decision_css_class(decision)
    approval_count = len(agent_state.get("required_approvals", []))

    st.markdown(
        f"""
        <div class="po-decision-hero {decision_class}">
            <div class="label">Decision</div>
            <div class="value">{decision}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="po-metric">
                <div class="label">Intent</div>
                <div class="value">{intent}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="po-metric {risk_class}">
                <div class="label">Risk Level</div>
                <div class="value">{risk_level}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="po-metric">
                <div class="label">Confidence</div>
                <div class="value">{confidence:.0%}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(min(max(confidence, 0.0), 1.0))
    with col4:
        st.markdown(
            f"""
            <div class="po-metric">
                <div class="label">Required Approvals</div>
                <div class="value">{approval_count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_final_answer_card(answer_text: str, agent_state: dict) -> None:
    """Render the final answer in a scannable card layout."""
    parsed = parse_agent_answer(answer_text)
    decision = parsed["decision"] or agent_state.get("policy_decision", "Unknown")

    with st.container(border=True):
        st.markdown("### Final Answer")

        short_answer = parsed["short_answer"] or parsed["summary"]
        if short_answer:
            st.markdown("**Short answer**")
            st.write(short_answer)

        rationale = parsed["rationale"] or agent_state.get("rationale_bullets", [])
        if rationale:
            st.markdown("**Why this decision**")
            for item in rationale[:3]:
                st.markdown(f"- {item}")

        approvals = parsed["approvals"] or agent_state.get("required_approvals", [])
        if approvals:
            st.markdown("**Required approvals**")
            for item in approvals:
                st.markdown(f"- {item}")

        open_questions = (
            parsed["open_questions"]
            or agent_state.get("open_questions", [])
        )
        if open_questions:
            st.markdown("**Open questions**")
            for item in open_questions:
                st.markdown(f"- {item}")
        elif parsed["missing"] or agent_state.get("blocking_missing_info"):
            blocking = parsed["missing"] or agent_state.get("blocking_missing_info", [])
            st.markdown("**Blocking information needed**")
            for item in blocking:
                st.markdown(f"- {item}")

        source_lines = parsed["sources"]
        if source_lines:
            st.markdown("**Citations**")
            for item in source_lines:
                st.markdown(f"- {item}")

        steps = parsed["steps"] or agent_state.get("next_steps", [])
        if steps:
            st.markdown("**Recommended next steps**")
            for index, step in enumerate(steps[:5], start=1):
                st.markdown(f"{index}. {step}")

        clarifying = (
            parsed["clarifying_question"]
            or agent_state.get("clarifying_question")
            or ""
        )
        if clarifying:
            st.markdown("**Clarifying question**")
            st.info(clarifying)

        disclaimer = parsed["disclaimer"] or (
            "Demo assistant using synthetic Acme Corp policies. "
            "Confirm real decisions with the relevant internal team."
        )
        st.caption(disclaimer)


def render_source_cards(chunks: list[dict], message_index: int) -> None:
    """Render compact retrieved policy source cards."""
    with st.expander("Retrieved policy sources", expanded=False):
        if not chunks:
            st.info("No policy sections were retrieved for this request.")
            return

        for index, chunk in enumerate(chunks):
            source = chunk.get("source", "unknown")
            section = chunk.get("section", "Unknown section")
            section_id = chunk.get("section_id")
            score = chunk.get("score")
            excerpt = clean_excerpt(chunk.get("text", ""), max_chars=250)
            score_text = (
                f"Score {score:.2f}" if score is not None else "Score n/a"
            )
            title = section_id or section
            st.markdown(f"**{title}** · {source} · {score_text}")
            st.caption(excerpt)
            with st.expander("View full retrieved text", expanded=False):
                st.write(chunk.get("text", ""))


def render_trace_timeline(trace: list[dict]) -> None:
    """Render the agent trace inside a collapsed expander."""
    with st.expander("Agent workflow trace", expanded=False):
        if not trace:
            st.info("No trace steps recorded.")
            return

        for step in trace:
            status = (step.get("status") or "started").lower()
            icon = TRACE_STATUS_ICON.get(status, "→")
            css_class = f"po-trace-{status}" if status in TRACE_STATUS_ICON else "po-trace-started"
            step_name = step.get("step_name", "unknown_step")
            message = step.get("message", "")
            st.markdown(
                f"""
                <div class="po-trace-step {css_class}">
                    <div class="po-trace-title">{icon} {step_name}
                        <span class="po-trace-status">{status}</span>
                    </div>
                    <div class="po-muted">{message}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            data = step.get("data") or {}
            if data:
                with st.expander(f"Step data: {step_name}", expanded=False):
                    st.json(data)


def render_developer_debug(agent_state: dict) -> None:
    """Show raw agent state for technical reviewers."""
    with st.expander("Developer Debug View", expanded=False):
        st.caption("Raw agent state JSON for architecture and debugging review.")
        st.json(agent_state)


def render_rag_extras(metadata: dict, message_index: int) -> None:
    """Show RAG sources and debug info for standard chat responses."""
    sources = metadata.get("sources", [])

    with st.expander("Sources used", expanded=False):
        if not sources:
            st.write("(none)")
        else:
            for index, source in enumerate(sources, start=1):
                st.markdown(
                    f"{index}. **{source['source_file']}** | "
                    f"page {source['page']} | "
                    f"chunk_id={source['chunk_id']}"
                )

    with st.expander("Debug info", expanded=False):
        st.markdown(
            f"- **Retrieved context count:** {metadata.get('retrieved_context_count', 0)}\n"
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


def render_citation_panels(agent_state: dict) -> None:
    """Render compact citation verification summary and cards."""
    coverage = float(agent_state.get("citation_coverage", 0.0) or 0.0)
    verified = agent_state.get("verified_citations", [])
    warnings = agent_state.get("citation_warnings", [])

    with st.expander("Citation verification", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Citation coverage", f"{coverage:.0%}")
        col2.metric("Verified citations", len(verified))
        col3.metric("Warnings", len(warnings))
        st.progress(min(max(coverage, 0.0), 1.0))

        if warnings:
            for warning in warnings:
                st.warning(warning)

        if not verified:
            st.info("No verified citations available.")
            return

        for index, citation in enumerate(verified):
            section_id = citation.get("section_id") or "—"
            section_title = citation.get("section_title") or citation.get("section", "Unknown")
            source = citation.get("source", "unknown")
            excerpt = citation.get("supporting_text_excerpt") or clean_excerpt(
                citation.get("text", ""), max_chars=220
            )
            st.markdown(
                f"""
                <div class="po-citation-card">
                    <strong>{section_id}</strong> · {section_title}<br>
                    <span class="po-muted">Source: {source}</span><br>
                    <span class="po-muted">Supports: policy threshold / approval requirement</span><br>
                    {excerpt}
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("View supporting text", expanded=False):
                st.write(citation.get("full_text") or excerpt)


def render_agent_extras(agent_state: dict, message_index: int) -> None:
    """Render agent decision, answer, citations, and collapsible diagnostics."""
    answer_text = agent_state.get("final_answer", "")

    render_decision_metrics(agent_state)
    render_final_answer_card(answer_text, agent_state)
    render_citation_panels(agent_state)
    render_source_cards(agent_state.get("retrieved_chunks", []), message_index)
    render_trace_timeline(agent_state.get("trace", []))
    render_developer_debug(agent_state)


def render_standard_thread_message(msg: dict, message_index: int) -> None:
    """Render one message in a standard RAG thread."""
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
        return

    metadata = msg.get("metadata", {})
    with st.chat_message("assistant"):
        st.markdown(msg["content"])
        render_rag_extras(metadata, message_index)


def render_agent_thread_message(msg: dict, message_index: int) -> None:
    """Render one message in a PolicyOps Agent thread."""
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
        return

    metadata = msg.get("metadata", {})
    agent_state = metadata.get("agent_state", {})

    if agent_state:
        with st.chat_message("assistant"):
            st.caption("PolicyOps Agent response")
        render_agent_extras(agent_state, message_index)
    else:
        with st.chat_message("assistant"):
            st.markdown(msg["content"])


def render_standard_thread(thread: dict) -> None:
    """Render all messages in a standard RAG thread."""
    if not thread["messages"]:
        render_empty_thread_examples(MODE_STANDARD)
        return

    for index, msg in enumerate(thread["messages"]):
        render_standard_thread_message(msg, index)


def render_agent_thread(thread: dict) -> None:
    """Render all messages in a PolicyOps Agent thread."""
    if not thread["messages"]:
        render_empty_thread_examples(MODE_AGENT)
        return

    for index, msg in enumerate(thread["messages"]):
        render_agent_thread_message(msg, index)


# ---------------------------------------------------------------------------
# Sidebar and info sections
# ---------------------------------------------------------------------------


def render_sidebar() -> str:
    """Render sidebar controls and return the active assistant mode key."""
    with st.sidebar:
        st.markdown("### PolicyOps Agent")
        st.caption("Enterprise AI policy assistant demo")

        mode_label = st.radio(
            "Assistant mode",
            MODE_OPTIONS,
            index=MODE_OPTIONS.index(MODE_KEY_TO_LABEL[st.session_state.assistant_mode]),
            help="Each mode keeps its own chat threads.",
        )
        mode = MODE_LABEL_TO_KEY[mode_label]
        st.session_state.assistant_mode = mode

        st.info(MODE_DESCRIPTIONS[mode])
        st.divider()

        st.markdown("#### Threads")
        if st.button("+ New thread", use_container_width=True):
            create_new_thread(mode)
            st.rerun()

        if st.button("Clear current thread", use_container_width=True):
            clear_active_thread(mode)
            st.rerun()

        active_id = st.session_state[_active_thread_key(mode)]
        for thread in list_threads(mode):
            thread_id = thread["thread_id"]
            label = thread.get("title", "New chat")
            button_type = "primary" if thread_id == active_id else "secondary"
            if st.button(
                label,
                key=f"thread_{mode}_{thread_id}",
                use_container_width=True,
                type=button_type,
            ):
                set_active_thread(mode, thread_id)
                st.rerun()

        st.divider()
        st.markdown("#### Knowledge base summary")
        st.markdown(f"- **{len(GOVERNANCE_DOCS)}** public AI governance docs")
        st.markdown(f"- **{len(ACME_POLICY_DOCS)}** Acme policy docs (synthetic)")

    return mode


def render_knowledge_base_section() -> None:
    """Show available documents grouped by corpus type."""
    st.subheader("Knowledge Base")
    st.write(
        "The app uses two document groups. Standard RAG Chat searches the public "
        "governance corpus. PolicyOps Agent searches the synthetic Acme workplace "
        "policy corpus (after mock policy ingestion)."
    )

    st.markdown("### Public AI governance documents")
    for name, description, corpus in GOVERNANCE_DOCS:
        st.markdown(f"- **{name}** — {description} (`{corpus}`)")

    st.markdown("### Acme Corp synthetic policy documents")
    st.caption("Fictional demo policies — not real company or legal advice.")
    for name, description, corpus in ACME_POLICY_DOCS:
        st.markdown(f"- **{name}** — {description} (`{corpus}`)")


def render_architecture_section() -> None:
    """Show system architecture for both modes."""
    st.subheader("Architecture")

    st.markdown("### Standard RAG Chat pipeline")
    st.code(RAG_PIPELINE, language=None)
    st.markdown(
        "- **Documents** — PDFs in `data/raw/`\n"
        "- **Chunks** — text segments with page metadata\n"
        "- **Embeddings** — OpenAI embedding vectors\n"
        "- **Vector database** — Chroma local store\n"
        "- **Retriever** — similarity search over chunks\n"
        "- **LLM answer** — grounded generation with citations"
    )

    st.markdown("### PolicyOps Agent pipeline")
    st.code(WORKFLOW_PIPELINE, language=None)
    st.markdown(
        "- **User scenario** — natural-language workplace question\n"
        "- **Intent** — rules-based request classification\n"
        "- **Scenario facts** — heuristic structured extraction\n"
        "- **Retrieval** — policy chunk search from Chroma\n"
        "- **Missing info** — policy-area checklist\n"
        "- **Decision engine** — deterministic rules in `agent/decision_rules.py`\n"
        "- **Citation verifier** — only cite retrieved sections\n"
        "- **Agent state** — shared workflow memory per run\n"
        "- **Tools** — parsing, retrieval, missing info, next steps\n"
        "- **Trace** — step-by-step workflow log (not chain-of-thought)"
    )


def render_faq_section() -> None:
    """Beginner-friendly FAQs for the dual-mode app."""
    st.subheader("FAQs")

    faqs = [
        (
            "What is the difference between Standard RAG Chat and PolicyOps Agent?",
            "Standard RAG Chat answers direct knowledge-base questions with retrieved "
            "sources. PolicyOps Agent handles workplace scenarios with structured "
            "decisions, risk, confidence, citations, and a workflow trace.",
        ),
        (
            "Why are there separate threads?",
            "Each mode keeps its own conversation history so switching modes does not "
            "mix RAG Q&A with agent scenario reviews.",
        ),
        (
            "What is a retrieved source?",
            "A document chunk returned by vector search. The app shows file, section, "
            "and similarity score so you can verify grounding.",
        ),
        (
            "What is an agent trace?",
            "A workflow log of agent steps (intent, retrieval, decision, etc.). It shows "
            "what ran — not private model reasoning.",
        ),
        (
            "What does confidence mean?",
            "A heuristic score based on rule strength, retrieval quality, missing "
            "information, and citation coverage. It is not a legal certainty score.",
        ),
        (
            "Are the policies real?",
            "The Acme Corp policies are synthetic demo documents. The NIST/OWASP "
            "documents are real public governance PDFs.",
        ),
        (
            "Can this be used for real HR/legal/compliance decisions?",
            "No. This is a portfolio demo prototype only.",
        ),
        (
            "What is planned for the next phase?",
            "Possible LangGraph migration, multi-turn memory, LLM-assisted parsing, "
            "and an agent evaluation dashboard.",
        ),
    ]

    for question, answer in faqs:
        with st.expander(question):
            st.write(answer)


# ---------------------------------------------------------------------------
# Query handling
# ---------------------------------------------------------------------------


def handle_user_query(query: str, mode: str) -> None:
    """Append user message, call the correct backend, and store the response."""
    append_message(mode, "user", query)

    setup_error = get_setup_error()
    if setup_error:
        if mode == MODE_AGENT:
            append_message(
                mode,
                "assistant",
                setup_error,
                metadata={"agent_state": {}},
            )
        else:
            append_message(
                mode,
                "assistant",
                setup_error,
                metadata={
                    "sources": [],
                    "retrieved_context_count": 0,
                    "answer_type": "standard_rag",
                },
            )
        st.rerun()

    try:
        if mode == MODE_AGENT:
            with st.spinner("Running PolicyOps Agent workflow..."):
                agent_state = run_policy_agent(query)
            append_message(
                mode,
                "assistant",
                agent_state["final_answer"],
                metadata={"agent_state": agent_state},
            )
        else:
            with st.spinner("Searching documents and generating answer..."):
                result = answer_question(query)
            append_message(
                mode,
                "assistant",
                result["answer"],
                metadata={
                    "sources": result.get("sources", []),
                    "retrieved_context_count": result.get("retrieved_context_count", 0),
                    "answer_type": "standard_rag",
                },
            )
    except SystemExit:
        error_text = (
            "Backend setup error. Check your API key and Chroma index, "
            "then restart the app."
        )
        if mode == MODE_AGENT:
            append_message(
                mode,
                "assistant",
                error_text,
                metadata={"agent_state": {}},
            )
        else:
            append_message(
                mode,
                "assistant",
                error_text,
                metadata={
                    "sources": [],
                    "retrieved_context_count": 0,
                    "answer_type": "standard_rag",
                },
            )
    except Exception as exc:
        error_text = (
            f"PolicyOps Agent failed for this request: {exc}"
            if mode == MODE_AGENT
            else f"Something went wrong while generating the answer: {exc}"
        )
        if mode == MODE_AGENT:
            append_message(
                mode,
                "assistant",
                error_text,
                metadata={"agent_state": {}},
            )
        else:
            append_message(
                mode,
                "assistant",
                error_text,
                metadata={
                    "sources": [],
                    "retrieved_context_count": 0,
                    "answer_type": "standard_rag",
                },
            )

    st.rerun()


def render_chat_tab(mode: str) -> None:
    """Render the active mode's chat thread and input."""
    render_mode_header(mode)
    thread = get_active_thread(mode)

    setup_error = get_setup_error()
    if setup_error:
        st.error(setup_error)
        if mode == MODE_AGENT:
            st.info("For Acme Corp policies, also run: python scripts/ingest_mock_policies.py")

    if mode == MODE_STANDARD:
        render_standard_thread(thread)
        placeholder = (
            "Ask a question about AI governance, LLM security, or the knowledge base..."
        )
    else:
        render_agent_thread(thread)
        placeholder = "Describe a workplace policy scenario for the agent to review..."

    question = st.chat_input(placeholder, key=f"chat_input_{mode}")

    pending = st.session_state.pending_question
    pending_mode = st.session_state.pending_mode or mode
    if pending and pending_mode == mode:
        st.session_state.pending_question = None
        st.session_state.pending_mode = None
        handle_user_query(pending, mode)
    elif question:
        handle_user_query(question, mode)


def main() -> None:
    """Run the Streamlit application."""
    st.set_page_config(
        page_title="PolicyOps Agent",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    inject_custom_css()
    mode = render_sidebar()

    tab_chat, tab_knowledge, tab_architecture, tab_faq = st.tabs(
        ["Chat", "Knowledge Base", "Architecture", "FAQs"]
    )

    with tab_chat:
        render_chat_tab(mode)

    with tab_knowledge:
        render_knowledge_base_section()

    with tab_architecture:
        render_architecture_section()

    with tab_faq:
        render_faq_section()


if __name__ == "__main__":
    main()
