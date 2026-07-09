"""Placeholder prompt templates for future LLM-based agent steps."""

INTENT_CLASSIFICATION_PROMPT = """Classify the user request into one intent label.
Return only one of: policy_question, policy_scenario, approval_check,
reimbursement_check, compliance_check, unknown."""

SCENARIO_EXTRACTION_PROMPT = """Extract structured scenario facts from the user request.
Return JSON with fields such as amount, currency, payment_method, policy_area,
people_involved, duration, and approval_status when present."""

POLICY_DECISION_PROMPT = """Using only retrieved policy context and extracted facts,
return a conservative policy decision with risk level and confidence."""

FINAL_ANSWER_PROMPT = """Write a concise final answer for the employee.
Include decision, summary, missing information, cited policy sources, and next steps.
Do not invent policy sources."""
