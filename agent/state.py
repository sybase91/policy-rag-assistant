"""Agent state definitions for the PolicyOps Agent."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict):
    """Structured state passed through the linear agent workflow."""

    user_query: str
    intent: str
    scenario_facts: dict
    missing_info: list[str]
    retrieved_chunks: list[dict]
    policy_decision: str
    risk_level: str
    confidence: float
    citations: list[dict]
    next_steps: list[str]
    draft_message: str
    final_answer: str
    trace: list[dict]


def create_initial_state(user_query: str) -> AgentState:
    """Create a safe starting state for a new agent run."""
    return {
        "user_query": user_query,
        "intent": "",
        "scenario_facts": {},
        "missing_info": [],
        "retrieved_chunks": [],
        "policy_decision": "",
        "risk_level": "",
        "confidence": 0.0,
        "citations": [],
        "next_steps": [],
        "draft_message": "",
        "final_answer": "",
        "trace": [],
    }
