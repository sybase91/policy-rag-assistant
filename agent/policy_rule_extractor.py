"""Deterministic policy rule extraction from retrieved chunks."""

from __future__ import annotations

import re

from agent.citation_verifier import clean_excerpt

SECTION_ID_REGEX = re.compile(r"\b(TE|RE|GH|RW|AM|DA)-\d{3}\b")
AMOUNT_REGEX = re.compile(r"(?:INR|₹|Rs\.?)\s*([\d,]+)", re.IGNORECASE)
APPROVAL_ACTORS = ("Manager", "Finance", "HR", "Legal", "Compliance", "Information Security", "Tax")

RULE_TYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("prohibition", ("not allowed", "never acceptable", "prohibited", "must not", "do not")),
    ("threshold", ("above inr", "below inr", "threshold", "inr 2,500", "inr 5,000", "inr 10,000")),
    ("approval", ("approval", "approve", "pre-approval", "manager", "compliance", "finance")),
    ("documentation", ("receipt", "document", "register", "record", "itemized")),
    ("escalation", ("escalate", "escalation", "compliance review", "legal review")),
    ("definition", ("means", "definition", "applies to", "purpose")),
    ("exception", ("exception", "unless", "may be allowed")),
    ("general", ()),
]


def _classify_rule_type(text: str) -> str:
    lowered = text.lower()
    for rule_type, keywords in RULE_TYPE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return rule_type
    return "general"


def _extract_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for match in AMOUNT_REGEX.finditer(text):
        try:
            amounts.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    return amounts


def _extract_approvals(text: str) -> list[str]:
    found: list[str] = []
    lowered = text.lower()
    mapping = {
        "manager": "Manager",
        "finance": "Finance",
        " hr": "HR",
        "human resources": "HR",
        "legal": "Legal",
        "compliance": "Compliance",
        "information security": "Information Security",
        "infosec": "Information Security",
        "security": "Information Security",
        "tax": "Tax",
    }
    for needle, label in mapping.items():
        if needle in lowered and label not in found:
            found.append(label)
    return found


def _section_title_from_chunk(chunk: dict) -> str:
    section = chunk.get("section", "")
    section_id = chunk.get("section_id")
    if section_id and section.startswith(section_id):
        return section[len(section_id) :].strip(" -")
    return section or "Unknown"


def extract_policy_rules(retrieved_chunks: list[dict]) -> list[dict]:
    """Extract structured policy rules from retrieved chunks."""
    rules: list[dict] = []
    seen: set[str] = set()

    for chunk in retrieved_chunks:
        text = chunk.get("text", "")
        section_id = chunk.get("section_id")
        if not section_id:
            match = SECTION_ID_REGEX.search(text)
            section_id = match.group(0) if match else None
        if not section_id or section_id in seen:
            continue
        seen.add(section_id)

        excerpt = clean_excerpt(text, max_chars=320)
        summary = excerpt
        for sentence in re.split(r"(?<=[.!?])\s+", excerpt):
            if len(sentence) > 20:
                summary = sentence.strip()
                break

        amounts = _extract_amounts(text)
        rules.append(
            {
                "section_id": section_id,
                "section_title": _section_title_from_chunk(chunk),
                "source": chunk.get("source", "unknown"),
                "rule_type": _classify_rule_type(text),
                "rule_summary": summary,
                "threshold_amount": amounts[0] if amounts else None,
                "currency": "INR" if amounts else None,
                "required_approvals": _extract_approvals(text),
                "applies_to": [],
                "raw_excerpt": excerpt,
            }
        )

    return rules


def select_rules_for_scenario(rules: list[dict], scenario_facts: dict) -> list[dict]:
    """Pick rules most relevant to the current scenario."""
    if not rules:
        return []

    policy_area = scenario_facts.get("policy_area", "general")
    amount = scenario_facts.get("gift_value") or scenario_facts.get("amount")
    selected: list[dict] = []

    for rule in rules:
        score = 0
        summary = rule.get("rule_summary", "").lower()
        section_id = (rule.get("section_id") or "").upper()

        if policy_area == "gifts_hospitality" and section_id.startswith("GH"):
            score += 3
        if policy_area == "remote_work" and section_id.startswith("RW"):
            score += 3
        if policy_area == "reimbursement" and section_id.startswith(("TE", "RE")):
            score += 3
        if policy_area == "data_access" and section_id.startswith("DA"):
            score += 3
        if policy_area == "travel_expense" and section_id.startswith("TE"):
            score += 3
        if rule.get("rule_type") == "threshold":
            score += 2
        if isinstance(amount, (int, float)) and rule.get("threshold_amount"):
            if abs(float(rule["threshold_amount"]) - float(amount)) <= 5000:
                score += 2
        if scenario_facts.get("cash_gift") and "cash" in summary:
            score += 4
        if scenario_facts.get("vendor_or_client_involved") and "vendor" in summary:
            score += 1
        if scenario_facts.get("external_vendor_involved") and "vendor" in summary:
            score += 2
        if scenario_facts.get("medical_reason") and "medical" in summary:
            score += 2
        if scenario_facts.get("cross_border_work") and "cross-border" in summary:
            score += 3
        if score > 0:
            selected.append((score, rule))

    selected.sort(key=lambda item: item[0], reverse=True)
    return [rule for _, rule in selected[:5]] or rules[:3]


def summarize_rules_for_explanation(rules: list[dict], policy_area: str) -> list[dict]:
    """Select rules for policy explanation answers."""
    if not rules:
        return []

    prefix_map = {
        "gifts_hospitality": "GH",
        "remote_work": "RW",
        "reimbursement": ("TE", "RE"),
        "data_access": "DA",
        "travel_expense": "TE",
        "general": None,
    }
    prefixes = prefix_map.get(policy_area)
    if prefixes is None:
        return rules[:6]
    if isinstance(prefixes, str):
        prefixes = (prefixes,)

    filtered = [rule for rule in rules if (rule.get("section_id") or "").startswith(prefixes)]
    if not filtered:
        filtered = [rule for rule in rules if not (rule.get("section_id") or "").startswith("AM")]
    return (filtered or rules)[:6]


def build_rationale_from_rules(rules: list[dict], scenario_facts: dict | None = None) -> list[str]:
    """Build rationale bullets citing section IDs."""
    bullets: list[str] = []
    for rule in rules[:4]:
        section_id = rule.get("section_id") or "Policy"
        summary = rule.get("rule_summary") or rule.get("raw_excerpt", "")
        bullets.append(f"{section_id} says {summary}")
    return bullets
