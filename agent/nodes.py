"""Workflow nodes for the PolicyOps Agent."""

from __future__ import annotations

from agent.answer_formatter import format_final_answer
from agent.citation_verifier import apply_citation_adjustments, verify_citations
from agent.llm_parser import hybrid_parse_scenario
from agent.memory import build_retrieval_query, merge_scenario_facts, slim_agent_state_snapshot
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


def initialize_state_node(state: AgentState) -> AgentState:
    """Seed graph state from thread context and previous snapshots."""
    add_trace_step(state, "initialize_state", "started", "Initializing graph state.")
    previous = state.get("previous_scenario_facts", {})
    if previous:
        state["merged_scenario_facts"] = dict(previous)
    add_trace_step(
        state,
        "initialize_state",
        "completed",
        "Graph state initialized.",
        {"thread_id": state.get("thread_id"), "history_len": len(state.get("conversation_history", []))},
    )
    return state


def hybrid_parse_scenario_node(state: AgentState) -> AgentState:
    """Parse scenario facts using heuristics plus optional LLM enrichment."""
    add_trace_step(state, "hybrid_parse_scenario", "started", "Parsing scenario with hybrid parser.")
    try:
        parsed = hybrid_parse_scenario(
            state["user_query"],
            conversation_history=state.get("conversation_history", []),
            previous_scenario_facts=state.get("previous_scenario_facts", {}),
        )
        state["scenario_facts"] = parsed["facts"]
        state["parser_mode"] = parsed.get("parser_mode", "heuristic")
        if parsed.get("warnings"):
            state.setdefault("errors", []).extend(parsed["warnings"])
        add_trace_step(
            state,
            "hybrid_parse_scenario",
            "completed",
            f"Parser mode: {state['parser_mode']}.",
            {"policy_area": state["scenario_facts"].get("policy_area"), "parser_mode": state["parser_mode"]},
        )
    except Exception as exc:  # noqa: BLE001
        state["scenario_facts"] = parse_scenario_tool(state["user_query"])
        state["parser_mode"] = "heuristic"
        add_trace_step(state, "hybrid_parse_scenario", "failed", f"Hybrid parse failed: {exc}")
    return state


def merge_thread_memory_node(state: AgentState) -> AgentState:
    """Merge previous and newly parsed scenario facts."""
    add_trace_step(state, "merge_thread_memory", "started", "Merging thread memory.")
    try:
        previous = state.get("previous_scenario_facts", {})
        current = state.get("scenario_facts", {})
        merged = merge_scenario_facts(previous, current)
        state["merged_scenario_facts"] = merged
        state["scenario_facts"] = merged
        state["policy_area"] = merged.get("policy_area", "")
        add_trace_step(
            state,
            "merge_thread_memory",
            "completed",
            "Scenario facts merged with thread memory.",
            {"policy_area": state["policy_area"], "merged_fields": list(merged.keys())[:8]},
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "merge_thread_memory", "failed", f"Memory merge failed: {exc}")
    return state


def provisional_clarify_node(state: AgentState) -> AgentState:
    """Set provisional decision when blocking information prevents a full decision."""
    add_trace_step(state, "provisional_clarify", "started", "Setting provisional clarify path.")
    state["policy_decision"] = "Needs more information"
    state["risk_level"] = "Medium"
    state["confidence"] = min(float(state.get("confidence", 0.0) or 0.0), 0.45)
    state["rationale_bullets"] = [
        "Essential facts or policy evidence are still missing for a confident decision."
    ]
    state["router_path"] = "clarify"
    add_trace_step(state, "provisional_clarify", "completed", "Provisional clarify state set.")
    return state


def escalation_review_node(state: AgentState) -> AgentState:
    """Force escalation for high-risk scenarios before citation verification."""
    add_trace_step(state, "escalation_review", "started", "Reviewing high-risk escalation criteria.")
    facts = state.get("merged_scenario_facts") or state.get("scenario_facts", {})
    approvals = ["Compliance"]
    rationale = ["This scenario has elevated governance or compliance risk."]

    if facts.get("sensitive_data_involved") and facts.get("external_vendor_involved"):
        approvals.extend(["Information Security", "Legal"])
        rationale.append("Sensitive data shared externally requires Security and Legal review.")
    if facts.get("public_official_involved"):
        approvals.append("Legal")
        rationale.append("Public official involvement requires Legal review.")
    if facts.get("cash_gift"):
        rationale.append("Cash or cash-equivalent gifts are high-risk and require escalation.")
    if facts.get("cross_border_work"):
        approvals.extend(["HR", "Legal"])
        rationale.append("Cross-border work requires HR and Legal review.")

    state["policy_decision"] = "Escalate"
    state["risk_level"] = "High"
    state["confidence"] = max(float(state.get("confidence", 0.0) or 0.0), 0.7)
    state["rationale_bullets"] = rationale
    state["required_approvals"] = list(dict.fromkeys(approvals))
    state["router_path"] = "escalate"
    add_trace_step(state, "escalation_review", "completed", "Escalation path selected.")
    return state


def save_thread_memory_node(state: AgentState) -> AgentState:
    """Persist a slim memory snapshot for the next turn."""
    add_trace_step(state, "save_thread_memory", "started", "Saving thread memory snapshot.")
    state["thread_memory"] = slim_agent_state_snapshot(state)
    add_trace_step(
        state,
        "save_thread_memory",
        "completed",
        "Thread memory snapshot saved.",
        {"turn_snapshot": state["thread_memory"]},
    )
    return state


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
        query = build_retrieval_query(state)
        chunks = retrieve_policy_tool(query, top_k=5)
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
        classified = missing_info_tool(
            state["user_query"],
            state.get("merged_scenario_facts") or state["scenario_facts"],
            state["retrieved_chunks"],
        )
        state["blocking_missing_info"] = classified["blocking_missing_info"]
        state["open_questions"] = classified["open_questions"]
        state["missing_info"] = classified["missing_info"]
        add_trace_step(
            state,
            "check_missing_info",
            "completed",
            (
                f"Blocking: {len(state['blocking_missing_info'])}, "
                f"open questions: {len(state['open_questions'])}."
            ),
            {
                "blocking_missing_info": state["blocking_missing_info"],
                "open_questions": state["open_questions"],
            },
        )
    except Exception as exc:  # noqa: BLE001
        add_trace_step(state, "check_missing_info", "failed", f"Missing info check failed: {exc}")
    return state


def make_policy_decision_node(state: AgentState) -> AgentState:
    """Make a policy-aware decision from facts and retrieved evidence."""
    add_trace_step(state, "make_policy_decision", "started", "Evaluating policy decision rules.")
    try:
        decision_result = make_policy_decision(
            state.get("merged_scenario_facts") or state["scenario_facts"],
            state["retrieved_chunks"],
            state["blocking_missing_info"],
            state.get("open_questions", []),
        )
        state["router_path"] = "decide"
        state["policy_decision"] = decision_result["decision"]
        state["risk_level"] = decision_result["risk_level"]
        state["confidence"] = decision_result["confidence"]
        state["rationale_bullets"] = decision_result.get("rationale_bullets", [])
        state["required_approvals"] = decision_result.get("required_approvals", [])
        state["decision_factors"] = decision_result.get("decision_factors", {})
        state["open_questions"] = decision_result.get(
            "open_questions", state.get("open_questions", [])
        )
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
            state.get("open_questions", []),
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
            state.get("open_questions", []),
            state.get("required_approvals", []),
            state.get("blocking_missing_info", []),
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
