"""Trace helpers for PolicyOps Agent workflow visibility."""

from __future__ import annotations

from agent.state import AgentState


def add_trace_step(
    state: AgentState,
    step_name: str,
    status: str,
    message: str,
    data: dict | None = None,
) -> AgentState:
    """Append a JSON-friendly workflow trace step to the agent state."""
    step = {
        "step_name": step_name,
        "status": status,
        "message": message,
        "data": data or {},
    }
    state["trace"].append(step)
    return state
