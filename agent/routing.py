"""Conditional routing for the LangGraph PolicyOps workflow."""

from __future__ import annotations

from typing import Literal

from agent.state import GraphState


from agent.tools import _amount_not_required_for_decision


def can_decide_without_amount(facts: dict) -> bool:
    """Return True when reimbursement/travel rules do not need an amount."""
    return _amount_not_required_for_decision(facts)


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
    if facts.get("vendor_contract_renewal") or facts.get("active_rfp"):
        return "escalate"
    if facts.get("data_already_shared"):
        return "escalate"
    if "hr data" in facts.get("data_types", []) and facts.get("external_vendor_involved"):
        return "escalate"
    if facts.get("public_ai_tool") and (
        facts.get("sensitive_data_involved")
        or "customer data" in facts.get("data_types", [])
    ):
        return "escalate"
    if facts.get("personal_channel") and facts.get("sensitive_data_involved"):
        return "escalate"
    if facts.get("sensitive_data_involved") and facts.get("external_vendor_involved"):
        return "escalate"

    blocking = state.get("blocking_missing_info") or []
    essential_blockers = {"amount", "gift value", "type of data"}
    if blocking and any(item in essential_blockers for item in blocking):
        if "amount" in blocking and can_decide_without_amount(facts):
            blocking = [item for item in blocking if item != "amount"]
        elif blocking == ["amount"] and facts.get("policy_area") in {
            "reimbursement",
            "travel_expense",
        } and can_decide_without_amount(facts):
            blocking = []
        if not blocking:
            return "decide"
        if not any(item in essential_blockers for item in blocking):
            return "decide"
        return "clarify"
    if blocking and blocking != ["relevant policy evidence"]:
        if facts.get("policy_area") and blocking == ["relevant policy evidence"]:
            return "decide"
        return "clarify"

    return "decide"
