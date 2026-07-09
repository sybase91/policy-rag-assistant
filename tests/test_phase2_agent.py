"""Phase 2 / 2.5 PolicyOps Agent tests with mocked retrieval."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agent.answer_formatter import format_final_answer
from agent.citation_verifier import clean_excerpt, verify_citations
from agent.graph import run_policy_agent
from agent.state import create_initial_state
from agent.tools import parse_scenario_tool


def _mock_chunk(
    section_id: str,
    source: str = "acme_travel_expense_policy.md",
    score: float = 0.82,
    text: str | None = None,
) -> dict:
    body = text or f"## {section_id} Example Section\nPolicy text for {section_id}."
    return {
        "text": body,
        "source": source,
        "section": f"{section_id} Example Section",
        "section_id": section_id,
        "score": score,
    }


def _mock_vectorstore(chunks: list[dict]) -> MagicMock:
    """Build a mock vectorstore that returns LangChain-like docs."""
    docs = []
    for chunk in chunks:
        doc = MagicMock()
        doc.page_content = chunk["text"]
        doc.metadata = {
            "source_file": chunk["source"],
            "section_id": chunk.get("section_id"),
            "section_title": chunk["section"].split(" ", 1)[-1],
        }
        distance = 1.0 - float(chunk.get("score", 0.8))
        docs.append((doc, distance))

    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = docs
    return vectorstore


MOCK_REIMBURSEMENT_CHUNKS = [
    _mock_chunk("TE-004", "acme_travel_expense_policy.md"),
    _mock_chunk("TE-006", "acme_travel_expense_policy.md"),
    _mock_chunk("RE-005", "acme_reimbursement_policy.md"),
]

MOCK_GIFT_CHUNKS = [
    _mock_chunk("GH-003", "acme_gifts_hospitality_policy.md", text="## GH-003 Gift Value Thresholds\nGifts above INR 10,000 require manager and Compliance approval."),
    _mock_chunk("GH-006", "acme_gifts_hospitality_policy.md", text="## GH-006 Gift Register\nRecord gifts in the gift register."),
]

MOCK_REMOTE_CHUNKS = [
    _mock_chunk("RW-003", "acme_remote_work_policy.md"),
    _mock_chunk("AM-002", "acme_approval_matrix.md"),
]

MOCK_DATA_ACCESS_CHUNKS = [
    _mock_chunk("DA-003", "acme_data_access_policy.md"),
    _mock_chunk("DA-005", "acme_data_access_policy.md"),
]


class ClientDinnerReimbursementTest(unittest.TestCase):
    """Client dinner INR 18,000 reimbursement scenario."""

    @patch("agent.tools.get_vectorstore")
    def test_client_dinner_scenario(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(MOCK_REIMBURSEMENT_CHUNKS)
        query = (
            "Can I reimburse a client dinner for INR 18,000 if two external guests "
            "attended and I paid with my own card?"
        )
        state = run_policy_agent(query, use_langgraph=False)

        self.assertEqual(state["intent"], "reimbursement_check")
        self.assertIn(
            state["policy_decision"],
            {"Needs approval", "Needs more information"},
        )
        self.assertIn("Manager", state.get("required_approvals", []))
        self.assertTrue(state.get("open_questions"))
        self.assertLess(len(state["final_answer"].split()), 600)
        self.assertIn("Short answer:", state["final_answer"])


class VendorGiftTest(unittest.TestCase):
    """INR 12,000 vendor gift scenario."""

    @patch("agent.tools.get_vectorstore")
    def test_vendor_gift_scenario(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(MOCK_GIFT_CHUNKS)
        query = "Can I accept a INR 12,000 gift from a vendor?"
        state = run_policy_agent(query, use_langgraph=False)

        self.assertEqual(state["scenario_facts"].get("amount"), 12000.0)
        self.assertIn(
            state["policy_decision"],
            {"Needs approval", "Escalate"},
        )
        self.assertNotEqual(state["policy_decision"], "Needs more information")
        approvals = " ".join(state.get("required_approvals", []))
        self.assertTrue(
            "Compliance" in approvals or "Manager" in approvals,
            msg="Expected Manager or Compliance in required approvals",
        )
        self.assertTrue(state.get("open_questions"))
        self.assertLess(len(state["final_answer"].split()), 600)


class MedicalRemoteWorkTest(unittest.TestCase):
    """Medical remote work for two weeks."""

    @patch("agent.tools.get_vectorstore")
    def test_medical_remote_work(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(MOCK_REMOTE_CHUNKS)
        query = "Am I allowed to work from home for two weeks because of a medical reason?"
        state = run_policy_agent(query, use_langgraph=False)

        combined = (
            state["final_answer"].lower()
            + " "
            + " ".join(state.get("required_approvals", [])).lower()
        )
        self.assertTrue("approval" in combined or "hr" in combined)


class CustomerDataVendorTest(unittest.TestCase):
    """Customer data shared with external vendor."""

    @patch("agent.tools.get_vectorstore")
    def test_customer_data_external_vendor(self, mock_get_vectorstore: MagicMock) -> None:
        mock_get_vectorstore.return_value = _mock_vectorstore(MOCK_DATA_ACCESS_CHUNKS)
        query = "Can I share customer data with an external vendor for analysis?"
        state = run_policy_agent(query, use_langgraph=False)

        self.assertIn(state["risk_level"], {"Medium", "High"})
        self.assertIn(state["policy_decision"], {"Needs approval", "Escalate"})
        approvals = " ".join(state.get("required_approvals", []))
        self.assertTrue(
            any(
                team in approvals
                for team in ("Information Security", "Legal", "Compliance")
            )
        )


class ParseScenarioToolTest(unittest.TestCase):
    """Unit tests for scenario parsing heuristics."""

    def test_inr_amount_extraction(self) -> None:
        facts = parse_scenario_tool("Client dinner for ₹18,000 with personal card")
        self.assertEqual(facts.get("amount"), 18000.0)
        self.assertEqual(facts.get("currency"), "INR")

    def test_usd_amount_extraction(self) -> None:
        facts = parse_scenario_tool("Hotel upgrade cost USD 500")
        self.assertEqual(facts.get("amount"), 500.0)
        self.assertEqual(facts.get("currency"), "USD")


class CitationVerifierTest(unittest.TestCase):
    """Citation verification must not invent sections."""

    def test_only_retrieved_sections_are_cited(self) -> None:
        retrieved = [_mock_chunk("TE-004"), _mock_chunk("RE-005")]
        result = verify_citations(
            {"decision": "Needs approval", "rationale_bullets": ["rule one", "rule two"]},
            retrieved,
        )
        cited_ids = {
            citation.get("section_id")
            for citation in result["verified_citations"]
            if citation.get("section_id")
        }
        self.assertTrue(cited_ids.issubset({"TE-004", "RE-005"}))
        self.assertNotIn("GH-999", cited_ids)

    def test_clean_excerpt_strips_headings_and_truncates(self) -> None:
        text = "## GH-003 Gift Value Thresholds\n\n" + ("A" * 300)
        excerpt = clean_excerpt(text, max_chars=80)
        self.assertNotIn("##", excerpt)
        self.assertLessEqual(len(excerpt), 80)
        self.assertTrue(excerpt.endswith("..."))


class FinalAnswerFormatterTest(unittest.TestCase):
    """Structured final answer formatting."""

    def test_includes_decision_and_disclaimer(self) -> None:
        state = create_initial_state("test query")
        state["policy_decision"] = "Needs approval"
        state["risk_level"] = "Medium"
        state["confidence"] = 0.75
        state["rationale_bullets"] = ["Manager approval is required."]
        state["open_questions"] = ["whether alcohol was included"]
        state["verified_citations"] = [_mock_chunk("TE-004")]
        answer = format_final_answer(state)
        self.assertIn("Decision: Needs approval", answer)
        self.assertIn("Short answer:", answer)
        self.assertIn("Open questions:", answer)
        self.assertIn("Disclaimer:", answer)


if __name__ == "__main__":
    unittest.main()
