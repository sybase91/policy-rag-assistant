"""Streamlit UI for PolicyOps Agent and the NIST Policy RAG Assistant.

When Agent Mode is OFF, the app preserves the original RAG chat behavior.
When Agent Mode is ON, queries run through the PolicyOps Agent workflow.
"""

from __future__ import annotations

import os
import re
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

AGENT_WELCOME_SAMPLES = AGENT_EXAMPLE_QUESTIONS[:3]

WORKFLOW_PIPELINE = (
    "User Query -> Intent -> Scenario Facts -> Retrieval -> "
    "Missing Info -> Decision -> Citation Verify -> Clarifying Q -> "
    "Next Steps -> Final Answer"
)

TRACE_STATUS_ICON = {
    "completed": "✓",
    "started": "→",
    "failed": "✕",
}


def init_session_state() -> None:
    """Create session state defaults on first load."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_mode" not in st.session_state:
        st.session_state.agent_mode = False
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None


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
        .po-card h3, .po-card h4 {
            margin-top: 0;
            margin-bottom: 0.55rem;
            color: #0f172a;
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
        .po-risk-low { border-left: 4px solid #16a34a; }
        .po-risk-medium { border-left: 4px solid #d97706; }
        .po-risk-high { border-left: 4px solid #dc2626; }
        .po-risk-unknown { border-left: 4px solid #94a3b8; }
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
        return (
            "No Chroma index found. Run python -m src.embed --rebuild first."
        )

    return None


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


def parse_agent_answer(text: str) -> dict:
    """Parse the deterministic final answer into display sections."""
    parsed = {
        "decision": "",
        "risk_level": "",
        "confidence": None,
        "summary": "",
        "rationale": [],
        "missing": [],
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
                parsed["confidence"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                parsed["confidence"] = None
            current = None
            continue
        if line == "Summary:":
            current = "summary"
            continue
        if line == "Why this decision:":
            current = "rationale"
            continue
        if line == "Missing information:":
            current = "missing"
            continue
        if line in {"Relevant policy sources:", "Relevant policy citations:"}:
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

        if current == "summary":
            parsed["summary"] += (line + " ")
        elif current == "rationale" and line.startswith("- "):
            parsed["rationale"].append(line[2:].strip())
        elif current == "missing" and line.startswith("- "):
            parsed["missing"].append(line[2:].strip())
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

    parsed["summary"] = parsed["summary"].strip()
    parsed["clarifying_question"] = parsed["clarifying_question"].strip()
    parsed["disclaimer"] = parsed["disclaimer"].strip()
    return parsed


def render_product_header(agent_mode: bool) -> None:
    """Render the enterprise product header."""
    if agent_mode:
        st.markdown(
            """
            <div class="po-header">
                <span class="po-badge">Phase 2 — Grounded Decision Engine</span>
                <h1>PolicyOps Agent</h1>
                <p>Agentic RAG assistant for workplace policy decisions</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="po-pipeline">{WORKFLOW_PIPELINE}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Ask Acme Corp policy questions, review the grounded decision, inspect "
            "retrieved policy sections, and follow the agent workflow trace."
        )
    else:
        st.title("Enterprise AI Policy RAG Assistant")
        st.markdown(
            "Ask questions about **public AI governance and LLM security documents**. "
            "Answers are grounded in NIST and OWASP policy PDFs with source citations."
        )


def render_agent_welcome() -> None:
    """Show a welcome card before the first agent conversation."""
    st.markdown(
        """
        <div class="po-welcome">
            <h3 style="margin-top:0;">Welcome to PolicyOps Agent</h3>
            <p class="po-muted" style="margin-bottom:0.5rem;">
                This demo helps you evaluate workplace policy scenarios using a traceable
                agent workflow over synthetic Acme Corp policy documents.
            </p>
            <p class="po-muted" style="margin-bottom:0;">
                <strong>Note:</strong> Acme Corp policies are fictional demo documents and
                are not legal, HR, finance, or compliance advice.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**Try one of these sample questions:**")
    cols = st.columns(3)
    for index, sample in enumerate(AGENT_WELCOME_SAMPLES):
        with cols[index]:
            if st.button("Use sample", key=f"welcome_sample_{index}", use_container_width=True):
                st.session_state.pending_question = sample
                st.rerun()
            st.caption(sample)


def render_sidebar() -> bool:
    """Render sidebar controls and return whether Agent Mode is enabled."""
    with st.sidebar:
        st.markdown("### Control Panel")
        agent_mode = st.toggle(
            "Agent Mode",
            value=st.session_state.agent_mode,
            help="Run the PolicyOps Agent workflow for Acme Corp policy scenarios.",
        )
        st.session_state.agent_mode = agent_mode
        st.divider()

        if agent_mode:
            st.markdown("#### Policy corpus")
            for policy in [
                "Travel and Expense",
                "Reimbursement",
                "Gifts and Hospitality",
                "Remote Work",
                "Approval Matrix",
                "Data Access",
            ]:
                st.markdown(f"- Acme Corp {policy} Policy")

            st.markdown("#### Project phase")
            st.info("Phase 2 — Grounded Decision Engine")

            st.markdown("#### Workflow")
            st.code(WORKFLOW_PIPELINE, language=None)

            st.markdown("#### Example questions")
            for index, example in enumerate(AGENT_EXAMPLE_QUESTIONS):
                label = example if len(example) <= 58 else example[:55] + "..."
                if st.button(label, key=f"agent_example_{index}", use_container_width=True):
                    st.session_state.pending_question = example
                    st.rerun()
        else:
            st.markdown("#### Knowledge base")
            st.markdown(
                "- NIST AI Risk Management Framework 1.0\n"
                "- NIST AI 600-1 Generative AI Profile\n"
                "- OWASP Top 10 for LLM Applications 2025\n"
                "- NIST Cybersecurity Framework 2.0"
            )
            st.markdown("#### Architecture")
            st.code(
                "PDFs -> Chunks -> Embeddings -> Chroma -> Retrieval -> Answer",
                language=None,
            )
            st.markdown("#### Example questions")
            for index, example in enumerate(RAG_EXAMPLE_QUESTIONS):
                if st.button(example, key=f"rag_example_{index}", use_container_width=True):
                    st.session_state.pending_question = example
                    st.rerun()

        st.divider()
        if st.button("Clear chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.rerun()

    return agent_mode


def render_decision_metrics(agent_state: dict) -> None:
    """Render prominent decision metrics with risk styling and confidence bar."""
    decision = agent_state.get("policy_decision", "Unknown")
    intent = agent_state.get("intent", "unknown")
    risk_level = agent_state.get("risk_level", "Unknown")
    confidence = float(agent_state.get("confidence", 0.0) or 0.0)
    risk_class = risk_css_class(risk_level)

    st.markdown(
        f"""
        <div class="po-decision-hero">
            <div class="label">Decision</div>
            <div class="value">{decision}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
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


def render_final_answer_card(answer_text: str, agent_state: dict) -> None:
    """Render the final answer in a scannable card layout."""
    parsed = parse_agent_answer(answer_text)
    decision = parsed["decision"] or agent_state.get("policy_decision", "Unknown")
    risk_level = parsed["risk_level"] or agent_state.get("risk_level", "Unknown")
    confidence = parsed["confidence"]
    if confidence is None:
        confidence = float(agent_state.get("confidence", 0.0) or 0.0)

    with st.container(border=True):
        st.markdown("### Final Answer")
        top1, top2, top3 = st.columns(3)
        with top1:
            st.markdown(f"**Decision:** {decision}")
        with top2:
            st.markdown(f"**Risk level:** {risk_level}")
        with top3:
            st.markdown(f"**Confidence:** {confidence:.0%}")

        st.markdown("**Summary**")
        if parsed["summary"]:
            st.write(parsed["summary"])
        else:
            st.write(answer_text)

        rationale = parsed["rationale"] or agent_state.get("rationale_bullets", [])
        if rationale:
            st.markdown("**Why this decision**")
            for item in rationale:
                st.markdown(f"- {item}")

        missing = parsed["missing"] or agent_state.get("missing_info", [])
        if missing:
            st.markdown("**Missing information**")
            for item in missing:
                st.markdown(f"- {item}")

        approvals = parsed["approvals"] or agent_state.get("required_approvals", [])
        if approvals:
            st.markdown("**Required approvals**")
            for item in approvals:
                st.markdown(f"- {item}")

        source_lines = parsed["sources"]
        verified = agent_state.get("verified_citations") or []
        if not source_lines and verified:
            source_lines = [
                (
                    f"{citation.get('source')}, {citation.get('section_id')}, "
                    f"{citation.get('section')}"
                    if citation.get("section_id")
                    else f"{citation.get('source')}, {citation.get('section')}"
                )
                for citation in verified
            ]
        elif not source_lines and agent_state.get("citations"):
            source_lines = [
                (
                    f"{citation.get('source')}, {citation.get('section_id')}, "
                    f"{citation.get('section')}"
                    if citation.get("section_id")
                    else f"{citation.get('source')}, {citation.get('section')}"
                )
                for citation in agent_state["citations"]
            ]
        if source_lines:
            st.markdown("**Relevant policy citations**")
            for item in source_lines:
                st.markdown(f"- {item}")

        steps = parsed["steps"] or agent_state.get("next_steps", [])
        if steps:
            st.markdown("**Recommended next steps**")
            for index, step in enumerate(steps, start=1):
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
            "This is a demo assistant using synthetic Acme Corp policies. "
            "For real decisions, confirm with the relevant internal team."
        )
        st.markdown("**Disclaimer**")
        st.caption(disclaimer)


def render_source_cards(chunks: list[dict], message_index: int) -> None:
    """Render retrieved policy chunks as source cards."""
    st.markdown("#### Retrieved policy sources")
    if not chunks:
        st.info("No policy sections were retrieved for this request.")
        return

    for index, chunk in enumerate(chunks, start=1):
        source = chunk.get("source", "unknown")
        section = chunk.get("section", "Unknown section")
        section_id = chunk.get("section_id")
        score = chunk.get("score")
        excerpt = (chunk.get("text") or "").strip().replace("\n", " ")
        if len(excerpt) > 220:
            excerpt = excerpt[:220] + "..."

        score_text = f"Similarity score: {score:.2f}" if score is not None else "Similarity score: n/a"
        section_label = f"{section_id} · {section}" if section_id else section
        st.markdown(
            f"""
            <div class="po-source-card">
                <div class="po-source-title">{source}</div>
                <div class="po-source-meta">{section_label} · {score_text}</div>
                <div class="po-source-excerpt">{excerpt}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("View full retrieved text", expanded=False):
            st.write(chunk.get("text", ""))


def render_trace_timeline(trace: list[dict]) -> None:
    """Render the agent trace as a workflow timeline."""
    st.markdown("#### Agent workflow trace")
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


def render_rag_extras(result: dict, message_index: int) -> None:
    """Show RAG sources, debug info, and feedback placeholders."""
    sources = result.get("sources", [])

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


def render_citation_panels(agent_state: dict) -> None:
    """Render citation coverage, warnings, and verified citations."""
    coverage = float(agent_state.get("citation_coverage", 0.0) or 0.0)
    st.markdown("#### Citation verification")
    st.metric("Citation coverage", f"{coverage:.0%}")
    st.progress(min(max(coverage, 0.0), 1.0))

    warnings = agent_state.get("citation_warnings", [])
    if warnings:
        st.markdown("**Citation warnings**")
        for warning in warnings:
            st.warning(warning)

    verified = agent_state.get("verified_citations", [])
    if verified:
        st.markdown("**Verified citations**")
        for citation in verified:
            section_id = citation.get("section_id")
            title = citation.get("section", "Unknown section")
            source = citation.get("source", "unknown")
            if section_id:
                st.markdown(f"- **{section_id}** — {source}, {title}")
            else:
                st.markdown(f"- {source}, {title}")
            excerpt = citation.get("supporting_text_excerpt")
            if excerpt:
                st.caption(excerpt)


def render_agent_extras(agent_state: dict, message_index: int) -> None:
    """Render polished agent decision, answer, sources, trace, and debug panels."""
    answer_text = agent_state.get("final_answer", "")

    left_col, right_col = st.columns([1.35, 1], gap="large")

    with left_col:
        render_decision_metrics(agent_state)
        render_final_answer_card(answer_text, agent_state)
        render_citation_panels(agent_state)
        render_source_cards(agent_state.get("retrieved_chunks", []), message_index)

    with right_col:
        render_trace_timeline(agent_state.get("trace", []))
        render_developer_debug(agent_state)


def render_message(msg: dict, message_index: int) -> None:
    """Render one stored chat message."""
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
        return

    if msg.get("mode") == "agent" and msg.get("agent_state"):
        with st.chat_message("assistant"):
            st.caption("PolicyOps Agent response")
        render_agent_extras(msg["agent_state"], message_index)
        return

    with st.chat_message("assistant"):
        st.markdown(msg["content"])
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

    try:
        with st.spinner("Searching documents and generating answer..."):
            result = answer_question(question)

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
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Backend setup error. Check your API key and Chroma index, "
                    "then restart the app."
                ),
                "mode": "rag",
                "sources": [],
                "retrieved_context_count": 0,
            }
        )
    except Exception as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Something went wrong while generating the answer: {exc}",
                "mode": "rag",
                "sources": [],
                "retrieved_context_count": 0,
            }
        )

    st.rerun()


def handle_new_agent_question(question: str) -> None:
    """Process a question with the PolicyOps Agent workflow."""
    st.session_state.messages.append({"role": "user", "content": question, "mode": "agent"})

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

    try:
        with st.spinner("Running PolicyOps Agent workflow..."):
            agent_state = run_policy_agent(question)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": agent_state["final_answer"],
                "mode": "agent",
                "agent_state": agent_state,
            }
        )
    except SystemExit:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": (
                    "Backend setup error. Check your API key and Chroma index, "
                    "then restart the app."
                ),
                "mode": "agent",
                "agent_state": {},
            }
        )
    except Exception as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"PolicyOps Agent failed for this request: {exc}",
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
        initial_sidebar_state="expanded",
    )

    init_session_state()
    inject_custom_css()
    agent_mode = render_sidebar()
    render_product_header(agent_mode)

    setup_error = get_setup_error()
    if setup_error:
        st.error(setup_error)
        if agent_mode:
            st.info(
                "For Acme Corp policies, also run: python scripts/ingest_mock_policies.py"
            )

    if agent_mode and not st.session_state.messages:
        render_agent_welcome()

    for index, msg in enumerate(st.session_state.messages):
        render_message(msg, index)

    chat_placeholder = (
        "Ask an Acme Corp policy scenario..."
        if agent_mode
        else "Ask a question about AI governance or LLM security..."
    )
    question = st.chat_input(chat_placeholder)

    pending = st.session_state.pending_question
    if pending:
        st.session_state.pending_question = None
        if agent_mode:
            handle_new_agent_question(pending)
        else:
            handle_new_rag_question(pending)
    elif question:
        if agent_mode:
            handle_new_agent_question(question)
        else:
            handle_new_rag_question(question)


if __name__ == "__main__":
    main()
