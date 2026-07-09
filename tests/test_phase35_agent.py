"""Phase 3.5 PolicyOps Agent tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agent.answer_formatter import format_final_answer
from agent.answer_routing import classify_answer_type
from agent.graph import run_policy_agent_graph
from agent.policy_rule_extractor import extract_policy_rules, select_rules_for_scenario
from agent.tools import filter_redundant_open_questions, missing_info_tool


def _mock_chunk(section_id: str, text: str | None = None, source: str = "acme_remote_work_policy.md", score: float = 0.82):
    return {
        "text": text or f"{section_id} says remote work requires manager approval for extended periods.",
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


class AnswerRoutingTest(unittest.TestCase):
    def test_wfh_question_is_policy_explanation(self) -> None:
        answer_type = classify_answer_type(
            "What is the work from home policy?",
            "policy_question",
            {"policy_area": "remote_work"},
        )
        self.assertEqual(answer_type, "policy_explanation")

    def test_vendor_gift_is_scenario_decision(self) -> None:
        answer_type = classify_answer_type(
            "Can I accept an INR 5,000 gift from a vendor?",
            "policy_scenario",
            {"policy_area": "gifts_hospitality", "amount": 5000},
        )
        self.assertEqual(answer_type, "scenario_decision")


class PolicyRuleExtractorTest(unittest.TestCase):
    def test_extract_rules_from_chunks(self) -> None:
        chunks = [
            _mock_chunk("GH-003", "Gifts above INR 5,000 must be reported to Compliance."),
            _mock_chunk("GH-004", "Cash gifts are not allowed."),
        ]
        rules = extract_policy_rules(chunks)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0]["section_id"], "GH-003")

    def test_select_rules_for_gift_scenario(self) -> None:
        rules = extract_policy_rules([_mock_chunk("GH-003"), _mock_chunk("RW-003")])
        selected = select_rules_for_scenario(
            rules,
            {"policy_area": "gifts_hospitality", "gift_value": 5000},
        )
        self.assertTrue(any(rule["section_id"] == "GH-003" for rule in selected))


class OpenQuestionFilterTest(unittest.TestCase):
    def test_skips_manager_approval_when_already_approved(self) -> None:
        filtered = filter_redundant_open_questions(
            ["manager approval", "remote work duration"],
            {"approval_status": "approved", "duration": "2 weeks"},
        )
        self.assertNotIn("manager approval", filtered)
        self.assertNotIn("remote work duration", filtered)

    def test_missing_info_tool_respects_answer_type(self) -> None:
        result = missing_info_tool(
            "What is the work from home policy?",
            {"policy_area": "remote_work"},
            [_mock_chunk("RW-001")],
            answer_type="policy_explanation",
        )
        self.assertEqual(result["open_questions"], [])


class FormatterTest(unittest.TestCase):
    def test_policy_explanation_formatter_uses_topic(self) -> None:
        answer = format_final_answer(
            {
                "answer_type": "policy_explanation",
                "explanation_title": "Work from home / remote work",
                "confidence": 0.72,
                "rationale_bullets": ["RW-003 says extended remote work needs manager approval."],
                "policy_basis": [
                    {
                        "section_id": "RW-003",
                        "section_title": "Extended remote work",
                        "rule_summary": "Manager approval is required for more than 5 business days.",
                    }
                ],
                "merged_scenario_facts": {"policy_area": "remote_work"},
                "next_steps": [],
                "verified_citations": [],
            }
        )
        self.assertIn("Topic: Work from home / remote work", answer)
        self.assertIn("Policy basis:", answer)
        self.assertNotIn("Decision:", answer)


class LangGraphPhase35Test(unittest.TestCase):
    @patch("agent.tools.get_vectorstore")
    def test_policy_explanation_path(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [_mock_chunk("RW-001"), _mock_chunk("RW-003"), _mock_chunk("RW-030")]
        )
        state = run_policy_agent_graph("What is the work from home policy?")
        self.assertEqual(state.get("answer_type"), "policy_explanation")
        self.assertIn("Topic:", state.get("final_answer", ""))
        step_names = [step.get("step_name") for step in state.get("trace", [])]
        self.assertIn("classify_answer_type", step_names)
        self.assertIn("extract_policy_rules", step_names)
        self.assertIn("build_policy_explanation", step_names)

    @patch("agent.tools.get_vectorstore")
    def test_5k_gift_allowed_with_reporting_language(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(
            [
                _mock_chunk(
                    "GH-003",
                    "Gifts above INR 5,000 must be reported to Compliance and recorded in the gift register.",
                    source="acme_gifts_hospitality_policy.md",
                )
            ]
        )
        state = run_policy_agent_graph("Can I accept an INR 5,000 gift from a vendor?")
        self.assertEqual(state.get("answer_type"), "scenario_decision")
        self.assertIn(state.get("policy_decision"), {"Allowed", "Needs approval", "Needs more information"})
        self.assertTrue(state.get("policy_basis") or state.get("rationale_bullets"))


if __name__ == "__main__":
    unittest.main()
