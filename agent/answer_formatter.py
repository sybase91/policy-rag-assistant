"""Final answer formatting for PolicyOps Agent Phase 3.5."""

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


def _format_policy_basis_lines(policy_basis: list[dict]) -> list[str]:
    lines: list[str] = []
    for rule in policy_basis[:6]:
        section_id = rule.get("section_id") or "Policy"
        summary = rule.get("rule_summary") or rule.get("raw_excerpt", "")
        title = rule.get("section_title", "")
        if title and title not in summary:
            lines.append(f"- {section_id} ({title}): {summary}")
        else:
            lines.append(f"- {section_id}: {summary}")
    return lines


def _append_citations_and_disclaimer(
    lines: list[str],
    state: AgentState,
    *,
    style: str,
    include_clarifying: bool = True,
) -> str:
    citations = state.get("verified_citations") or state.get("citations", [])
    if citations:
        lines.extend(["", "Citations:"])
        for citation in citations[:5]:
            lines.append(_format_citation_line(citation))

    if include_clarifying:
        clarifying = state.get("clarifying_question")
        open_questions = state.get("open_questions", [])
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


def format_policy_explanation_answer(state: AgentState, style: str | None = None) -> str:
    """Format an informational policy explanation answer."""
    style = style or ANSWER_STYLE
    title = state.get("explanation_title") or "Policy overview"
    confidence = float(state.get("confidence") or 0.0)
    policy_basis = state.get("policy_basis") or state.get("extracted_policy_rules", [])
    retrieved = state.get("retrieved_chunks") or []

    lines = [
        f"Topic: {title}",
        "",
        f"Confidence: {confidence:.0%}",
        "",
        "Summary:",
    ]

    if not retrieved and not policy_basis:
        lines.append(
            "- No relevant policy sections were found in the Acme Corp corpus for this topic. "
            "Do not assume a policy exists without verified documentation."
        )

    rationale = state.get("rationale_bullets", [])[:4]
    if rationale:
        for item in rationale:
            lines.append(f"- {item}")
    else:
        lines.append("- The retrieved Acme Corp policy sections describe the rules below.")

    basis_lines = _format_policy_basis_lines(policy_basis)
    if basis_lines:
        lines.extend(["", "Policy basis:"])
        lines.extend(basis_lines)

    facts = state.get("merged_scenario_facts") or state.get("scenario_facts", {})
    policy_area = facts.get("policy_area", "general")
    if policy_area and policy_area != "general":
        lines.extend(["", "How this applies to your question:", f"- Policy area: {policy_area.replace('_', ' ')}"])

    steps = state.get("next_steps", [])[:4]
    if steps:
        lines.extend(["", "Recommended next steps:"])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")

    return _append_citations_and_disclaimer(lines, state, style=style, include_clarifying=False)


def format_scenario_decision_answer(state: AgentState, style: str | None = None) -> str:
    """Format a scenario-based decision answer."""
    style = style or ANSWER_STYLE
    decision = state.get("policy_decision") or "Unknown"
    risk_level = state.get("risk_level") or "Unknown"
    confidence = float(state.get("confidence") or 0.0)

    lines = [
        f"Decision: {decision}",
        "",
        f"Risk level: {risk_level}",
        f"Confidence: {confidence:.0%}",
        "",
        "Short answer:",
        _SHORT_ANSWER.get(decision, _SHORT_ANSWER["Needs more information"]),
    ]

    rationale = state.get("rationale_bullets", [])[:4]
    if rationale:
        lines.extend(["", "Why this decision:"])
        for item in rationale:
            lines.append(f"- {item}")

    policy_basis = state.get("policy_basis", [])
    basis_lines = _format_policy_basis_lines(policy_basis)
    if basis_lines:
        lines.extend(["", "Policy basis:"])
        lines.extend(basis_lines)

    facts = state.get("merged_scenario_facts") or state.get("scenario_facts", {})
    apply_lines: list[str] = []
    if facts.get("amount") or facts.get("gift_value"):
        value = facts.get("gift_value") or facts.get("amount")
        currency = facts.get("currency", "INR")
        apply_lines.append(f"- Amount in scope: {currency} {value:,.0f}")
    if facts.get("duration"):
        apply_lines.append(f"- Duration: {facts['duration']}")
    if facts.get("approval_status") == "approved":
        apply_lines.append("- Manager approval is already documented.")
    if apply_lines:
        lines.extend(["", "How this applies to your case:"])
        lines.extend(apply_lines)

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

    return _append_citations_and_disclaimer(lines, state, style=style)


def format_escalation_guidance_answer(state: AgentState, style: str | None = None) -> str:
    """Format a high-risk escalation guidance answer."""
    style = style or ANSWER_STYLE
    decision = state.get("policy_decision") or "Escalate"
    risk_level = state.get("risk_level") or "High"
    confidence = float(state.get("confidence") or 0.0)

    lines = [
        f"Decision: {decision}",
        "",
        f"Risk level: {risk_level}",
        f"Confidence: {confidence:.0%}",
        "",
        "Short answer:",
        _SHORT_ANSWER.get("Escalate", _SHORT_ANSWER["Needs more information"]),
        "",
        "Why escalation is required:",
    ]
    for item in state.get("rationale_bullets", [])[:4]:
        lines.append(f"- {item}")

    basis_lines = _format_policy_basis_lines(state.get("policy_basis", []))
    if basis_lines:
        lines.extend(["", "Policy basis:"])
        lines.extend(basis_lines)

    approvals = state.get("required_approvals", [])
    if approvals:
        lines.extend(["", "Required approvals:"])
        for item in approvals:
            lines.append(f"- {item}")

    steps = state.get("next_steps", [])[:5]
    if steps:
        lines.extend(["", "Recommended next steps:"])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")

    return _append_citations_and_disclaimer(lines, state, style=style)


def format_clarification_followup_answer(state: AgentState, style: str | None = None) -> str:
    """Format a follow-up answer that builds on prior context."""
    return format_scenario_decision_answer(state, style=style)


def format_final_answer(state: AgentState, style: str | None = None) -> str:
    """Dispatch to the correct formatter based on answer_type."""
    answer_type = state.get("answer_type", "scenario_decision")
    formatters = {
        "policy_explanation": format_policy_explanation_answer,
        "scenario_decision": format_scenario_decision_answer,
        "clarification_followup": format_clarification_followup_answer,
        "escalation_guidance": format_escalation_guidance_answer,
        "insufficient_context": format_scenario_decision_answer,
    }
    formatter = formatters.get(answer_type, format_scenario_decision_answer)
    return formatter(state, style=style)
