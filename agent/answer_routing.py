"""Answer-type classification for PolicyOps Agent Phase 3.5."""

from __future__ import annotations

import re

POLICY_EXPLANATION_PATTERNS = (
    r"^what is the .+ policy",
    r"^what are the .+ policies",
    r"^what is the .+ reimbursement",
    r"^explain the .+ policy",
    r"^tell me about the .+ policy",
    r"approval matrix",
    r"explain the approval matrix",
)

SCENARIO_PATTERNS = (
    "can i ",
    "am i ",
    "should i ",
    "if i ",
    "may i ",
    "i already ",
    "i lost my",
    "i need to work",
    "i need to ",
)


def classify_answer_type(
    user_query: str,
    intent: str,
    scenario_facts: dict,
    *,
    is_follow_up: bool = False,
    had_open_questions: bool = False,
) -> str:
    """Classify how the final answer should be structured."""
    text = user_query.lower().strip()

    if is_follow_up or (had_open_questions and len(text.split()) <= 18):
        return "clarification_followup"

    for pattern in POLICY_EXPLANATION_PATTERNS:
        if re.search(pattern, text):
            if not any(marker in text for marker in SCENARIO_PATTERNS):
                return "policy_explanation"

    if intent == "policy_question" and not any(marker in text for marker in SCENARIO_PATTERNS):
        if "what is" in text or "what are" in text:
            return "policy_explanation"

    if scenario_facts.get("cash_gift") or scenario_facts.get("public_official_involved"):
        return "escalation_guidance"
    if scenario_facts.get("cross_border_work"):
        return "escalation_guidance"
    if scenario_facts.get("sensitive_data_involved") and scenario_facts.get("external_vendor_involved"):
        return "escalation_guidance"

    if len(text.split()) <= 8 and "policy" in text and "help" in text:
        return "insufficient_context"

    if text.strip() in {"can i do it?", "is this allowed under policy?"}:
        return "insufficient_context"

    return "scenario_decision"
