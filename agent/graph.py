"""Orchestrator for the PolicyOps Agent."""

from __future__ import annotations

from agent.langgraph_workflow import run_policy_agent_graph
from agent.nodes import (
    check_missing_info_node,
    classify_intent_node,
    generate_clarifying_question_node,
    generate_final_answer_node,
    generate_next_steps_node,
    make_policy_decision_node,
    parse_scenario_node,
    retrieve_policy_node,
    verify_citations_node,
)
from agent.state import AgentState, create_initial_state
from src.config import USE_LANGGRAPH


def run_policy_agent_legacy(user_query: str) -> AgentState:
    """Run the original linear Phase 2 workflow."""
    state = create_initial_state(user_query)

    state = classify_intent_node(state)
    state = parse_scenario_node(state)
    state = retrieve_policy_node(state)
    state = check_missing_info_node(state)
    state = make_policy_decision_node(state)
    state = verify_citations_node(state)
    state = generate_clarifying_question_node(state)
    state = generate_next_steps_node(state)
    state = generate_final_answer_node(state)

    return state


def run_policy_agent(
    user_query: str,
    thread_id: str | None = None,
    conversation_history: list[dict] | None = None,
    previous_state: dict | None = None,
    use_langgraph: bool | None = None,
) -> AgentState:
    """Run PolicyOps Agent with LangGraph by default and legacy fallback."""
    should_use_langgraph = USE_LANGGRAPH if use_langgraph is None else use_langgraph
    if should_use_langgraph:
        return run_policy_agent_graph(
            user_query=user_query,
            thread_id=thread_id,
            conversation_history=conversation_history,
            previous_state=previous_state,
        )
    return run_policy_agent_legacy(user_query)


__all__ = ["run_policy_agent", "run_policy_agent_legacy", "run_policy_agent_graph"]
