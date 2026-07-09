"""Run PolicyOps Agent evaluations against golden policy cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import run_policy_agent
from evals.eval_metrics import aggregate_metrics, score_case

GOLDEN_PATH = ROOT / "evals" / "golden_policy_cases.json"
RESULTS_PATH = ROOT / "evals" / "latest_eval_results.json"


def _mock_chunk(section_id: str, source: str = "acme_policy.md", score: float = 0.84) -> dict:
    return {
        "text": f"Policy text for {section_id}.",
        "source": source,
        "section": f"{section_id} Example Section",
        "section_id": section_id,
        "score": score,
    }


def _mock_vectorstore_for_case(case: dict) -> MagicMock:
    sections = case.get("must_cite_sections")
    if sections is None:
        sections = ["GH-003"]
    if not sections:
        chunks = []
    else:
        chunks = [_mock_chunk(section_id) for section_id in sections]
    docs = []
    for chunk in chunks:
        doc = MagicMock()
        doc.page_content = chunk["text"]
        doc.metadata = {
            "source_file": chunk["source"],
            "section_id": chunk["section_id"],
            "section_title": "Example",
        }
        distance = 1.0 - float(chunk["score"])
        docs.append((doc, distance))
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = docs
    return vectorstore


def run_evals(use_langgraph: bool = True) -> dict:
    """Execute all golden cases and return aggregated results."""
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    results: list[dict] = []

    for case in cases:
        with patch("agent.tools.get_vectorstore") as mock_get_vectorstore:
            mock_get_vectorstore.return_value = _mock_vectorstore_for_case(case)
            state = run_policy_agent(
                case["query"],
                use_langgraph=use_langgraph,
            )
        checks = score_case(case, state)
        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected": {
                    "decision": case.get("expected_decision"),
                    "risk_level": case.get("expected_risk_level"),
                    "required_approvals": case.get("expected_required_approvals", []),
                    "must_cite_sections": case.get("must_cite_sections", []),
                },
                "actual": {
                    "decision": state.get("policy_decision"),
                    "risk_level": state.get("risk_level"),
                    "required_approvals": state.get("required_approvals", []),
                    "open_questions": state.get("open_questions", []),
                    "confidence": state.get("confidence"),
                },
                "checks": checks,
                "state": {
                    "policy_decision": state.get("policy_decision"),
                    "risk_level": state.get("risk_level"),
                    "confidence": state.get("confidence"),
                    "required_approvals": state.get("required_approvals", []),
                    "open_questions": state.get("open_questions", []),
                    "verified_citations": state.get("verified_citations", []),
                    "retrieved_chunks": state.get("retrieved_chunks", []),
                    "final_answer": state.get("final_answer", ""),
                },
            }
        )

    metrics = aggregate_metrics(results)
    payload = {"metrics": metrics, "results": results}
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    payload = run_evals(use_langgraph=True)
    metrics = payload["metrics"]
    print("PolicyOps Agent Evaluation Results")
    print(f"Total cases: {metrics['total_cases']}")
    print(f"Pass rate: {metrics['pass_rate']:.1%}")
    print(f"Decision accuracy: {metrics['decision_accuracy']:.1%}")
    print(f"Risk accuracy: {metrics['risk_level_accuracy']:.1%}")
    print(f"Citation hit rate: {metrics['must_cite_hit_rate']:.1%}")
    print(f"Retrieval hit rate: {metrics['retrieval_hit_rate']:.1%}")
    print(f"Approval match rate: {metrics['required_approval_match']:.1%}")
    print(f"Average confidence: {metrics['average_confidence']:.2f}")

    failed = [item for item in payload["results"] if not item["checks"]["passed"]]
    if failed:
        print("\nFailed cases:")
        for item in failed[:8]:
            print(
                f"- {item['id']}: expected decision {item['expected']['decision']}, "
                f"got {item['actual']['decision']}"
            )
    print(f"\nSaved results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
