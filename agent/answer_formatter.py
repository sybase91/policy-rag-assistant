"""Final answer formatting for PolicyOps Agent."""

from __future__ import annotations

from agent.state import AgentState

ANSWER_STYLE = "concise"

DISCLAIMER = (
    "Demo assistant using synthetic Acme Corp policies. "
    "Confirm real decisions with the relevant internal team."
)

_SHORT_ANSWER = {
    "Allowed": (
        "Based on the facts provided, this request appears permitted under the "
        "retrieved policy sections, subject to standard documentation requirements."
    ),
    "Needs approval": (
        "You can likely proceed only after the required approvals are in place. "
        "The policy evidence suggests approval is required, not an automatic rejection."
    ),
    "Not allowed": (
        "The retrieved policy sections indicate this request should not proceed "
        "without an explicit exception from the appropriate governance team."
    ),
    "Escalate": (
        "This scenario has elevated risk. Escalate to the appropriate governance "
        "team before taking any action."
    ),
    "Needs more information": (
        "A provisional decision cannot be made yet because essential facts or "
        "policy evidence are still missing."
    ),
}


def _format_citation_line(citation: dict) -> str:
    section_id = citation.get("section_id")
    section_title = citation.get("section_title") or citation.get("section", "")
    if section_id:
        if section_title and section_id not in str(section_title):
            return f"- {section_id} {section_title}".strip()
        return f"- {section_id}"
    source = citation.get("source", "unknown")
    return f"- {source}, {section_title}"


def format_final_answer(state: AgentState, style: str | None = None) -> str:
    """Build a concise, modular business-friendly final answer."""
    style = style or ANSWER_STYLE
    lines: list[str] = []

    decision = state.get("policy_decision") or "Unknown"
    risk_level = state.get("risk_level") or "Unknown"
    confidence = float(state.get("confidence") or 0.0)

    lines.extend(
        [
            f"Decision: {decision}",
            "",
            f"Risk level: {risk_level}",
            f"Confidence: {confidence:.0%}",
            "",
            "Short answer:",
            _SHORT_ANSWER.get(decision, _SHORT_ANSWER["Needs more information"]),
        ]
    )

    rationale = state.get("rationale_bullets", [])[:3]
    if rationale:
        lines.extend(["", "Why this decision:"])
        for item in rationale:
            lines.append(f"- {item}")

    approvals = state.get("required_approvals", [])
    if approvals:
        lines.extend(["", "Required approvals:"])
        for item in approvals:
            lines.append(f"- {item}")

    open_questions = state.get("open_questions", [])
    blocking = state.get("blocking_missing_info", [])
    if open_questions:
        lines.extend(["", "Open questions:"])
        for item in open_questions:
            lines.append(f"- {item}")
    elif blocking:
        lines.extend(["", "Blocking information needed:"])
        for item in blocking:
            lines.append(f"- {item}")

    steps = state.get("next_steps", [])[:5]
    if steps:
        lines.extend(["", "Recommended next steps:"])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")

    citations = state.get("verified_citations") or state.get("citations", [])
    if citations:
        lines.extend(["", "Citations:"])
        for citation in citations[:5]:
            lines.append(_format_citation_line(citation))

    clarifying = state.get("clarifying_question")
    if clarifying and open_questions:
        lines.extend(["", "Clarifying question:", clarifying])

    if style == "detailed":
        warnings = state.get("citation_warnings", [])
        if warnings:
            lines.extend(["", "Citation warnings:"])
            for warning in warnings:
                lines.append(f"- {warning}")

    lines.extend(["", "Disclaimer:", DISCLAIMER])
    return "\n".join(lines)
