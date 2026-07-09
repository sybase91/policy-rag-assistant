"""Rule-based tools for PolicyOps Agent."""

from __future__ import annotations

import re

from agent.decision_rules import make_policy_decision
from agent.schemas import empty_scenario_facts
from src.retrieve import get_vectorstore

INR_PATTERN = re.compile(
    r"(?:₹|INR\s*|Rs\.?\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)
USD_PATTERN = re.compile(
    r"(?:\$|USD\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)
PLAIN_AMOUNT_PATTERN = re.compile(r"\b(\d[\d,]{3,})\b")
SECTION_ID_REGEX = re.compile(r"\b(TE|RE|GH|RW|AM|DA)-\d{3}\b")


def classify_intent_tool(user_query: str) -> str:
    """Classify the query using simple keyword rules."""
    text = user_query.lower()

    if any(word in text for word in ("reimburse", "reimbursement", "claim", "receipt")):
        return "reimbursement_check"
    if any(word in text for word in ("approve", "approval", "allowed", "permitted")):
        return "approval_check"
    if any(word in text for word in ("compliance", "conflict", "vendor", "gift", "data")):
        return "compliance_check"
    if any(word in text for word in ("can i", "am i", "should i", "if i", "lost my")):
        return "policy_scenario"
    if any(word in text for word in ("what is", "what are", "policy", "rule")):
        return "policy_question"
    return "unknown"


def _parse_amount_and_currency(text: str) -> tuple[float | None, str | None]:
    """Extract amount and currency from mixed formats."""
    inr_match = INR_PATTERN.search(text)
    if inr_match:
        return float(inr_match.group(1).replace(",", "")), "INR"

    usd_match = USD_PATTERN.search(text)
    if usd_match:
        return float(usd_match.group(1).replace(",", "")), "USD"

    plain_match = PLAIN_AMOUNT_PATTERN.search(text)
    if plain_match:
        return float(plain_match.group(1).replace(",", "")), "INR"

    return None, None


def parse_scenario_tool(user_query: str) -> dict:
    """Extract structured scenario facts using lightweight heuristics."""
    text = user_query.lower()
    facts = empty_scenario_facts(user_query)

    amount, currency = _parse_amount_and_currency(user_query)
    if amount is not None:
        facts["amount"] = amount
        facts["currency"] = currency
        facts["gift_value"] = amount

    documentation: list[str] = []
    if "receipt" in text and "lost" not in text:
        documentation.append("receipt mentioned")
    if "lost receipt" in text or "lost my receipt" in text:
        documentation.append("lost receipt")
    facts["documentation_provided"] = documentation

    if "personal card" in text or "own card" in text or "my own card" in text:
        facts["payment_method"] = "personal card"
    elif "company card" in text or "corporate card" in text:
        facts["payment_method"] = "company card"

    people: list[str] = []
    if "external guest" in text or "external guests" in text:
        people.append("external guests")
        facts["external_parties_involved"] = True
    if "client" in text:
        people.append("client")
        facts["external_parties_involved"] = True
    if "vendor" in text:
        people.append("vendor")
        facts["vendor_or_client_involved"] = True
    facts["people_involved"] = people

    if any(word in text for word in ("client dinner", "client meal", "meal", "dinner", "taxi", "reimburse", "receipt")):
        facts["policy_area"] = "reimbursement"
        if "client dinner" in text or "client meal" in text:
            facts["expense_type"] = "client dinner"
        elif "taxi" in text:
            facts["expense_type"] = "taxi"
        elif "meal" in text or "dinner" in text:
            facts["expense_type"] = "meal"

    if "gift" in text:
        facts["policy_area"] = "gifts_hospitality"
        facts["expense_type"] = "gift"
        if "vendor" in text:
            facts["vendor_or_client_involved"] = True

    if "remote" in text or "work from home" in text or "wfh" in text:
        facts["policy_area"] = "remote_work"

    if "hotel upgrade" in text or ("upgrade" in text and "hotel" in text):
        facts["policy_area"] = "travel_expense"
        facts["expense_type"] = "hotel upgrade"
    elif "travel" in text or "trip" in text or "hotel" in text:
        facts["policy_area"] = "travel_expense"
        facts["expense_type"] = "travel"

    data_types: list[str] = []
    if "customer data" in text:
        data_types.append("customer data")
        facts["policy_area"] = "data_access"
        facts["sensitive_data_involved"] = True
    if "hr data" in text:
        data_types.append("hr data")
        facts["policy_area"] = "data_access"
        facts["sensitive_data_involved"] = True
    if "finance data" in text:
        data_types.append("finance data")
        facts["policy_area"] = "data_access"
        facts["sensitive_data_involved"] = True
    if "confidential" in text:
        facts["sensitive_data_involved"] = True
    facts["data_types"] = data_types

    if "external vendor" in text or ("vendor" in text and "share" in text):
        facts["external_vendor_involved"] = True
        facts["policy_area"] = "data_access"

    if "public official" in text:
        facts["public_official_involved"] = True
        facts["policy_area"] = "gifts_hospitality"

    if "cash gift" in text or "cash" in text and "gift" in text:
        facts["cash_gift"] = True
        facts["policy_area"] = "gifts_hospitality"

    if "medical" in text:
        facts["medical_reason"] = True

    if "cross-border" in text or "another country" in text or "outside the country" in text:
        facts["cross_border_work"] = True

    duration_match = re.search(r"(\d+)\s+(day|days|week|weeks)", text)
    if duration_match:
        facts["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"

    if "alcohol" in text:
        facts["alcohol_mentioned"] = True

    if any(word in text for word in ("already approved", "manager approved", "approved by manager")):
        facts["approval_status"] = "approved"
    elif "not approved" in text or "without approval" in text:
        facts["approval_status"] = "not approved"
    else:
        facts["approval_status"] = "unknown"

    if facts["policy_area"] == "" and "policy" in text:
        facts["policy_area"] = "general"

    return facts


def _format_section(metadata: dict) -> str:
    """Build a readable section label from chunk metadata."""
    section_id = metadata.get("section_id")
    section_title = metadata.get("section_title")
    if section_id and section_title:
        return f"{section_id} {section_title}"
    if section_id:
        return str(section_id)
    if section_title:
        return str(section_title)
    policy_name = metadata.get("policy_name")
    if policy_name:
        return str(policy_name)
    return "Unknown section"


def _extract_section_id(metadata: dict, section: str, text: str) -> str | None:
    """Get section_id from metadata or regex fallback."""
    section_id = metadata.get("section_id")
    if section_id:
        return str(section_id)
    match = SECTION_ID_REGEX.search(section) or SECTION_ID_REGEX.search(text)
    return match.group(0) if match else None


def retrieve_policy_tool(user_query: str, top_k: int = 5) -> list[dict]:
    """Retrieve policy chunks and normalize them for the agent workflow."""
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(user_query, k=top_k)

    normalized: list[dict] = []
    for doc, score in results:
        metadata = doc.metadata
        distance = float(score)
        similarity = round(max(0.0, min(1.0, 1.0 - distance)), 2)
        section = _format_section(metadata)
        section_id = _extract_section_id(metadata, section, doc.page_content)

        normalized.append(
            {
                "text": doc.page_content,
                "source": metadata.get("source_file", metadata.get("policy_name", "unknown")),
                "section": section,
                "section_id": section_id,
                "score": similarity,
            }
        )

    return normalized


def missing_info_tool(
    user_query: str,
    scenario_facts: dict,
    retrieved_chunks: list[dict],
) -> list[str]:
    """Return policy-area aware missing information."""
    text = user_query.lower()
    missing: list[str] = []
    policy_area = scenario_facts.get("policy_area", "general")

    if not retrieved_chunks:
        missing.append("relevant policy evidence")

    if policy_area == "reimbursement":
        if scenario_facts.get("amount") is None:
            missing.append("amount")
        if "receipt mentioned" not in scenario_facts.get("documentation_provided", []) and "lost receipt" not in scenario_facts.get("documentation_provided", []):
            if "receipt" not in text and "lost" not in text:
                missing.append("itemized receipt")
        if "business purpose" not in text:
            missing.append("business purpose")
        if scenario_facts.get("external_parties_involved") and "attendee" not in text and "guest" not in text:
            missing.append("attendee names")
        if scenario_facts.get("approval_status") == "unknown":
            missing.append("approval status")
        if scenario_facts.get("expense_type") in {"client dinner", "meal"} and not scenario_facts.get("alcohol_mentioned"):
            if "alcohol" not in text:
                missing.append("whether alcohol was included")

    elif policy_area == "gifts_hospitality":
        if scenario_facts.get("gift_value") is None and scenario_facts.get("amount") is None:
            missing.append("gift value")
        if not scenario_facts.get("people_involved"):
            missing.append("giver/recipient details")
        if "vendor" not in text and "client" not in text:
            missing.append("whether vendor or client is involved")
        if not scenario_facts.get("cash_gift") and "cash" not in text:
            missing.append("whether the gift is cash or cash equivalent")
        if scenario_facts.get("public_official_involved") is False and "public official" not in text:
            missing.append("whether a public official is involved")

    elif policy_area == "remote_work":
        if not scenario_facts.get("duration"):
            missing.append("remote work duration")
        if "location" not in text and not scenario_facts.get("location"):
            missing.append("work location")
        if scenario_facts.get("approval_status") == "unknown":
            missing.append("manager approval")
        if scenario_facts.get("medical_reason") and "hr" not in text:
            missing.append("HR approval for medical exception")
        if scenario_facts.get("cross_border_work"):
            missing.append("cross-border approval details")

    elif policy_area == "data_access":
        if not scenario_facts.get("data_types"):
            missing.append("type of data")
        if scenario_facts.get("external_vendor_involved") and scenario_facts.get("approval_status") == "unknown":
            missing.append("Information Security approval status")
        if scenario_facts.get("sensitive_data_involved"):
            missing.append("data classification")

    return list(dict.fromkeys(missing))


def generate_clarifying_question_tool(
    missing_info: list[str],
    scenario_facts: dict,
    decision_result: dict,
) -> str | None:
    """Generate a short clarifying question when key details are missing."""
    if not missing_info:
        return None

    policy_area = scenario_facts.get("policy_area", "general")
    missing_text = " ".join(missing_info).lower()

    if policy_area == "reimbursement":
        return (
            "Was alcohol included in the bill, and do you already have manager approval?"
        )
    if policy_area == "gifts_hospitality":
        return (
            "What is the approximate value of the gift, and is the giver a vendor, client, or public official?"
        )
    if policy_area == "remote_work":
        return (
            "How long do you need to work remotely, and do you already have manager or HR approval?"
        )
    if policy_area == "data_access":
        return (
            "What type of customer data will be shared, and has Security or Legal approved the external vendor?"
        )
    if "receipt" in missing_text:
        return "Do you have an itemized receipt or approved lost-receipt documentation?"
    return "Can you provide the missing details listed above before submitting this request?"


def generate_next_steps_tool(
    decision: str,
    missing_info: list[str],
    required_approvals: list[str] | None = None,
) -> list[str]:
    """Generate recommended next steps."""
    steps: list[str] = []
    required_approvals = required_approvals or []

    if missing_info:
        steps.append("Confirm the missing information before submitting the request.")
        for item in missing_info:
            steps.append(f"Provide {item}.")

    for approval in required_approvals:
        steps.append(f"Request {approval} approval if not already obtained.")

    if decision == "Needs approval":
        steps.append(
            "Check whether manager, Finance, HR, Legal, or Information Security approval is required."
        )
    if decision == "Escalate":
        steps.append("Escalate this request to the appropriate governance team before proceeding.")

    steps.append("Attach relevant receipts or supporting documents.")
    steps.append("Review the cited Acme Corp policy sections before taking action.")
    return list(dict.fromkeys(steps))


def basic_decision_tool(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Backward-compatible wrapper around Phase 2 policy decision logic."""
    return make_policy_decision(scenario_facts, retrieved_chunks, missing_info)
