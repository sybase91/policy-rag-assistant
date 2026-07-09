"""Workflow nodes for the PolicyOps Agent."""

from __future__ import annotations

from agent.state import AgentState
from agent.tools import (
    basic_decision_tool,
    classify_intent_tool,
    generate_next_steps_tool,
    missing_info_tool,
    parse_scenario_tool,
    retrieve_policy_tool,
)
from agent.trace import add_trace_step


def classify_intent_node(state: AgentState) -> AgentState:
    """Classify the user's request intent."""
    add_trace_step(
        state,
        "classify_intent",
        "started",
        "Classifying the user request intent.",
    )
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
        add_trace_step(
            state,
            "classify_intent",
            "failed",
            f"Intent classification failed: {exc}",
        )
    return state


def parse_scenario_node(state: AgentState) -> AgentState:
    """Extract structured scenario facts from the user query."""
    add_trace_step(
        state,
        "parse_scenario",
        "started",
        "Extracting structured scenario facts.",
    )
    try:
        facts = parse_scenario_tool(state["user_query"])
        state["scenario_facts"] = facts
        add_trace_step(
            state,
            "parse_scenario",
            "completed",
            "Scenario facts extracted.",
            {"scenario_facts": facts},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(
            state,
            "parse_scenario",
            "failed",
            f"Scenario parsing failed: {exc}",
        )
    return state


def retrieve_policy_node(state: AgentState) -> AgentState:
    """Retrieve relevant policy chunks from the vector store."""
    add_trace_step(
        state,
        "retrieve_policy",
        "started",
        "Retrieving relevant policy sections.",
    )
    try:
        chunks = retrieve_policy_tool(state["user_query"], top_k=5)
        state["retrieved_chunks"] = chunks
        state["citations"] = [
            {
                "source": chunk["source"],
                "section": chunk["section"],
                "score": chunk["score"],
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
        add_trace_step(
            state,
            "retrieve_policy",
            "failed",
            f"Policy retrieval failed: {exc}",
        )
    return state


def check_missing_info_node(state: AgentState) -> AgentState:
    """Identify missing information needed for a confident decision."""
    add_trace_step(
        state,
        "check_missing_info",
        "started",
        "Checking for missing scenario details.",
    )
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
        add_trace_step(
            state,
            "check_missing_info",
            "failed",
            f"Missing info check failed: {exc}",
        )
    return state


def make_basic_decision_node(state: AgentState) -> AgentState:
    """Make a conservative policy decision from facts and retrieved evidence."""
    add_trace_step(
        state,
        "make_basic_decision",
        "started",
        "Evaluating a basic policy decision.",
    )
    try:
        decision_result = basic_decision_tool(
            state["scenario_facts"],
            state["retrieved_chunks"],
            state["missing_info"],
        )
        state["policy_decision"] = decision_result["decision"]
        state["risk_level"] = decision_result["risk_level"]
        state["confidence"] = decision_result["confidence"]
        add_trace_step(
            state,
            "make_basic_decision",
            "completed",
            f"Decision: {state['policy_decision']}.",
            decision_result,
        )
    except Exception as exc:  # noqa: BLE001
        state["policy_decision"] = "Unknown"
        state["risk_level"] = "Medium"
        state["confidence"] = 0.0
        add_trace_step(
            state,
            "make_basic_decision",
            "failed",
            f"Decision step failed: {exc}",
        )
    return state


def generate_next_steps_node(state: AgentState) -> AgentState:
    """Generate recommended next steps for the user."""
    add_trace_step(
        state,
        "generate_next_steps",
        "started",
        "Generating recommended next steps.",
    )
    try:
        steps = generate_next_steps_tool(
            state["policy_decision"],
            state["missing_info"],
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
        add_trace_step(
            state,
            "generate_next_steps",
            "failed",
            f"Next steps generation failed: {exc}",
        )
    return state


def generate_final_answer_node(state: AgentState) -> AgentState:
    """Build the final user-facing answer in a deterministic format."""
    add_trace_step(
        state,
        "generate_final_answer",
        "started",
        "Formatting the final answer.",
    )
    try:
        lines = [
            f"Decision: {state['policy_decision'] or 'Unknown'}",
            "",
            f"Risk level: {state['risk_level'] or 'Unknown'}",
            "",
            "Summary:",
        ]

        if state["missing_info"]:
            lines.append(
                "Based on the information provided, I found potentially relevant "
                "policy sections, but more information is needed before a confident "
                "decision can be made."
            )
        else:
            lines.append(
                "Based on the information provided and the retrieved policy sections, "
                "this request likely requires review against Acme Corp policy rules."
            )

        if state["missing_info"]:
            lines.extend(["", "Missing information:"])
            for item in state["missing_info"]:
                lines.append(f"- {item}")

        if state["citations"]:
            lines.extend(["", "Relevant policy sources:"])
            for citation in state["citations"]:
                policy_name = citation.get("source", "unknown")
                section = citation.get("section", "Unknown section")
                lines.append(f"- {policy_name}, {section}")

        if state["next_steps"]:
            lines.extend(["", "Recommended next steps:"])
            for index, step in enumerate(state["next_steps"], start=1):
                lines.append(f"{index}. {step}")

        final_answer = "\n".join(lines)
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
        add_trace_step(
            state,
            "generate_final_answer",
            "failed",
            f"Final answer generation failed: {exc}",
        )
    return state
