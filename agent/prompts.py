"""Placeholder prompt templates for future LLM-based agent steps."""

INTENT_CLASSIFICATION_PROMPT = """Classify the user request into one intent label.
Return only one of: policy_question, policy_scenario, approval_check,
reimbursement_check, compliance_check, unknown.

Phase 2 note: intent is still rules-based in code; this prompt is reserved for later."""

SCENARIO_EXTRACTION_PROMPT = """Extract structured scenario facts from the user request.
Return JSON with fields such as amount, currency, payment_method, policy_area,
people_involved, duration, approval_status, and documentation_provided when present.

Phase 2 note: scenario parsing is heuristic in code for predictability."""

POLICY_DECISION_PROMPT = """Using only retrieved policy context and extracted facts,
return a conservative policy decision with risk level, confidence, rationale bullets,
required approvals, and verified citations.

Phase 2 note: decision rules are deterministic in decision_rules.py."""

FINAL_ANSWER_PROMPT = """Write a concise final answer for the employee.
Include decision, summary, missing information, verified citations, next steps,
and a clarifying question when needed. Do not invent sources.

Phase 2 note: answer_formatter.py handles deterministic formatting today."""
