"""Thread memory helpers for multi-turn PolicyOps Agent conversations."""

from __future__ import annotations

import json
from typing import Any

from agent.state import AgentState


def get_thread_context(thread: dict) -> dict:
    """Extract messages and stored memory from a Streamlit thread."""
    return {
        "messages": thread.get("messages", []),
        "agent_memory": thread.get("agent_memory", {}),
        "thread_id": thread.get("thread_id"),
    }


def get_previous_agent_state(thread: dict) -> dict | None:
    """Return the last agent state snapshot from thread memory or messages."""
    memory = thread.get("agent_memory", {})
    if memory.get("last_agent_state"):
        return memory["last_agent_state"]

    for message in reversed(thread.get("messages", [])):
        if message.get("role") == "assistant":
            metadata = message.get("metadata", {})
            agent_state = metadata.get("agent_state")
            if agent_state:
                return slim_agent_state_snapshot(agent_state)
    return None


def serialize_agent_state_for_ui(state: dict | None) -> dict:
    """Return a JSON-safe agent state copy for Streamlit storage and debug panels."""
    if not state:
        return {}

    payload = dict(state)
    history = payload.pop("conversation_history", None) or []
    payload["conversation_history_len"] = len(history)

    # Aliased lists (citations == verified_citations) must not be walked twice.
    if payload.get("citations") is payload.get("verified_citations"):
        payload.pop("citations", None)

    try:
        return json.loads(json.dumps(payload, default=str))
    except (TypeError, ValueError):
        return _json_safe(payload)


def normalize_citation_entries(citations: Any) -> list[dict]:
    """Coerce citation data into a list of dicts for UI rendering."""
    if not citations:
        return []
    if isinstance(citations, str):
        return []
    if isinstance(citations, dict):
        if any(key in citations for key in ("section_id", "section", "source")):
            return [citations]
        return []

    normalized: list[dict] = []
    if not isinstance(citations, list):
        return normalized

    for item in citations:
        if isinstance(item, dict):
            normalized.append(item)
        elif isinstance(item, str) and item.strip():
            normalized.append(
                {
                    "section_id": item,
                    "section": item,
                    "section_title": item,
                    "source": "unknown",
                }
            )
    return normalized


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
    """Recursively convert a value to JSON-serializable data."""
    if seen is None:
        seen = set()

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    obj_id = id(value)
    if obj_id in seen:
        if isinstance(value, dict):
            return {
                str(key): _json_safe(item, seen | {obj_id})
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [_json_safe(item, seen | {obj_id}) for item in value]
        return str(value)

    if isinstance(value, dict):
        seen.add(obj_id)
        return {str(key): _json_safe(item, seen) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        seen.add(obj_id)
        return [_json_safe(item, seen) for item in value]

    return str(value)


def is_follow_up_turn(thread: dict) -> bool:
    """True when the prior agent turn left open questions or a clarifying question."""
    prev = get_previous_agent_state(thread)
    if not prev:
        return False
    if prev.get("clarifying_question"):
        return True
    if prev.get("open_questions"):
        return True
    return bool(prev.get("blocking_missing_info"))


def merge_scenario_facts(previous: dict | None, new: dict) -> dict:
    """Merge scenario facts; new explicit values override previous ones."""
    merged = dict(previous or {})
    for key, value in new.items():
        if value is None:
            continue
        if isinstance(value, bool):
            merged[key] = value
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        if isinstance(value, str) and value == "":
            continue
        merged[key] = value
    return merged


def summarize_thread_for_agent(thread: dict, max_turns: int = 6) -> str:
    """Build a compact conversation summary for LLM parsing."""
    lines: list[str] = []
    messages = thread.get("messages", [])[-max_turns:]
    for message in messages:
        role = message.get("role", "unknown")
        content = (message.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_retrieval_query(state: AgentState) -> str:
    """Build a retrieval query that includes merged scenario context on follow-ups."""
    facts = state.get("merged_scenario_facts") or state.get("scenario_facts", {})
    parts = [state.get("user_query", "")]
    if facts.get("policy_area"):
        parts.append(f"policy area {facts['policy_area']}")
    if facts.get("amount"):
        parts.append(f"amount {facts['amount']} {facts.get('currency', '')}")
    if facts.get("vendor_or_client_involved"):
        parts.append("vendor client gift")
    if facts.get("external_vendor_involved"):
        parts.append("external vendor data sharing")
    if facts.get("expense_type"):
        parts.append(str(facts["expense_type"]))
    return " ".join(part for part in parts if part).strip()


def slim_agent_state_snapshot(state: AgentState) -> dict:
    """Store a lightweight agent snapshot on the thread for follow-up turns."""
    return {
        "scenario_facts": state.get("merged_scenario_facts") or state.get("scenario_facts", {}),
        "policy_decision": state.get("policy_decision"),
        "risk_level": state.get("risk_level"),
        "confidence": state.get("confidence"),
        "open_questions": state.get("open_questions", []),
        "blocking_missing_info": state.get("blocking_missing_info", []),
        "clarifying_question": state.get("clarifying_question"),
        "required_approvals": state.get("required_approvals", []),
        "user_query": state.get("user_query"),
    }


def save_agent_state_to_thread(thread: dict, state: AgentState) -> None:
    """Persist agent memory on the Streamlit thread object."""
    memory = thread.setdefault("agent_memory", {})
    snapshot = slim_agent_state_snapshot(state)
    memory["scenario_facts"] = snapshot["scenario_facts"]
    memory["last_agent_state"] = snapshot
    memory["turn_count"] = int(memory.get("turn_count", 0)) + 1
