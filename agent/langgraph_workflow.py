"""LangGraph workflow for PolicyOps Agent Phase 3."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    check_missing_info_node,
    classify_intent_node,
    escalation_review_node,
    generate_clarifying_question_node,
    generate_final_answer_node,
    generate_next_steps_node,
    hybrid_parse_scenario_node,
    initialize_state_node,
    make_policy_decision_node,
    merge_thread_memory_node,
    provisional_clarify_node,
    retrieve_policy_node,
    save_thread_memory_node,
    verify_citations_node,
)
from agent.routing import route_after_missing_info
from agent.state import AgentState, GraphState, create_initial_state


def _build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("initialize_state", initialize_state_node)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("hybrid_parse_scenario", hybrid_parse_scenario_node)
    workflow.add_node("merge_thread_memory", merge_thread_memory_node)
    workflow.add_node("retrieve_policy", retrieve_policy_node)
    workflow.add_node("check_missing_info", check_missing_info_node)
    workflow.add_node("make_policy_decision", make_policy_decision_node)
    workflow.add_node("provisional_clarify", provisional_clarify_node)
    workflow.add_node("escalation_review", escalation_review_node)
    workflow.add_node("generate_clarifying_question", generate_clarifying_question_node)
    workflow.add_node("verify_citations", verify_citations_node)
    workflow.add_node("generate_next_steps", generate_next_steps_node)
    workflow.add_node("generate_final_answer", generate_final_answer_node)
    workflow.add_node("save_thread_memory", save_thread_memory_node)

    workflow.add_edge(START, "initialize_state")
    workflow.add_edge("initialize_state", "classify_intent")
    workflow.add_edge("classify_intent", "hybrid_parse_scenario")
    workflow.add_edge("hybrid_parse_scenario", "merge_thread_memory")
    workflow.add_edge("merge_thread_memory", "retrieve_policy")
    workflow.add_edge("retrieve_policy", "check_missing_info")

    workflow.add_conditional_edges(
        "check_missing_info",
        route_after_missing_info,
        {
            "decide": "make_policy_decision",
            "clarify": "provisional_clarify",
            "escalate": "escalation_review",
        },
    )

    workflow.add_edge("make_policy_decision", "verify_citations")
    workflow.add_edge("provisional_clarify", "verify_citations")
    workflow.add_edge("escalation_review", "verify_citations")
    workflow.add_edge("verify_citations", "generate_clarifying_question")
    workflow.add_edge("generate_clarifying_question", "generate_next_steps")
    workflow.add_edge("generate_next_steps", "generate_final_answer")
    workflow.add_edge("generate_final_answer", "save_thread_memory")
    workflow.add_edge("save_thread_memory", END)

    return workflow.compile()


_COMPILED_GRAPH = None


def get_compiled_graph():
    """Return a singleton compiled LangGraph workflow."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = _build_graph()
    return _COMPILED_GRAPH


def run_policy_agent_graph(
    user_query: str,
    thread_id: str | None = None,
    conversation_history: list[dict] | None = None,
    previous_state: dict | None = None,
) -> AgentState:
    """Run the LangGraph PolicyOps Agent workflow."""
    state = create_initial_state(user_query)
    state["thread_id"] = thread_id
    state["conversation_history"] = conversation_history or []

    previous_facts = {}
    if previous_state:
        previous_facts = (
            previous_state.get("scenario_facts")
            or previous_state.get("merged_scenario_facts")
            or {}
        )
    state["previous_scenario_facts"] = previous_facts

    graph = get_compiled_graph()
    result = graph.invoke(state)
    return result
