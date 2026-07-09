"""Linear orchestrator for the PolicyOps Agent."""

from __future__ import annotations

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


def run_policy_agent(user_query: str) -> AgentState:
    """Run the Phase 2 PolicyOps Agent workflow."""
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
