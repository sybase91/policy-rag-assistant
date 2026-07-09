"""Workflow nodes for the PolicyOps Agent."""

from __future__ import annotations

from agent.answer_formatter import format_final_answer
from agent.citation_verifier import apply_citation_adjustments, verify_citations
from agent.state import AgentState
from agent.decision_rules import make_policy_decision
from agent.tools import (
    classify_intent_tool,
    generate_clarifying_question_tool,
    generate_next_steps_tool,
    missing_info_tool,
    parse_scenario_tool,
    retrieve_policy_tool,
)
from agent.trace import add_trace_step


def classify_intent_node(state: AgentState) -> AgentState:
    """Classify the user's request intent."""
    add_trace_step(state, "classify_intent", "started", "Classifying the user request intent.")
    try:
        intent = classify_intent_tool(state["user_query"])
        state["intent"] = intent
        add_trace_step(
            state,
            "classify_intent",
            "completed",
            f"Intent classified as {intent}.",
            {"intent": intent},
        )
    except Exception as exc:  # noqa: BLE001
        state["intent"] = "unknown"
        add_trace_step(state, "classify_intent", "failed", f"Intent classification failed: {exc}")
    return state


def parse_scenario_node(state: AgentState) -> AgentState:
    """Extract structured scenario facts from the user query."""
    add_trace_step(state, "parse_scenario", "started", "Extracting structured scenario facts.")
    try:
        facts = parse_scenario_tool(state["user_query"])
        state["scenario_facts"] = facts
        add_trace_step(
            state,
            "parse_scenario",
            "completed",
            "Scenario facts extracted.",
            {"policy_area": facts.get("policy_area"), "amount": facts.get("amount")},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "parse_scenario", "failed", f"Scenario parsing failed: {exc}")
    return state


def retrieve_policy_node(state: AgentState) -> AgentState:
    """Retrieve relevant policy chunks from the vector store."""
    add_trace_step(state, "retrieve_policy", "started", "Retrieving relevant policy sections.")
    try:
        chunks = retrieve_policy_tool(state["user_query"], top_k=5)
        state["retrieved_chunks"] = chunks
        state["citations"] = [
            {
                "source": chunk["source"],
                "section": chunk["section"],
                "section_id": chunk.get("section_id"),
                "score": chunk.get("score"),
            }
            for chunk in chunks
        ]
        add_trace_step(
            state,
            "retrieve_policy",
            "completed",
            f"Retrieved {len(chunks)} policy chunks.",
            {"retrieved_count": len(chunks)},
        )
    except Exception as exc:  # noqa: BLE001
        state["retrieved_chunks"] = []
        state["citations"] = []
        add_trace_step(state, "retrieve_policy", "failed", f"Policy retrieval failed: {exc}")
    return state


def check_missing_info_node(state: AgentState) -> AgentState:
    """Identify missing information needed for a confident decision."""
    add_trace_step(state, "check_missing_info", "started", "Checking for missing scenario details.")
    try:
        missing = missing_info_tool(
            state["user_query"],
            state["scenario_facts"],
            state["retrieved_chunks"],
        )
        state["missing_info"] = missing
        add_trace_step(
            state,
            "check_missing_info",
            "completed",
            f"Missing info check completed with {len(missing)} item(s).",
            {"missing_info": missing},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "check_missing_info", "failed", f"Missing info check failed: {exc}")
    return state


def make_policy_decision_node(state: AgentState) -> AgentState:
    """Make a policy-aware decision from facts and retrieved evidence."""
    add_trace_step(state, "make_policy_decision", "started", "Evaluating policy decision rules.")
    try:
        decision_result = make_policy_decision(
            state["scenario_facts"],
            state["retrieved_chunks"],
            state["missing_info"],
        )
        state["policy_decision"] = decision_result["decision"]
        state["risk_level"] = decision_result["risk_level"]
        state["confidence"] = decision_result["confidence"]
        state["rationale_bullets"] = decision_result.get("rationale_bullets", [])
        state["required_approvals"] = decision_result.get("required_approvals", [])
        state["decision_factors"] = decision_result.get("decision_factors", {})
        add_trace_step(
            state,
            "make_policy_decision",
            "completed",
            f"Decision: {state['policy_decision']}.",
            {
                "decision": state["policy_decision"],
                "risk_level": state["risk_level"],
                "confidence": state["confidence"],
            },
        )
    except Exception as exc:  # noqa: BLE001
        state["policy_decision"] = "Unknown"
        state["risk_level"] = "Medium"
        state["confidence"] = 0.0
        add_trace_step(state, "make_policy_decision", "failed", f"Decision step failed: {exc}")
    return state


def verify_citations_node(state: AgentState) -> AgentState:
    """Verify citations against retrieved chunks only."""
    add_trace_step(state, "verify_citations", "started", "Verifying citations against retrieved chunks.")
    try:
        decision_result = {
            "decision": state.get("policy_decision"),
            "rationale_bullets": state.get("rationale_bullets", []),
        }
        verification = verify_citations(decision_result, state.get("retrieved_chunks", []))
        adjusted = apply_citation_adjustments(
            {
                "decision": state.get("policy_decision"),
                "confidence": state.get("confidence", 0.0),
            },
            verification,
        )

        state["verified_citations"] = verification.get("verified_citations", [])
        state["citation_warnings"] = verification.get("citation_warnings", [])
        state["citation_coverage"] = verification.get("citation_coverage", 0.0)
        state["policy_decision"] = adjusted.get("decision", state["policy_decision"])
        state["confidence"] = adjusted.get("confidence", state["confidence"])
        state["citations"] = state["verified_citations"]

        add_trace_step(
            state,
            "verify_citations",
            "completed",
            f"Verified {len(state['verified_citations'])} citation(s).",
            {
                "citation_coverage": state["citation_coverage"],
                "warnings": state["citation_warnings"],
            },
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "verify_citations", "failed", f"Citation verification failed: {exc}")
    return state


def generate_clarifying_question_node(state: AgentState) -> AgentState:
    """Generate a clarifying question when important details are missing."""
    add_trace_step(
        state,
        "generate_clarifying_question",
        "started",
        "Generating a clarifying question if needed.",
    )
    try:
        question = generate_clarifying_question_tool(
            state.get("missing_info", []),
            state.get("scenario_facts", {}),
            {
                "decision": state.get("policy_decision"),
                "risk_level": state.get("risk_level"),
            },
        )
        state["clarifying_question"] = question
        add_trace_step(
            state,
            "generate_clarifying_question",
            "completed",
            "Clarifying question generated." if question else "No clarifying question needed.",
            {"clarifying_question": question},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(
            state,
            "generate_clarifying_question",
            "failed",
            f"Clarifying question generation failed: {exc}",
        )
    return state


def generate_next_steps_node(state: AgentState) -> AgentState:
    """Generate recommended next steps for the user."""
    add_trace_step(state, "generate_next_steps", "started", "Generating recommended next steps.")
    try:
        steps = generate_next_steps_tool(
            state["policy_decision"],
            state["missing_info"],
            state.get("required_approvals", []),
        )
        state["next_steps"] = steps
        add_trace_step(
            state,
            "generate_next_steps",
            "completed",
            f"Generated {len(steps)} next step(s).",
            {"next_steps": steps},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "generate_next_steps", "failed", f"Next steps generation failed: {exc}")
    return state


def generate_final_answer_node(state: AgentState) -> AgentState:
    """Build the final user-facing answer in a structured format."""
    add_trace_step(state, "generate_final_answer", "started", "Formatting the final answer.")
    try:
        final_answer = format_final_answer(state)
        state["final_answer"] = final_answer
        state["draft_message"] = final_answer
        add_trace_step(
            state,
            "generate_final_answer",
            "completed",
            "Final answer formatted.",
            {"answer_preview": final_answer[:240]},
        )
    except Exception as exc:  # noqa: BLE001
        state["final_answer"] = (
            "I could not complete the PolicyOps Agent workflow for this request. "
            f"Error: {exc}"
        )
        add_trace_step(state, "generate_final_answer", "failed", f"Final answer generation failed: {exc}")
    return state


# Backward-compatible alias for Phase 1 references.
make_basic_decision_node = make_policy_decision_node
