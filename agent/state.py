"""Agent state definitions for the PolicyOps Agent."""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Structured state passed through the agent workflow."""

    user_query: str
    intent: str
    scenario_facts: dict
    missing_info: list[str]
    blocking_missing_info: list[str]
    open_questions: list[str]
    retrieved_chunks: list[dict]
    policy_decision: str
    risk_level: str
    confidence: float
    citations: list[dict]
    next_steps: list[str]
    draft_message: str
    final_answer: str
    trace: list[dict]
    rationale_bullets: list[str]
    required_approvals: list[str]
    decision_factors: dict
    verified_citations: list[dict]
    citation_warnings: list[str]
    citation_coverage: float
    clarifying_question: str | None
    # Phase 3 fields
    thread_id: str | None
    conversation_history: list[dict]
    previous_scenario_facts: dict
    merged_scenario_facts: dict
    policy_area: str
    parser_mode: str
    router_path: str
    errors: list[str]
    thread_memory: dict


class GraphState(AgentState, total=False):
    """LangGraph-compatible state schema."""


def create_initial_state(user_query: str) -> AgentState:
    """Create a safe starting state for a new agent run."""
    return {
        "user_query": user_query,
        "intent": "",
        "scenario_facts": {},
        "missing_info": [],
        "blocking_missing_info": [],
        "open_questions": [],
        "retrieved_chunks": [],
        "policy_decision": "",
        "risk_level": "",
        "confidence": 0.0,
        "citations": [],
        "next_steps": [],
        "draft_message": "",
        "final_answer": "",
        "trace": [],
        "rationale_bullets": [],
        "required_approvals": [],
        "decision_factors": {},
        "verified_citations": [],
        "citation_warnings": [],
        "citation_coverage": 0.0,
        "clarifying_question": None,
        "thread_id": None,
        "conversation_history": [],
        "previous_scenario_facts": {},
        "merged_scenario_facts": {},
        "policy_area": "",
        "parser_mode": "heuristic",
        "router_path": "",
        "errors": [],
        "thread_memory": {},
    }
