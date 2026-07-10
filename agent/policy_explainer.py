"""Policy explanation builder for informational queries."""

from __future__ import annotations

from agent.policy_rule_extractor import build_rationale_from_rules, extract_policy_rules, summarize_rules_for_explanation


def build_policy_explanation(
    scenario_facts: dict,
    extracted_rules: list[dict],
    retrieved_chunks: list[dict],
) -> dict:
    """Build state fields for policy_explanation answer type."""
    policy_area = scenario_facts.get("policy_area", "general")
    rules = summarize_rules_for_explanation(extracted_rules, policy_area)
    if not rules and retrieved_chunks:
        rules = summarize_rules_for_explanation(
            extract_policy_rules(retrieved_chunks),
            policy_area,
        )
    rationale = build_rationale_from_rules(rules)

    area_titles = {
        "remote_work": "Work from home / remote work",
        "gifts_hospitality": "Gifts and hospitality",
        "reimbursement": "Reimbursement",
        "data_access": "Data access",
        "travel_expense": "Travel and expense",
        "general": "Workplace policy",
    }
    title = area_titles.get(policy_area, "Workplace policy")

    confidence = 0.55
    if retrieved_chunks:
        confidence = min(0.85, 0.5 + len(rules) * 0.05)
    else:
        rationale = rationale or [
            "No relevant policy sections were retrieved for this topic. "
            "Confirm whether a policy exists before relying on this summary."
        ]

    return {
        "policy_decision": "",
        "risk_level": "Low" if retrieved_chunks else "Medium",
        "confidence": round(confidence, 2),
        "rationale_bullets": rationale,
        "required_approvals": [],
        "policy_basis": rules,
        "decision_factors": {"policy_area": policy_area, "answer_type": "policy_explanation"},
        "explanation_title": title,
    }
