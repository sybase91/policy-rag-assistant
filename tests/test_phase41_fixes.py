"""Phase 4.1 targeted regression tests for audit failure fixes."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agent.answer_routing import classify_answer_type
from agent.decision_rules import make_policy_decision
from agent.routing import route_after_missing_info
from agent.tools import missing_info_tool, parse_scenario_tool
from src.generate import REFUSAL_MESSAGE, _should_refuse_retrieval


class Phase41ParsingTest(unittest.TestCase):
    def test_cricket_tickets_sets_gifts_hospitality(self) -> None:
        facts = parse_scenario_tool(
            "Vendor invited me to cricket match tickets worth INR 12,000. Can I accept?"
        )
        self.assertEqual(facts["policy_area"], "gifts_hospitality")
        self.assertTrue(facts["vendor_hospitality"])

    def test_duplicate_claim_flag(self) -> None:
        facts = parse_scenario_tool("I submitted the same taxi expense twice by mistake.")
        self.assertTrue(facts["duplicate_claim"])

    def test_amount_last_wins_on_correction(self) -> None:
        facts = parse_scenario_tool(
            "Vendor gift worth INR 12,000, actually INR 8,000. Can I keep it?"
        )
        self.assertEqual(facts["amount"], 8000.0)

    def test_chatgpt_and_customer_data(self) -> None:
        facts = parse_scenario_tool(
            "Can I paste customer data into ChatGPT to draft an email?"
        )
        self.assertTrue(facts["public_ai_tool"])
        self.assertEqual(facts["policy_area"], "data_access")

    def test_finance_report_data_type(self) -> None:
        facts = parse_scenario_tool("I need access to finance reports for a project.")
        self.assertIn("finance data", facts["data_types"])


class Phase41RoutingTest(unittest.TestCase):
    def test_alcohol_routes_to_decide_without_amount(self) -> None:
        facts = parse_scenario_tool("Client dinner included alcohol. Is reimbursement allowed?")
        missing = missing_info_tool(facts["raw_query"], facts, [{"section_id": "TE-006", "score": 0.8}])
        self.assertNotIn("amount", missing["blocking_missing_info"])
        state = {
            "answer_type": "scenario_decision",
            "scenario_facts": facts,
            "merged_scenario_facts": facts,
            "blocking_missing_info": missing["blocking_missing_info"],
        }
        self.assertEqual(route_after_missing_info(state), "decide")

    def test_data_already_shared_escalates(self) -> None:
        facts = parse_scenario_tool(
            "I already sent HR data to a vendor before security approval."
        )
        state = {
            "answer_type": "scenario_decision",
            "scenario_facts": facts,
            "merged_scenario_facts": facts,
            "blocking_missing_info": [],
        }
        self.assertEqual(route_after_missing_info(state), "escalate")


class Phase41DecisionRulesTest(unittest.TestCase):
    def test_duplicate_claim_not_allowed(self) -> None:
        facts = parse_scenario_tool("I claimed the same taxi expense twice.")
        chunks = [{"section_id": "RE-011", "score": 0.8, "text": "RE-011 duplicate"}]
        result = make_policy_decision(facts, chunks, [])
        self.assertEqual(result["decision"], "Not allowed")

    def test_late_submission_over_90_days(self) -> None:
        facts = parse_scenario_tool("I submitted my expense 100 days late.")
        chunks = [{"section_id": "RE-019", "score": 0.8, "text": "RE-019 late"}]
        result = make_policy_decision(facts, chunks, [])
        self.assertIn(result["decision"], {"Not allowed", "Needs approval"})

    def test_vendor_hospitality_needs_approval(self) -> None:
        facts = parse_scenario_tool("Vendor sent cricket match tickets. Can I go?")
        chunks = [{"section_id": "GH-018", "score": 0.8, "text": "GH-018 hospitality"}]
        result = make_policy_decision(facts, chunks, [])
        self.assertEqual(result["decision"], "Needs approval")

    def test_gift_value_open_question_for_notebook(self) -> None:
        facts = parse_scenario_tool("Can I accept a small branded notebook from a vendor?")
        missing = missing_info_tool(facts["raw_query"], facts, [{"section_id": "GH-002", "score": 0.8}])
        joined = " ".join(missing["open_questions"] + missing["blocking_missing_info"]).lower()
        self.assertIn("gift value", joined)


class Phase41AnswerRoutingTest(unittest.TestCase):
    def test_approval_matrix_is_policy_explanation(self) -> None:
        answer_type = classify_answer_type(
            "Explain the approval matrix for gifts.",
            "policy_question",
            {"policy_area": "general"},
        )
        self.assertEqual(answer_type, "policy_explanation")


class Phase41RagBoundaryTest(unittest.TestCase):
    def test_refuse_low_similarity(self) -> None:
        doc = MagicMock()
        doc.metadata = {"source_file": "acme_reimbursement.md"}
        doc.page_content = "Travel reimbursement policy text."
        self.assertTrue(
            _should_refuse_retrieval("What is the refund policy?", [(doc, 0.2)])
        )

    def test_refuse_topic_mismatch(self) -> None:
        doc = MagicMock()
        doc.metadata = {"source_file": "acme_travel_expense.md"}
        doc.page_content = "Client meal reimbursement limits."
        self.assertTrue(
            _should_refuse_retrieval("What is the company refund policy?", [(doc, 0.9)])
        )

    @patch("src.generate.retrieve_context_with_scores")
    @patch("src.generate.validate_api_key")
    @patch("src.generate.ChatOpenAI")
    def test_answer_question_refuses_boundary_case(
        self, mock_llm: MagicMock, _mock_key: MagicMock, mock_retrieve: MagicMock
    ) -> None:
        from src.generate import answer_question

        doc = MagicMock()
        doc.metadata = {"source_file": "acme_reimbursement.md"}
        doc.page_content = "Reimbursement only."
        mock_retrieve.return_value = [(doc, 0.2)]
        result = answer_question("What is the refund policy?")
        self.assertEqual(result["answer"], REFUSAL_MESSAGE)
        mock_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
