"""Phase 4 quality audit tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from evals.phase4_audit_metrics import (
    detect_failure_modes,
    generate_failure_mode_report,
    score_phase4_case,
    sections_hit,
)
from evals.run_phase4_quality_audit import run_phase4_audit

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "evals" / "phase4_quality_questions.json"


class Phase4QuestionsTest(unittest.TestCase):
    def test_question_suite_has_75_cases(self) -> None:
        cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 75)
        categories = {case["category"] for case in cases}
        self.assertIn("policy_explanation", categories)
        self.assertIn("standard_rag", categories)
        self.assertIn("multi_turn_memory", categories)


class Phase4MetricsTest(unittest.TestCase):
    def test_section_prefix_match(self) -> None:
        state = {
            "verified_citations": [{"section_id": "GH-003"}],
            "final_answer": "",
            "policy_basis": [],
        }
        self.assertTrue(sections_hit(["GH"], state))

    def test_generic_answer_detection(self) -> None:
        case = {
            "mode": "policyops_agent",
            "category": "gifts_hospitality",
            "failure_modes_to_check": ["generic_answer"],
        }
        state = {
            "final_answer": "You can likely proceed under policy evidence suggests.",
            "policy_basis": [],
            "rationale_bullets": [],
        }
        modes = detect_failure_modes(case, state)
        self.assertIn("generic_answer", modes)

    def test_standard_rag_policyops_confusion(self) -> None:
        case = {"mode": "standard_rag", "failure_modes_to_check": ["standard_rag_policyops_confusion"]}
        state = {"final_answer": "Decision: Allowed\nRisk level: Low"}
        modes = detect_failure_modes(case, state)
        self.assertIn("standard_rag_policyops_confusion", modes)

    def test_report_generation(self) -> None:
        results = [
            {
                "id": "test_case",
                "turns": ["test"],
                "score": {
                    "passed": False,
                    "score": 50,
                    "failure_modes": ["wrong_decision"],
                    "expected": {"decision": "Escalate"},
                    "actual": {"decision": "Allowed"},
                },
            }
        ]
        metrics = {"total_cases": 1, "passed": 0, "failed": 1, "average_score": 50, "pass_rate": 0.0, "top_failure_mode": "wrong_decision", "failure_mode_counts": {"wrong_decision": 1}}
        report = generate_failure_mode_report(results, metrics)
        self.assertIn("Phase 4 Failure Mode Audit", report)
        self.assertIn("wrong_decision", report)


class Phase4AuditRunnerTest(unittest.TestCase):
    @patch("evals.run_phase4_quality_audit.run_policy_agent_graph")
    def test_mock_audit_smoke(self, mock_graph: MagicMock) -> None:
        mock_graph.return_value = {
            "final_answer": "GH-003 says gifts above INR 10,000 need Manager and Compliance approval.",
            "answer_type": "scenario_decision",
            "policy_decision": "Needs approval",
            "policy_basis": [{"section_id": "GH-003", "rule_summary": "threshold"}],
            "required_approvals": ["Manager", "Compliance"],
            "verified_citations": [{"section_id": "GH-003"}],
            "retrieved_chunks": [{"section_id": "GH-003", "text": "GH-003 policy"}],
            "open_questions": [],
            "rationale_bullets": ["GH-003 threshold"],
            "merged_scenario_facts": {"amount": 12000},
        }
        payload = run_phase4_audit(use_mock=True, case_id="gift_12000_vendor")
        self.assertEqual(payload["metrics"]["total_cases"], 1)
        self.assertIn("results", payload)

    def test_score_phase4_case_pass(self) -> None:
        case = {
            "mode": "policyops_agent",
            "category": "gifts_hospitality",
            "expected_answer_type": "scenario_decision",
            "expected_decision": "Needs approval",
            "expected_sections_any": ["GH-003"],
            "must_include_concepts": ["Compliance"],
        }
        state = {
            "final_answer": "GH-003 says Manager and Compliance approval required for INR 10,000 gifts.",
            "answer_type": "scenario_decision",
            "policy_decision": "Needs approval",
            "policy_basis": [{"section_id": "GH-003", "rule_summary": "Compliance approval"}],
            "required_approvals": ["Manager", "Compliance"],
            "verified_citations": [{"section_id": "GH-003"}],
            "retrieved_chunks": [{"section_id": "GH-003", "text": "GH-003"}],
            "rationale_bullets": ["GH-003 threshold"],
            "open_questions": [],
        }
        result = score_phase4_case(case, state)
        self.assertGreaterEqual(result["score"], 80)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
