"""Rule-based tools for PolicyOps Agent Phase 1."""

from __future__ import annotations

import re

from src.retrieve import get_vectorstore

AMOUNT_PATTERN = re.compile(
    r"(?:₹|INR\s*|Rs\.?\s*)(\d[\d,]*(?:\.\d+)?)",
    re.IGNORECASE,
)
PLAIN_AMOUNT_PATTERN = re.compile(r"\b(\d[\d,]{3,})\b")


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


def _parse_amount(text: str) -> int | None:
    """Extract a numeric amount from INR-style or plain number text."""
    match = AMOUNT_PATTERN.search(text)
    if match:
        return int(float(match.group(1).replace(",", "")))

    plain_match = PLAIN_AMOUNT_PATTERN.search(text)
    if plain_match:
        return int(plain_match.group(1).replace(",", ""))
    return None


def parse_scenario_tool(user_query: str) -> dict:
    """Extract basic structured facts using lightweight heuristics."""
    text = user_query.lower()
    facts: dict = {"raw_query": user_query}

    amount = _parse_amount(user_query)
    if amount is not None:
        facts["amount"] = amount
        facts["currency"] = "INR"

    if "personal card" in text or "own card" in text:
        facts["payment_method"] = "personal card"
    if "external guest" in text or "client dinner" in text or "client meal" in text:
        facts["people_involved"] = "external guests"
        facts["policy_area"] = "reimbursement"
    elif "vendor" in text and "gift" in text:
        facts["policy_area"] = "gifts_hospitality"
        facts["people_involved"] = "vendor"
    elif "remote" in text or "work from home" in text:
        facts["policy_area"] = "remote_work"
    elif "hotel upgrade" in text or "upgrade" in text:
        facts["policy_area"] = "travel_expense"
    elif "customer data" in text or "share data" in text:
        facts["policy_area"] = "data_access"
    elif "reimburse" in text or "receipt" in text:
        facts["policy_area"] = "reimbursement"

    if "medical" in text:
        facts["reason"] = "medical"

    duration_match = re.search(r"(\d+)\s+(day|days|week|weeks)", text)
    if duration_match:
        facts["duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"

    if "alcohol" in text:
        facts["alcohol_included"] = True

    if "manager approval" in text or "approved by manager" in text:
        facts["approval_status"] = "manager approved"

    return facts


def _format_section(metadata: dict) -> str:
    """Build a readable section label from chunk metadata."""
    section_id = metadata.get("section_id")
    section_title = metadata.get("section_title")
    policy_name = metadata.get("policy_name")

    if section_id and section_title:
        return f"{section_id} {section_title}"
    if policy_name:
        return str(policy_name)
    return "Unknown section"


def retrieve_policy_tool(user_query: str, top_k: int = 5) -> list[dict]:
    """Retrieve policy chunks and normalize them for the agent workflow."""
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(user_query, k=top_k)

    normalized: list[dict] = []
    for doc, score in results:
        metadata = doc.metadata
        distance = float(score)
        similarity = max(0.0, min(1.0, 1.0 - distance))

        normalized.append(
            {
                "text": doc.page_content,
                "source": metadata.get("source_file", metadata.get("policy_name", "unknown")),
                "section": _format_section(metadata),
                "score": round(similarity, 2),
                "metadata": {
                    "policy_name": metadata.get("policy_name"),
                    "section_id": metadata.get("section_id"),
                    "section_title": metadata.get("section_title"),
                    "chunk_id": metadata.get("chunk_id"),
                },
            }
        )

    return normalized


def missing_info_tool(
    user_query: str,
    scenario_facts: dict,
    retrieved_chunks: list[dict],
) -> list[str]:
    """Return a list of missing details based on simple policy rules."""
    text = user_query.lower()
    missing: list[str] = []

    if any(word in text for word in ("reimburse", "claim", "expense", "dinner", "meal")):
        if "amount" not in scenario_facts:
            missing.append("amount")
        if "receipt" not in text and "lost receipt" not in text:
            missing.append("itemized receipt")
        if "approval" not in text and "approved" not in text:
            missing.append("approval status")
        if ("client" in text or "guest" in text) and "guest" not in text and "attendee" not in text:
            missing.append("guest details")

    if "travel" in text or "trip" in text or "hotel" in text:
        if "date" not in text and "duration" not in scenario_facts:
            missing.append("travel details")

    if "gift" in text and "amount" not in scenario_facts:
        missing.append("gift value")

    if ("remote" in text or "work from home" in text) and "duration" not in scenario_facts:
        missing.append("remote work duration")

    if "approval" in text and "approval_status" not in scenario_facts:
        missing.append("approver information")

    if "share" in text and "customer data" in text:
        if "vendor" not in text:
            missing.append("external party details")
        missing.append("Information Security approval status")

    if not retrieved_chunks:
        missing.append("relevant policy evidence")

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(missing))


def basic_decision_tool(
    scenario_facts: dict,
    retrieved_chunks: list[dict],
    missing_info: list[str],
) -> dict:
    """Return a conservative Phase 1 policy decision."""
    if not retrieved_chunks:
        return {
            "decision": "Needs more information",
            "risk_level": "Medium",
            "confidence": 0.35,
        }

    if missing_info:
        decision = "Needs more information"
        confidence = 0.55
    else:
        decision = "Needs approval"
        confidence = 0.65

    amount = scenario_facts.get("amount")
    policy_area = scenario_facts.get("policy_area", "")

    if policy_area == "gifts_hospitality" and isinstance(amount, int) and amount >= 10000:
        decision = "Needs approval"
        confidence = 0.7

    if policy_area == "data_access":
        decision = "Needs approval"
        confidence = 0.75

    if policy_area == "travel_expense" and "upgrade" in scenario_facts.get("raw_query", "").lower():
        decision = "Needs approval"
        confidence = 0.7

    if scenario_facts.get("alcohol_included"):
        decision = "Needs approval"
        confidence = max(confidence, 0.68)

    if policy_area == "remote_work" and scenario_facts.get("reason") == "medical":
        decision = "Needs approval"
        confidence = 0.62

    weak_evidence = not retrieved_chunks or max(chunk["score"] for chunk in retrieved_chunks) < 0.35
    if weak_evidence:
        decision = "Needs more information"
        confidence = min(confidence, 0.5)

    risk_level = "Low"
    if decision in {"Needs approval", "Needs more information"}:
        risk_level = "Medium"
    if policy_area == "data_access":
        risk_level = "High"

    return {
        "decision": decision,
        "risk_level": risk_level,
        "confidence": round(confidence, 2),
    }


def generate_next_steps_tool(decision: str, missing_info: list[str]) -> list[str]:
    """Generate simple next-step guidance for the user."""
    steps: list[str] = []

    if missing_info:
        steps.append("Confirm the missing information before submitting the request.")
        for item in missing_info:
            steps.append(f"Provide {item}.")

    if decision == "Needs approval":
        steps.append(
            "Check whether manager, Finance, HR, Legal, or Information Security approval is required."
        )

    steps.append("Attach relevant receipts or supporting documents.")
    steps.append("Review the cited Acme Corp policy sections before taking action.")

    return list(dict.fromkeys(steps))
