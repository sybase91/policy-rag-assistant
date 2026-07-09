"""Deterministic policy decision rules for PolicyOps Agent.

Decisions prioritize the most useful conservative outcome. Secondary missing
details become open questions rather than forcing "Needs more information".
"""

from __future__ import annotations

from agent.schemas import DECISION_VALUES, RISK_VALUES

BLOCKING_EVIDENCE = "relevant policy evidence"


def _top_score(chunks: list[dict]) -> float:
    if not chunks:
        return 0.0
    return max(float(chunk.get("score") or 0.0) for chunk in chunks)


def _base_confidence(
    chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> float:
    score = _top_score(chunks)
    confidence = 0.48 + (score * 0.32)
    confidence -= min(len(blocking_missing_info), 3) * 0.1
    confidence -= min(len(open_questions or []), 4) * 0.03
    if not chunks:
        confidence = 0.28
    elif score < 0.35:
        confidence = min(confidence, 0.5)
    return round(max(0.12, min(confidence, 0.9)), 2)


def _blocked(decision: str, blocking_missing_info: list[str], chunks: list[dict]) -> str:
    """Downgrade to Needs more information only when truly blocked."""
    if not blocking_missing_info:
        return decision
    if BLOCKING_EVIDENCE in blocking_missing_info or not chunks:
        return "Needs more information"
    essential_blockers = {
        "amount",
        "gift value",
        "type of data",
    }
    if any(item in blocking_missing_info for item in essential_blockers):
        return "Needs more information"
    return decision


def evaluate_reimbursement_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
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
        "Reimbursement must follow retrieved travel and expense policy thresholds."
    )

    if scenario_facts.get("external_parties_involved") or "client" in str(
        scenario_facts.get("expense_type", "")
    ).lower():
        rationale.append(
            "Client meals with external guests require documented business purpose and approval."
        )

    if currency == "INR" and isinstance(amount, (int, float)):
        if amount > 25000:
            approvals.append("Finance")
            rationale.append("Client meals above INR 25,000 require Finance approval.")
        elif amount > 10000:
            approvals.append("Manager")
            rationale.append("Client meals above INR 10,000 require manager approval.")

    if scenario_facts.get("payment_method") == "personal card":
        rationale.append(
            "Personal card reimbursement is permitted when policy rules and documentation are met."
        )

    if scenario_facts.get("alcohol_mentioned"):
        approvals.append("Finance")
        rationale.append("Alcohol requires explicit Finance approval.")

    if "lost receipt" in str(scenario_facts.get("documentation_provided", [])):
        decision = "Needs more information"
        rationale.append("Lost-receipt claims need alternate documentation before approval.")

    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "reimbursement", "amount": amount},
    }


def evaluate_gift_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> dict:
    """Apply gifts and hospitality rules."""
    amount = scenario_facts.get("gift_value") or scenario_facts.get("amount")
    decision = "Needs approval"
    risk_level = "Medium"
    rationale: list[str] = []
    approvals: list[str] = ["Manager"]

    if scenario_facts.get("cash_gift"):
        return {
            "decision": "Escalate",
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
        rationale.append("Gift value must be confirmed before a threshold decision.")
    elif isinstance(amount, (int, float)) and amount >= 10000:
        approvals.append("Compliance")
        rationale.append("Gifts above INR 10,000 require manager and Compliance approval.")

    if scenario_facts.get("vendor_or_client_involved"):
        rationale.append(
            "Vendor or client gifts create conflict-of-interest risk and need compliance review."
        )

    if not retrieved_chunks:
        decision = "Needs more information"
        rationale.append("No supporting gift policy sections were retrieved.")
    else:
        rationale.append("Retrieved gift policy sections support an approval-based response.")

    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4] or ["Gift requests must follow Acme hospitality policy."],
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "gifts_hospitality", "gift_value": amount},
    }


def evaluate_remote_work_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> dict:
    """Apply remote work rules."""
    decision = "Needs approval"
    risk_level = "Medium"
    rationale = ["Extended or exception-based remote work requires documented approval."]
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

    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "remote_work"},
    }


def evaluate_data_access_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> dict:
    """Apply data access and external sharing rules."""
    decision = "Needs approval"
    risk_level = "High"
    rationale = [
        "Sharing company data externally requires documented need-to-know and approval."
    ]
    approvals = ["Information Security"]

    if scenario_facts.get("external_vendor_involved"):
        approvals.extend(["Legal", "Compliance"])
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
        approvals = list(dict.fromkeys(approvals + ["Legal", "Compliance"]))

    if not retrieved_chunks:
        decision = "Needs more information"
    else:
        decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "decision_factors": {"policy_area": "data_access"},
    }


def evaluate_travel_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> dict:
    """Apply travel and hotel upgrade rules."""
    decision = "Needs approval"
    risk_level = "Medium"
    rationale = ["Travel-related requests must follow Acme Corp travel and expense policy."]
    approvals = ["Manager"]

    expense_type = str(scenario_facts.get("expense_type", "")).lower()
    if "upgrade" in expense_type or "hotel upgrade" in scenario_facts.get("raw_query", "").lower():
        rationale.append("Hotel upgrades are generally not reimbursable without prior approval.")

    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": approvals,
        "decision_factors": {"policy_area": "travel_expense"},
    }


def evaluate_general_policy_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
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
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": [
            "Retrieved policy sections appear relevant to the question asked."
        ],
        "required_approvals": [],
        "decision_factors": {"policy_area": scenario_facts.get("policy_area", "general")},
    }


def make_policy_decision(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
) -> dict:
    """Route to the correct policy evaluator and return a structured decision."""
    policy_area = scenario_facts.get("policy_area", "general")
    open_questions = open_questions or []

    if policy_area == "reimbursement":
        result = evaluate_reimbursement_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )
    elif policy_area == "gifts_hospitality":
        result = evaluate_gift_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )
    elif policy_area == "remote_work":
        result = evaluate_remote_work_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )
    elif policy_area == "data_access":
        result = evaluate_data_access_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )
    elif policy_area == "travel_expense":
        result = evaluate_travel_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )
    else:
        result = evaluate_general_policy_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions
        )

    if result["decision"] not in DECISION_VALUES:
        result["decision"] = "Needs more information"
    if result["risk_level"] not in RISK_VALUES:
        result["risk_level"] = "Medium"

    result["blocking_missing_info"] = blocking_missing_info
    result["open_questions"] = open_questions
    result["missing_info"] = blocking_missing_info + open_questions
    return result
