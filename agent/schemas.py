"""Typed structures for PolicyOps Agent Phase 2 outputs.

These TypedDict definitions document the expected shape of agent data.
They help beginners understand what each workflow step produces.
"""

from __future__ import annotations

from typing import TypedDict

DECISION_VALUES = (
    "Allowed",
    "Not allowed",
    "Needs approval",
    "Needs more information",
    "Escalate",
)

RISK_VALUES = ("Low", "Medium", "High")


class ScenarioFacts(TypedDict, total=False):
    """Structured facts extracted from the user scenario."""

    policy_area: str
    amount: float | None
    currency: str | None
    expense_type: str | None
    people_involved: list[str]
    external_parties_involved: bool
    payment_method: str | None
    location: str | None
    duration: str | None
    approval_status: str | None
    documentation_provided: list[str]
    sensitive_data_involved: bool
    gift_value: float | None
    vendor_or_client_involved: bool
    alcohol_mentioned: bool
    medical_reason: bool
    cross_border_work: bool
    public_official_involved: bool
    cash_gift: bool
    data_types: list[str]
    external_vendor_involved: bool
    submission_days_late: int | None
    duplicate_claim: bool
    personal_expense: bool
    data_already_shared: bool
    public_ai_tool: bool
    personal_channel: bool
    public_link_sharing: bool
    cumulative_gifts: bool
    vendor_contract_renewal: bool
    active_rfp: bool
    personal_gift: bool
    vendor_hospitality: bool
    production_access: bool
    raw_query: str


class RetrievedPolicyChunk(TypedDict, total=False):
    """One normalized policy chunk returned by retrieval."""

    text: str
    source: str
    section: str
    section_id: str | None
    score: float | None


class VerifiedCitation(TypedDict, total=False):
    """A citation verified against retrieved chunks."""

    source: str
    section: str
    section_id: str | None
    supporting_text_excerpt: str


class PolicyDecision(TypedDict, total=False):
    """Structured policy decision output."""

    decision: str
    risk_level: str
    confidence: float
    rationale_bullets: list[str]
    missing_info: list[str]
    required_approvals: list[str]
    citations: list[dict]
    recommended_next_steps: list[str]
    clarifying_question: str | None
    decision_factors: dict


def empty_scenario_facts(raw_query: str) -> ScenarioFacts:
    """Create a safe empty ScenarioFacts dictionary."""
    return {
        "policy_area": "",
        "amount": None,
        "currency": None,
        "expense_type": None,
        "people_involved": [],
        "external_parties_involved": False,
        "payment_method": None,
        "location": None,
        "duration": None,
        "approval_status": None,
        "documentation_provided": [],
        "sensitive_data_involved": False,
        "gift_value": None,
        "vendor_or_client_involved": False,
        "alcohol_mentioned": False,
        "medical_reason": False,
        "cross_border_work": False,
        "public_official_involved": False,
        "cash_gift": False,
        "data_types": [],
        "external_vendor_involved": False,
        "submission_days_late": None,
        "duplicate_claim": False,
        "personal_expense": False,
        "data_already_shared": False,
        "public_ai_tool": False,
        "personal_channel": False,
        "public_link_sharing": False,
        "cumulative_gifts": False,
        "vendor_contract_renewal": False,
        "active_rfp": False,
        "personal_gift": False,
        "vendor_hospitality": False,
        "production_access": False,
        "raw_query": raw_query,
    }


def decision_values() -> tuple[str, ...]:
    """Return allowed decision labels."""
    return DECISION_VALUES


def risk_values() -> tuple[str, ...]:
    """Return allowed risk labels."""
    return RISK_VALUES
