"""Final answer formatting for PolicyOps Agent Phase 2."""

from __future__ import annotations

from agent.state import AgentState

DISCLAIMER = (
    "This is a demo assistant using synthetic Acme Corp policies. "
    "For real decisions, confirm with the relevant internal team."
)


def format_final_answer(state: AgentState) -> str:
    """Build a structured business-friendly final answer."""
    lines: list[str] = []

    decision = state.get("policy_decision") or "Unknown"
    risk_level = state.get("risk_level") or "Unknown"
    confidence = float(state.get("confidence") or 0.0)

    lines.extend(
        [
            f"Decision: {decision}",
            "",
            f"Risk level: {risk_level}",
            "",
            f"Confidence: {confidence:.2f}",
            "",
            "Summary:",
        ]
    )

    if state.get("missing_info"):
        lines.append(
            "Based on the information provided, relevant policy sections were retrieved, "
            "but additional details are needed before a fully confident decision can be made."
        )
    else:
        lines.append(
            "Based on the retrieved Acme Corp policy sections and the scenario facts provided, "
            "this request should be handled using the policy rules below."
        )

    rationale = state.get("rationale_bullets", [])
    if rationale:
        lines.extend(["", "Why this decision:"])
        for item in rationale:
            lines.append(f"- {item}")

    missing = state.get("missing_info", [])
    if missing:
        lines.extend(["", "Missing information:"])
        for item in missing:
            lines.append(f"- {item}")

    approvals = state.get("required_approvals", [])
    if approvals:
        lines.extend(["", "Required approvals:"])
        for item in approvals:
            lines.append(f"- {item}")

    citations = state.get("verified_citations") or state.get("citations", [])
    if citations:
        lines.extend(["", "Relevant policy citations:"])
        for citation in citations:
            source = citation.get("source", "unknown")
            section_id = citation.get("section_id")
            section = citation.get("section", "Unknown section")
            if section_id:
                lines.append(f"- {source}, {section_id}, {section}")
            else:
                lines.append(f"- {source}, {section}")

    steps = state.get("next_steps", [])
    if steps:
        lines.extend(["", "Recommended next steps:"])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")

    clarifying = state.get("clarifying_question")
    if clarifying:
        lines.extend(["", "Clarifying question:", clarifying])

    warnings = state.get("citation_warnings", [])
    if warnings:
        lines.extend(["", "Citation warnings:"])
        for warning in warnings:
            lines.append(f"- {warning}")

    lines.extend(["", "Disclaimer:", DISCLAIMER])
    return "\n".join(lines)
