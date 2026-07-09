"""Phase 3 PolicyOps Agent tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.graph import run_policy_agent, run_policy_agent_graph
from agent.llm_parser import parse_scenario_with_llm
from agent.memory import merge_scenario_facts
from agent.citation_verifier import verify_citations
from evals.run_agent_evals import run_evals

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "evals" / "latest_eval_results.json"


def _mock_chunk(section_id: str, source: str = "acme_gifts_hospitality_policy.md", score: float = 0.82):
    return {
        "text": f"Policy text for {section_id}.",
        "source": source,
        "section": f"{section_id} Example Section",
        "section_id": section_id,
        "score": score,
    }


def _mock_vectorstore(chunks: list[dict]) -> MagicMock:
    docs = []
    for chunk in chunks:
        doc = MagicMock()
        doc.page_content = chunk["text"]
        doc.metadata = {
            "source_file": chunk["source"],
            "section_id": chunk.get("section_id"),
            "section_title": "Example",
        }
        docs.append((doc, 1.0 - float(chunk.get("score", 0.8))))
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = docs
    return vectorstore


class LangGraphRunnerTest(unittest.TestCase):
    @patch("agent.tools.get_vectorstore")
    def test_langgraph_runner_returns_final_answer(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [_mock_chunk("GH-003"), _mock_chunk("GH-006")]
        )
        state = run_policy_agent_graph("Can I accept an INR 12,000 gift from a vendor?")
        self.assertIn("final_answer", state)
        self.assertTrue(state["final_answer"])
        step_names = [step.get("step_name") for step in state.get("trace", [])]
        self.assertIn("hybrid_parse_scenario", step_names)
        self.assertIn("save_thread_memory", step_names)


class LLMParserFallbackTest(unittest.TestCase):
    @patch("agent.llm_parser.validate_api_key", side_effect=SystemExit)
    def test_llm_parser_falls_back_to_heuristic(self, _mock_key) -> None:
        result = parse_scenario_with_llm("Can I accept an INR 12,000 gift from a vendor?")
        self.assertEqual(result["parser_mode"], "heuristic")
        self.assertEqual(result["facts"].get("amount"), 12000.0)


class MemoryMergeTest(unittest.TestCase):
    def test_merge_follow_up_facts(self) -> None:
        previous = {
            "policy_area": "gifts_hospitality",
            "amount": 12000.0,
            "currency": "INR",
            "vendor_or_client_involved": True,
        }
        from agent.tools import merge_follow_up_facts

        new = merge_follow_up_facts({}, "It is not cash and no public official is involved.")
        merged = merge_scenario_facts(previous, new)
        self.assertFalse(merged.get("cash_gift", True))
        self.assertFalse(merged.get("public_official_involved", True))

    @patch("agent.tools.get_vectorstore")
    def test_follow_up_turn_updates_open_questions(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [_mock_chunk("GH-003"), _mock_chunk("GH-006")]
        )
        first = run_policy_agent(
            "Can I accept an INR 12,000 gift from a vendor?",
            use_langgraph=True,
        )
        second = run_policy_agent(
            "It is not cash and no public official is involved.",
            conversation_history=[
                {"role": "user", "content": "Can I accept an INR 12,000 gift from a vendor?"},
                {"role": "assistant", "content": first["final_answer"], "metadata": {"agent_state": first}},
            ],
            previous_state=first,
            use_langgraph=True,
        )
        self.assertIn(second["policy_decision"], {"Needs approval", "Escalate"})
        self.assertFalse(second["scenario_facts"].get("cash_gift", True))


class DecisionCalibrationRegressionTest(unittest.TestCase):
    @patch("agent.tools.get_vectorstore")
    def test_vendor_gift_still_needs_approval(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [_mock_chunk("GH-003"), _mock_chunk("GH-006")]
        )
        state = run_policy_agent("Can I accept an INR 12,000 gift from a vendor?", use_langgraph=True)
        self.assertIn(state["policy_decision"], {"Needs approval", "Escalate"})

    @patch("agent.tools.get_vectorstore")
    def test_data_vendor_escalates_or_needs_approval(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [_mock_chunk("DA-003", "acme_data_access_policy.md"), _mock_chunk("DA-005", "acme_data_access_policy.md")]
        )
        state = run_policy_agent(
            "Can I share customer data with an external vendor for analysis?",
            use_langgraph=True,
        )
        self.assertIn(state["policy_decision"], {"Needs approval", "Escalate"})


class CitationVerifierRegressionTest(unittest.TestCase):
    def test_citations_subset_of_retrieved(self) -> None:
        retrieved = [_mock_chunk("GH-003"), _mock_chunk("GH-006")]
        result = verify_citations(
            {"decision": "Needs approval", "rationale_bullets": ["one"]},
            retrieved,
        )
        cited = {item.get("section_id") for item in result["verified_citations"]}
        self.assertTrue(cited.issubset({"GH-003", "GH-006"}))


class EvalRunnerTest(unittest.TestCase):
    def test_eval_runner_completes(self) -> None:
        payload = run_evals(use_langgraph=True)
        self.assertIn("metrics", payload)
        self.assertGreater(payload["metrics"]["total_cases"], 0)
        self.assertTrue(RESULTS_PATH.exists())
        saved = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        self.assertIn("decision_accuracy", saved["metrics"])


if __name__ == "__main__":
    unittest.main()
