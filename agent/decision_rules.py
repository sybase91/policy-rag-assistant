"""Deterministic policy decision rules for PolicyOps Agent."""

from __future__ import annotations

from agent.policy_rule_extractor import build_rationale_from_rules, select_rules_for_scenario
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
    if not blocking_missing_info:
        return decision
    if not chunks:
        return "Needs more information"
    essential_blockers = {"amount", "gift value", "type of data"}
    if any(item in blocking_missing_info for item in essential_blockers):
        return "Needs more information"
    return decision


def _rules_or_default(
    extracted_rules: list[dict] | None,
    scenario_facts: dict,
    fallback: list[str],
) -> list[str]:
    if extracted_rules:
        selected = select_rules_for_scenario(extracted_rules, scenario_facts)
        bullets = build_rationale_from_rules(selected)
        if bullets:
            return bullets
    return fallback


def evaluate_reimbursement_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    amount = scenario_facts.get("amount") or scenario_facts.get("gift_value")
    currency = (scenario_facts.get("currency") or "INR").upper()
    decision = "Needs approval"
    risk_level = "Medium"
    approvals: list[str] = []

    if not retrieved_chunks:
        return {
            "decision": "Needs more information",
            "risk_level": "Medium",
            "confidence": 0.3,
            "rationale_bullets": ["No relevant policy sections were retrieved."],
            "required_approvals": [],
            "policy_basis": [],
            "decision_factors": {"policy_area": "reimbursement"},
        }

    fallback: list[str] = []
    if currency == "INR" and isinstance(amount, (int, float)):
        if amount > 25000:
            approvals.extend(["Manager", "Finance"])
            fallback.append(
                "TE-004 says client meals above INR 25,000 require manager and Finance pre-approval."
            )
        elif amount > 10000:
            approvals.append("Manager")
            fallback.append(
                "TE-004 says client meals above INR 10,000 require manager approval."
            )
        else:
            decision = "Allowed"
            fallback.append("TE-004 covers client meals up to INR 10,000 with manager approval.")

    if "lost receipt" in str(scenario_facts.get("documentation_provided", [])):
        decision = "Needs more information"
        fallback.append(
            "RE-004 says missing-receipt claims need a lost-receipt declaration and approvals based on amount."
        )

    if scenario_facts.get("alcohol_mentioned"):
        approvals.append("Finance")
        fallback.append("TE-006 says alcohol requires Finance pre-approval and separate itemization.")
        decision = "Needs approval"

    rationale = _rules_or_default(extracted_policy_rules, scenario_facts, fallback)
    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)
    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "policy_basis": basis,
        "decision_factors": {"policy_area": "reimbursement", "amount": amount},
    }


def evaluate_gift_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    amount = scenario_facts.get("gift_value") or scenario_facts.get("amount")
    decision = "Needs approval"
    risk_level = "Medium"
    approvals: list[str] = []

    if scenario_facts.get("cash_gift"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.82,
            "rationale_bullets": _rules_or_default(
                extracted_policy_rules,
                scenario_facts,
                ["GH-004 says cash and cash-equivalent gifts are not allowed."],
            ),
            "required_approvals": ["Compliance"],
            "policy_basis": select_rules_for_scenario(extracted_policy_rules or [], scenario_facts),
            "decision_factors": {"policy_area": "gifts_hospitality", "cash_gift": True},
        }

    if scenario_facts.get("public_official_involved"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.8,
            "rationale_bullets": _rules_or_default(
                extracted_policy_rules,
                scenario_facts,
                ["GH-007 says gifts involving public officials require Legal and Compliance pre-approval."],
            ),
            "required_approvals": ["Legal", "Compliance"],
            "policy_basis": select_rules_for_scenario(extracted_policy_rules or [], scenario_facts),
            "decision_factors": {"policy_area": "gifts_hospitality", "public_official": True},
        }

    if scenario_facts.get("vendor_contract_renewal") or scenario_facts.get("active_rfp"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.78,
            "rationale_bullets": _rules_or_default(
                extracted_policy_rules,
                scenario_facts,
                ["GH-016 and AM-010 require Compliance review during vendor contract renewal or active RFP periods."],
            ),
            "required_approvals": ["Compliance", "Legal"],
            "policy_basis": select_rules_for_scenario(extracted_policy_rules or [], scenario_facts),
            "decision_factors": {"policy_area": "gifts_hospitality", "procurement_risk": True},
        }

    if scenario_facts.get("cumulative_gifts"):
        return {
            "decision": "Needs approval",
            "risk_level": "Medium",
            "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
            "rationale_bullets": _rules_or_default(
                extracted_policy_rules,
                scenario_facts,
                ["GH-006 says cumulative gifts above INR 15,000 from the same counterparty require Compliance review."],
            ),
            "required_approvals": ["Compliance"],
            "policy_basis": select_rules_for_scenario(extracted_policy_rules or [], scenario_facts),
            "decision_factors": {"policy_area": "gifts_hospitality", "cumulative_gifts": True},
        }

    fallback: list[str] = []
    if amount is None:
        decision = "Needs more information"
        fallback.append("Gift value must be confirmed before applying GH-003 thresholds.")
    elif isinstance(amount, (int, float)):
        if amount >= 10000:
            approvals.extend(["Manager", "Compliance"])
            fallback.append(
                "GH-003 says gifts above INR 10,000 require manager and Compliance approval before acceptance."
            )
        elif amount > 5000:
            decision = "Allowed"
            risk_level = "Low"
            fallback.append(
                "GH-003 says gifts above INR 5,000 must be reported to Compliance and recorded in the gift register."
            )
        else:
            decision = "Allowed"
            risk_level = "Low"
            fallback.append(
                "GH-003 treats gifts under INR 2,500 as generally acceptable when modest and not cash."
            )

    if scenario_facts.get("vendor_or_client_involved"):
        fallback.append("GH-016 says vendor and client gifts require threshold and conflict-of-interest review.")

    if not retrieved_chunks:
        decision = "Needs more information"
        fallback.append("No supporting gift policy sections were retrieved.")

    rationale = _rules_or_default(extracted_policy_rules, scenario_facts, fallback)
    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)
    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "policy_basis": basis,
        "decision_factors": {"policy_area": "gifts_hospitality", "gift_value": amount},
    }


def _duration_weeks(scenario_facts: dict) -> float | None:
    duration = str(scenario_facts.get("duration", "")).lower()
    match = __import__("re").search(r"(\d+)\s+week", duration)
    if match:
        return float(match.group(1))
    return None


def evaluate_remote_work_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    decision = "Needs approval"
    risk_level = "Medium"
    approvals = ["Manager"]
    fallback: list[str] = []

    if scenario_facts.get("cross_border_work"):
        return {
            "decision": "Escalate",
            "risk_level": "High",
            "confidence": 0.78,
            "rationale_bullets": _rules_or_default(
                extracted_policy_rules,
                scenario_facts,
                ["RW-005 says cross-border remote work requires HR, Legal, Tax, and InfoSec approval."],
            ),
            "required_approvals": ["HR", "Legal", "Tax", "Information Security"],
            "policy_basis": select_rules_for_scenario(extracted_policy_rules or [], scenario_facts),
            "decision_factors": {"policy_area": "remote_work", "cross_border": True},
        }

    weeks = _duration_weeks(scenario_facts)
    if scenario_facts.get("medical_reason"):
        approvals.append("HR")
        fallback.append("RW-004 says medical remote work over 5 business days requires HR review.")

    if weeks and weeks >= 2:
        fallback.append(
            "RW-003 says remote work for more than 5 consecutive business days requires manager approval and a documented plan."
        )
        if scenario_facts.get("approval_status") == "approved":
            decision = "Allowed"
            fallback.append("Manager approval is already documented for this request.")
    elif scenario_facts.get("approval_status") == "approved":
        decision = "Allowed"
        risk_level = "Low"
        fallback.append("RW-015 says short-term remote work may proceed with documented manager approval.")

    rationale = _rules_or_default(extracted_policy_rules, scenario_facts, fallback or [
        "RW-003 says extended remote work requires documented manager approval."
    ])
    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)
    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "policy_basis": basis,
        "decision_factors": {"policy_area": "remote_work"},
    }


def evaluate_data_access_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    decision = "Needs approval"
    risk_level = "High"
    approvals = ["Information Security"]
    fallback = ["DA-007 says external sharing requires business justification and security review."]

    data_types = scenario_facts.get("data_types", [])
    if "customer data" in data_types:
        approvals.extend(["Legal"])
        fallback.append(
            "DA-003 says customer data external sharing requires business owner, Legal, and InfoSec approval."
        )
    if "hr data" in data_types:
        approvals.extend(["Legal", "HR"])
        fallback.append("DA-018 says HR data external sharing requires HR, Legal, and InfoSec approval.")

    if scenario_facts.get("sensitive_data_involved") and scenario_facts.get("external_vendor_involved"):
        decision = "Escalate"
        approvals = list(dict.fromkeys(approvals + ["Legal", "Compliance"]))

    if not retrieved_chunks:
        decision = "Needs more information"
    else:
        decision = _blocked(decision, blocking_missing_info, retrieved_chunks)

    rationale = _rules_or_default(extracted_policy_rules, scenario_facts, fallback)
    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": list(dict.fromkeys(approvals)),
        "policy_basis": basis,
        "decision_factors": {"policy_area": "data_access"},
    }


def evaluate_travel_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    decision = "Needs approval"
    risk_level = "Medium"
    approvals = ["Manager"]
    fallback = ["TE-011 says hotel upgrades require manager pre-approval."]

    expense_type = str(scenario_facts.get("expense_type", "")).lower()
    if "upgrade" in expense_type:
        fallback.append("Hotel upgrades are not standard lodging and need prior approval.")

    rationale = _rules_or_default(extracted_policy_rules, scenario_facts, fallback)
    decision = _blocked(decision, blocking_missing_info, retrieved_chunks)
    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": rationale[:4],
        "required_approvals": approvals,
        "policy_basis": basis,
        "decision_factors": {"policy_area": "travel_expense"},
    }


def evaluate_general_policy_case(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    if not retrieved_chunks:
        return {
            "decision": "Needs more information",
            "risk_level": "Medium",
            "confidence": 0.3,
            "rationale_bullets": ["No relevant policy evidence was retrieved."],
            "required_approvals": [],
            "policy_basis": [],
            "decision_factors": {"policy_area": scenario_facts.get("policy_area", "general")},
        }

    basis = select_rules_for_scenario(extracted_policy_rules or [], scenario_facts)
    return {
        "decision": "Allowed",
        "risk_level": "Low",
        "confidence": _base_confidence(retrieved_chunks, blocking_missing_info, open_questions),
        "rationale_bullets": build_rationale_from_rules(basis) or [
            "Retrieved policy sections are relevant to the question asked."
        ],
        "required_approvals": [],
        "policy_basis": basis,
        "decision_factors": {"policy_area": scenario_facts.get("policy_area", "general")},
    }


def make_policy_decision(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    blocking_missing_info: list[str],
    open_questions: list[str] | None = None,
    extracted_policy_rules: list[dict] | None = None,
) -> dict:
    """Route to the correct policy evaluator and return a structured decision."""
    policy_area = scenario_facts.get("policy_area", "general")
    open_questions = open_questions or []
    kwargs = {
        "extracted_policy_rules": extracted_policy_rules,
    }

    if policy_area == "reimbursement":
        result = evaluate_reimbursement_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )
    elif policy_area == "gifts_hospitality":
        result = evaluate_gift_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )
    elif policy_area == "remote_work":
        result = evaluate_remote_work_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )
    elif policy_area == "data_access":
        result = evaluate_data_access_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )
    elif policy_area == "travel_expense":
        result = evaluate_travel_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )
    else:
        result = evaluate_general_policy_case(
            scenario_facts, retrieved_chunks, blocking_missing_info, open_questions, **kwargs
        )

    if result["decision"] not in DECISION_VALUES:
        result["decision"] = "Needs more information"
    if result["risk_level"] not in RISK_VALUES:
        result["risk_level"] = "Medium"

    result["blocking_missing_info"] = blocking_missing_info
    result["open_questions"] = open_questions
    result["missing_info"] = blocking_missing_info + open_questions
    return result
