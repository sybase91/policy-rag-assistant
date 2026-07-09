"""Evaluation metrics for PolicyOps Agent golden cases."""

from __future__ import annotations


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def decision_accuracy(expected, actual) -> bool:
    return actual in _as_list(expected)


def risk_level_accuracy(expected, actual) -> bool:
    return actual in _as_list(expected)


def required_approval_match(expected, actual) -> bool:
    expected_set = {item.lower() for item in _as_list(expected)}
    actual_set = {item.lower() for item in _as_list(actual or [])}
    if not expected_set:
        return True
    return bool(expected_set & actual_set)


def citation_presence(state: dict, required_sections: list[str] | None = None) -> bool:
    if required_sections is not None and len(required_sections) == 0:
        return True
    return bool(state.get("verified_citations") or state.get("citations"))


def must_cite_hit_rate(required_sections: list[str], state: dict) -> bool:
    if not required_sections:
        return True
    cited_ids = {
        (citation.get("section_id") or "")
        for citation in (state.get("verified_citations") or state.get("citations") or [])
    }
    return any(section in cited_ids for section in required_sections)


def open_question_relevance(expected_keywords: list[str], state: dict) -> bool:
    if not expected_keywords:
        return True
    blob = " ".join(state.get("open_questions", [])).lower()
    blob += " " + (state.get("final_answer") or "").lower()
    return any(keyword.lower() in blob for keyword in expected_keywords)


def retrieval_hit_rate(state: dict) -> bool:
    return len(state.get("retrieved_chunks", [])) > 0


def final_answer_non_empty(state: dict) -> bool:
    return bool((state.get("final_answer") or "").strip())


def escalation_precision(case: dict, state: dict) -> bool:
    """Pass unless the agent escalates when Escalate is not an allowed outcome."""
    expected = _as_list(case.get("expected_decision", []))
    actual = state.get("policy_decision")
    if actual != "Escalate":
        return True
    return "Escalate" in expected


def score_case(case: dict, state: dict) -> dict:
    """Score one golden case against an agent state."""
    checks = {
        "decision_accuracy": decision_accuracy(case.get("expected_decision"), state.get("policy_decision")),
        "risk_level_accuracy": risk_level_accuracy(case.get("expected_risk_level"), state.get("risk_level")),
        "required_approval_match": required_approval_match(
            case.get("expected_required_approvals", []), state.get("required_approvals", [])
        ),
        "citation_presence": citation_presence(state, case.get("must_cite_sections")),
        "must_cite_hit_rate": must_cite_hit_rate(case.get("must_cite_sections", []), state),
        "open_question_relevance": open_question_relevance(case.get("expected_open_questions", []), state),
        "retrieval_hit_rate": retrieval_hit_rate(state),
        "final_answer_non_empty": final_answer_non_empty(state),
        "escalation_precision": escalation_precision(case, state),
    }
    checks["passed"] = all(checks.values())
    return checks


def aggregate_metrics(results: list[dict]) -> dict:
    """Aggregate per-case scores into dashboard metrics."""
    total = len(results)
    if total == 0:
        return {"total_cases": 0}

    def rate(key: str) -> float:
        return round(sum(1 for item in results if item["checks"].get(key)) / total, 3)

    confidences = [float(item["state"].get("confidence", 0.0) or 0.0) for item in results]
    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

    return {
        "total_cases": total,
        "decision_accuracy": rate("decision_accuracy"),
        "risk_level_accuracy": rate("risk_level_accuracy"),
        "required_approval_match": rate("required_approval_match"),
        "citation_presence": rate("citation_presence"),
        "must_cite_hit_rate": rate("must_cite_hit_rate"),
        "open_question_relevance": rate("open_question_relevance"),
        "retrieval_hit_rate": rate("retrieval_hit_rate"),
        "final_answer_non_empty": rate("final_answer_non_empty"),
        "escalation_precision": rate("escalation_precision"),
        "average_confidence": avg_confidence,
        "pass_rate": round(sum(1 for item in results if item["checks"]["passed"]) / total, 3),
    }
