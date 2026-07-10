"""Run Phase 4 quality audit against comprehensive question suite."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.langgraph_workflow import run_policy_agent_graph
from agent.memory import serialize_agent_state_for_ui
from evals.eval_helpers import mock_vectorstore_for_case
from evals.phase4_audit_metrics import (
    aggregate_phase4_metrics,
    generate_failure_mode_report,
    score_phase4_case,
)

QUESTIONS_PATH = ROOT / "evals" / "phase4_quality_questions.json"
RESULTS_PATH = ROOT / "evals" / "phase4_quality_results.json"
REPORT_PATH = ROOT / "reports" / "phase4_failure_modes.md"


@contextmanager
def _optional_mock(case: dict, use_mock: bool):
    if not use_mock:
        yield
        return
    with patch("agent.tools.get_vectorstore") as mock_get_vectorstore:
        mock_get_vectorstore.return_value = mock_vectorstore_for_case(case)
        yield


def _run_policyops_case(case: dict, use_mock: bool) -> tuple[dict, list[dict]]:
    turn_states: list[dict] = []
    conversation_history: list[dict] = []
    previous_state: dict | None = None

    with _optional_mock(case, use_mock):
        for turn in case.get("turns", []):
            state = run_policy_agent_graph(
                turn,
                conversation_history=list(conversation_history),
                previous_state=previous_state,
            )
            turn_states.append(state)
            conversation_history.append({"role": "user", "content": turn})
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": state.get("final_answer", ""),
                    "metadata": {"agent_state": serialize_agent_state_for_ui(state)},
                }
            )
            previous_state = state

    return turn_states[-1], turn_states


def _run_standard_rag_case(case: dict) -> dict:
    try:
        from src.generate import answer_question
    except ImportError as exc:
        return {
            "final_answer": f"Standard RAG unavailable: {exc}",
            "mode": "standard_rag",
            "sources": [],
            "retrieved_chunks": [],
        }

    query = case.get("turns", [""])[-1]
    try:
        result = answer_question(query)
    except Exception as exc:  # noqa: BLE001
        return {
            "final_answer": f"Standard RAG error: {exc}",
            "mode": "standard_rag",
            "sources": [],
            "retrieved_chunks": [],
        }

    answer = result.get("answer", "")
    sources = result.get("sources", [])
    return {
        "final_answer": answer,
        "mode": "standard_rag",
        "sources": sources,
        "retrieved_chunks": [{"source": s} for s in sources],
        "verified_citations": [{"source": s} for s in sources],
    }


def run_phase4_audit(
    *,
    use_mock: bool = False,
    category: str | None = None,
    case_id: str | None = None,
    skip_standard_rag: bool = False,
) -> dict:
    """Execute Phase 4 quality audit and write results + report."""
    cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    if category:
        cases = [c for c in cases if c.get("category") == category]
    if case_id:
        cases = [c for c in cases if c.get("id") == case_id]
    if skip_standard_rag:
        cases = [c for c in cases if c.get("mode") != "standard_rag"]

    results: list[dict] = []
    for case in cases:
        mode = case.get("mode", "policyops_agent")
        if mode == "standard_rag":
            state = _run_standard_rag_case(case)
            turn_states = None
        else:
            state, turn_states = _run_policyops_case(case, use_mock=use_mock)

        score = score_phase4_case(case, state, turn_states)
        results.append(
            {
                "id": case["id"],
                "category": case.get("category"),
                "mode": mode,
                "turns": case.get("turns", []),
                "query": case.get("turns", [""])[-1],
                "score": score,
                "state_summary": {
                    "answer_type": state.get("answer_type"),
                    "policy_decision": state.get("policy_decision"),
                    "risk_level": state.get("risk_level"),
                    "confidence": state.get("confidence"),
                    "open_questions": state.get("open_questions", []),
                    "required_approvals": state.get("required_approvals", []),
                    "cited_sections": [
                        c.get("section_id") for c in (state.get("verified_citations") or [])
                    ],
                    "retrieved_count": len(state.get("retrieved_chunks") or []),
                },
            }
        )

    metrics = aggregate_phase4_metrics(results)
    if results and all(item["state_summary"].get("retrieved_count", 0) == 0 for item in results if item.get("mode") == "policyops_agent"):
        metrics["retrieval_warning"] = (
            "All PolicyOps cases returned zero retrieved chunks. "
            "Re-ingest with scripts/ingest_mock_policies.py --replace and verify OPENAI_API_KEY, "
            "or use --mock for offline runs."
        )
    payload = {
        "metrics": metrics,
        "config": {"use_mock": use_mock, "category": category, "case_id": case_id},
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(generate_failure_mode_report(results, metrics), encoding="utf-8")
    return payload


def _print_summary(payload: dict) -> None:
    metrics = payload["metrics"]
    print("Phase 4 Quality Audit Results")
    print(f"Total cases: {metrics.get('total_cases', 0)}")
    print(f"Passed: {metrics.get('passed', 0)}")
    print(f"Failed: {metrics.get('failed', 0)}")
    print(f"Average score: {metrics.get('average_score', 0)}")
    print(f"Pass rate: {metrics.get('pass_rate', 0):.1%}")
    print(f"Top failure mode: {metrics.get('top_failure_mode', 'none')}")
    if metrics.get("retrieval_warning"):
        print(f"\nWARNING: {metrics['retrieval_warning']}")

    print("\nFailure modes by frequency:")
    for mode, count in list(metrics.get("failure_mode_counts", {}).items())[:10]:
        print(f"  {mode}: {count}")

    failed = sorted(
        [item for item in payload["results"] if not item["score"]["passed"]],
        key=lambda item: item["score"]["score"],
    )
    print("\nWorst 10 cases:")
    for item in failed[:10]:
        modes = ", ".join(item["score"]["failure_modes"][:3]) or "none"
        print(f"  {item['id']} (score {item['score']['score']}): {modes}")

    print(f"\nSaved results to {RESULTS_PATH}")
    print(f"Saved report to {REPORT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 4 quality audit")
    parser.add_argument("--mock", action="store_true", help="Use mocked vectorstore retrieval")
    parser.add_argument("--category", type=str, default=None, help="Filter by category")
    parser.add_argument("--id", dest="case_id", type=str, default=None, help="Run single case by id")
    parser.add_argument(
        "--skip-standard-rag",
        action="store_true",
        help="Skip standard RAG cases (no API key needed)",
    )
    args = parser.parse_args()

    payload = run_phase4_audit(
        use_mock=args.mock,
        category=args.category,
        case_id=args.case_id,
        skip_standard_rag=args.skip_standard_rag,
    )
    _print_summary(payload)


if __name__ == "__main__":
    main()
