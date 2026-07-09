"""Deterministic policy decision rules for PolicyOps Agent Phase 2.

These rules combine scenario facts and retrieved evidence into a conservative
structured decision. They are not legal advice.
"""

from __future__ import annotations

from agent.schemas import DECISION_VALUES, RISK_VALUES

SECTION_ID_PATTERN = r"\b(TE|RE|GH|RW|AM|DA)-\d{3}\b"


def _top_score(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    return max(float(chunk.get("score") or 0.0) for chunk in chunks)


def _has_section(chunks: list[dict], prefix: str) -> bool:
    for chunk in chunks:
        section_id = (chunk.get("section_id") or "") or ""
        if section_id.startswith(prefix):
            return True
        section = chunk.get("section", "")
        if isinstance(section, str) and section.startswith(prefix):
            return True
    return False


def _base_confidence(chunks: list[dict], missing_info: list[str]) -> float:
    score = _top_score(chunks)
    confidence = 0.45 + (score * 0.35)
    confidence -= min(len(missing_info), 4) * 0.06
    if not chunks:
        confidence = 0.25
    elif score < 0.35:
        confidence = min(confidence, 0.45)
    return round(max(0.1, min(confidence, 0.92)), 2)


def evaluate_reimbursement_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Apply reimbursement and client meal rules."""
    amount = scenario_facts.get("amount") or scenario_facts.get("gift_value")
    currency = (scenario_facts.get("currency") or "INR").upper()
    decision = "Needs approval"
    risk_level = "Medium"
    rationale: list[str] = []
    approvals: list[str] = []

    if not retrieved_chunks:
        return {
            "decision": "Needs more information",
            "risk_level": "Medium",
            "confidence": 0.3,
            "rationale_bullets": ["No relevant policy sections were retrieved."],
            "required_approvals": [],
            "decision_factors": {"policy_area": "reimbursement"},
        }

    rationale.append(
        "Reimbursement requests must be supported by policy sections and complete documentation."
    )

    if scenario_facts.get("external_parties_involved") or "client" in str(
        scenario_facts.get("expense_type", "")
    ).lower():
        rationale.append(
            "Client meals require business purpose, attendee details, itemized receipt, and approval."
        )

    if currency == "INR" and isinstance(amount, (int, float)):
        if amount > 25000:
            decision = "Needs approval"
            approvals.append("Finance")
            rationale.append("Client meals above INR 25,000 require Finance approval.")
        elif amount > 10000:
            decision = "Needs approval"
            approvals.append("Manager")
            rationale.append("Client meals above INR 10,000 require manager approval.")

    if scenario_facts.get("payment_method") == "personal card":
        rationale.append(
            "Personal card usage is allowed when documentation is complete and policy rules are met."
        )

    if "itemized receipt" in missing_info or "lost receipt" in str(
        scenario_facts.get("documentation_provided", [])
    ):
        decision = "Needs more information"
        rationale.append("Receipt or lost-receipt documentation is required before approval.")

    if scenario_facts.get("alcohol_mentioned"):
        decision = "Needs approval"
        approvals.append("Finance")
        rationale.append("Alcohol generally requires explicit Finance approval.")

    if missing_info:
        decision = "Needs more information"

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": rationale,
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "reimbursement", "amount": amount},
    }


def evaluate_gift_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Apply gifts and hospitality rules."""
    amount = scenario_facts.get("gift_value") or scenario_facts.get("amount")
    decision = "Needs approval"
    risk_level = "Medium"
    rationale: list[str] = []
    approvals: list[str] = ["Manager"]

    if scenario_facts.get("cash_gift"):
        return {
            "decision": "Not allowed",
            "risk_level": "High",
            "confidence": 0.82,
            "rationale_bullets": ["Cash and cash-equivalent gifts are not acceptable."],
            "required_approvals": ["Compliance"],
            "decision_factors": {"policy_area": "gifts_hospitality", "cash_gift": True},
        }

    if scenario_facts.get("public_official_involved"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.8,
            "rationale_bullets": [
                "Gifts involving public officials require Legal review before acceptance."
            ],
            "required_approvals": ["Legal", "Compliance"],
            "decision_factors": {"policy_area": "gifts_hospitality", "public_official": True},
        }

    if amount is None:
        decision = "Needs more information"
        rationale.append("Gift value must be confirmed before a decision can be made.")
    elif isinstance(amount, (int, float)) and amount >= 10000:
        decision = "Needs approval"
        approvals.append("Compliance")
        rationale.append("Gifts above INR 10,000 require manager and Compliance approval.")

    if missing_info:
        decision = "Needs more information"

    if not retrieved_chunks:
        decision = "Needs more information"
        rationale.append("No supporting gift policy sections were retrieved.")

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": rationale or ["Gift requests must follow Acme Corp hospitality policy."],
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "gifts_hospitality", "gift_value": amount},
    }


def evaluate_remote_work_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Apply remote work rules."""
    decision = "Needs approval"
    risk_level = "Medium"
    rationale = [
        "Extended or exception-based remote work requires documented approval."
    ]
    approvals = ["Manager"]

    if scenario_facts.get("medical_reason"):
        approvals.append("HR")
        rationale.append("Medical-related remote work should be reviewed with HR.")

    if scenario_facts.get("cross_border_work"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.78,
            "rationale_bullets": [
                "Cross-border remote work requires HR and Legal approval in advance."
            ],
            "required_approvals": ["HR", "Legal"],
            "decision_factors": {"policy_area": "remote_work", "cross_border": True},
        }

    duration = scenario_facts.get("duration", "")
    if "week" in str(duration).lower():
        approvals.append("HR")
        rationale.append("Remote work beyond a short period requires formal approval.")

    if missing_info:
        decision = "Needs more information"

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": rationale,
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "remote_work"},
    }


def evaluate_data_access_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Apply data access and external sharing rules."""
    decision = "Needs approval"
    risk_level = "High"
    rationale = [
        "Sharing company data externally requires documented need-to-know and approval."
    ]
    approvals = ["Information Security"]

    if scenario_facts.get("external_vendor_involved"):
        approvals.extend(["Manager", "Legal"])
        rationale.append(
            "Customer or confidential data shared with an external vendor requires Security review."
        )

    data_types = scenario_facts.get("data_types", [])
    if any(item in data_types for item in ("customer data", "hr data", "finance data")):
        risk_level = "High"
        rationale.append("Sensitive data types increase governance and security risk.")

    if scenario_facts.get("sensitive_data_involved") and scenario_facts.get(
        "external_vendor_involved"
    ):
        decision = "Escalate"

    if missing_info:
        decision = "Needs more information"

    if not retrieved_chunks:
        decision = "Needs more information"

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": rationale,
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "data_access"},
    }


def evaluate_travel_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Apply travel and hotel upgrade rules."""
    decision = "Needs approval"
    risk_level = "Medium"
    rationale = ["Travel-related requests must follow Acme Corp travel and expense policy."]
    approvals = ["Manager"]

    expense_type = str(scenario_facts.get("expense_type", "")).lower()
    if "upgrade" in expense_type or "hotel upgrade" in scenario_facts.get("raw_query", "").lower():
        decision = "Needs approval"
        rationale.append("Hotel upgrades are generally not reimbursable without prior approval.")

    if missing_info:
        decision = "Needs more information"

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": rationale,
        "required_approvals": approvals,
        "decision_factors": {"policy_area": "travel_expense"},
    }


def evaluate_general_policy_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Fallback evaluator for broad policy questions."""
    if not retrieved_chunks:
        return {
            "decision": "Needs more information",
            "risk_level": "Medium",
            "confidence": 0.3,
            "rationale_bullets": ["No relevant policy evidence was retrieved."],
            "required_approvals": [],
            "decision_factors": {"policy_area": scenario_facts.get("policy_area", "general")},
        }

    return {
        "decision": "Allowed",
        "risk_level": "Low",
        "confidence": _base_confidence(retrieved_chunks, missing_info),
        "rationale_bullets": [
            "Retrieved policy sections appear relevant to the question asked."
        ],
        "required_approvals": [],
        "decision_factors": {"policy_area": scenario_facts.get("policy_area", "general")},
    }


def make_policy_decision(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Route to the correct policy evaluator and return a structured decision."""
    policy_area = scenario_facts.get("policy_area", "general")

    if policy_area == "reimbursement":
        result = evaluate_reimbursement_case(scenario_facts, retrieved_chunks, missing_info)
    elif policy_area == "gifts_hospitality":
        result = evaluate_gift_case(scenario_facts, retrieved_chunks, missing_info)
    elif policy_area == "remote_work":
        result = evaluate_remote_work_case(scenario_facts, retrieved_chunks, missing_info)
    elif policy_area == "data_access":
        result = evaluate_data_access_case(scenario_facts, retrieved_chunks, missing_info)
    elif policy_area == "travel_expense":
        result = evaluate_travel_case(scenario_facts, retrieved_chunks, missing_info)
    else:
        result = evaluate_general_policy_case(scenario_facts, retrieved_chunks, missing_info)

    if result["decision"] not in DECISION_VALUES:
        result["decision"] = "Needs more information"
    if result["risk_level"] not in RISK_VALUES:
        result["risk_level"] = "Medium"

    result["missing_info"] = missing_info
    return result
