"""LLM-assisted scenario parsing with deterministic fallback."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from agent.tools import merge_follow_up_facts, parse_scenario_tool
from src.config import LLM_PARSER_MODEL, USE_LLM_PARSER
from src.embed import validate_api_key


class ParsedScenarioOutput(BaseModel):
    """Structured scenario fields for LLM parsing."""

    policy_area: str = ""
    amount: float | None = None
    currency: str | None = None
    expense_type: str | None = None
    payment_method: str | None = None
    vendor_or_client_involved: bool = False
    external_vendor_involved: bool = False
    external_parties_involved: bool = False
    sensitive_data_involved: bool = False
    medical_reason: bool = False
    cross_border_work: bool = False
    public_official_involved: bool = False
    cash_gift: bool = False
    alcohol_mentioned: bool = False
    approval_status: str | None = None
    duration: str | None = None
    data_types: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


def _pydantic_to_facts(model: ParsedScenarioOutput) -> dict:
    return model.model_dump(exclude_none=True)


def merge_parsed_facts(heuristic: dict, llm_facts: dict) -> dict:
    """Merge heuristic and LLM facts; heuristic wins on explicit numeric fields."""
    merged = dict(heuristic)
    for key, value in llm_facts.items():
        if key in {"amount", "currency", "gift_value"} and heuristic.get(key) not in (None, ""):
            continue
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        merged[key] = value
    if merged.get("amount") is not None and merged.get("gift_value") is None:
        merged["gift_value"] = merged["amount"]
    return merged


def parse_scenario_with_llm(
    user_query: str,
    conversation_history: list[dict] | None = None,
    previous_scenario_facts: dict | None = None,
    heuristic_facts: dict | None = None,
) -> dict:
    """Parse scenario facts using heuristics plus optional LLM enrichment."""
    heuristic = heuristic_facts or parse_scenario_tool(user_query)
    heuristic = merge_follow_up_facts(heuristic, user_query)
    if previous_scenario_facts:
        from agent.memory import merge_scenario_facts

        heuristic = merge_scenario_facts(previous_scenario_facts, heuristic)

    warnings: list[str] = []
    if not USE_LLM_PARSER:
        return {"facts": heuristic, "parser_mode": "heuristic", "warnings": warnings}

    try:
        validate_api_key()
    except SystemExit:
        warnings.append("LLM parser skipped: API key unavailable.")
        return {"facts": heuristic, "parser_mode": "heuristic", "warnings": warnings}

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        history_text = ""
        if conversation_history:
            lines = []
            for message in conversation_history[-6:]:
                role = message.get("role", "user")
                content = (message.get("content") or "").strip()
                if content:
                    lines.append(f"{role}: {content}")
            history_text = "\n".join(lines)

        system_prompt = (
            "Extract structured workplace policy scenario facts from the user message. "
            "Return only factual fields supported by the text. Do not make a policy decision."
        )
        user_prompt = json.dumps(
            {
                "user_query": user_query,
                "conversation_history": history_text,
                "previous_scenario_facts": previous_scenario_facts or {},
                "heuristic_facts": heuristic,
            },
            indent=2,
        )

        llm = ChatOpenAI(model=LLM_PARSER_MODEL, temperature=0)
        structured_llm = llm.with_structured_output(ParsedScenarioOutput)
        result = structured_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        )
        llm_facts = _pydantic_to_facts(result)
        merged = merge_parsed_facts(heuristic, llm_facts)
        return {"facts": merged, "parser_mode": "hybrid", "warnings": warnings}
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"LLM parser fallback used: {exc}")
        return {"facts": heuristic, "parser_mode": "heuristic", "warnings": warnings}


def hybrid_parse_scenario(
    user_query: str,
    conversation_history: list[dict] | None = None,
    previous_scenario_facts: dict | None = None,
) -> dict[str, Any]:
    """Convenience wrapper used by workflow nodes."""
    heuristic = parse_scenario_tool(user_query)
    return parse_scenario_with_llm(
        user_query=user_query,
        conversation_history=conversation_history,
        previous_scenario_facts=previous_scenario_facts,
        heuristic_facts=heuristic,
    )
