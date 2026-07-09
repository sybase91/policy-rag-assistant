"""Conditional routing for the LangGraph PolicyOps workflow."""

from __future__ import annotations

from typing import Literal

from agent.state import GraphState


def route_after_missing_info(
    state: GraphState,
) -> Literal["explain", "decide", "clarify", "escalate"]:
    """Route based on answer type, risk flags, and blocking missing information."""
    answer_type = state.get("answer_type", "scenario_decision")
    if answer_type == "policy_explanation":
        return "explain"
    if answer_type == "insufficient_context":
        return "clarify"

    facts = state.get("merged_scenario_facts") or state.get("scenario_facts", {})

    if facts.get("public_official_involved") or facts.get("cash_gift"):
        return "escalate"
    if facts.get("cross_border_work"):
        return "escalate"
    if facts.get("sensitive_data_involved") and facts.get("external_vendor_involved"):
        return "escalate"

    if state.get("blocking_missing_info"):
        return "clarify"

    return "decide"
