# Phase 4 Failure Mode Audit

## Summary

- Total cases: 75
- Passed: 61
- Failed: 14
- Average score: 93.9
- Pass rate: 81.3%
- Top failure mode: `wrong_decision`

## Top Failure Modes

| Failure mode | Count | Severity | Example case | Recommended fix |
| --- | ---: | --- | --- | --- |
| wrong_decision | 13 | High | gift_cricket_tickets | Ground decision_rules.py in extracted policy rules and corpus thresholds. |
| low_grounding | 3 | Medium | gift_cumulative_quarter | Include must_include concepts from policy_basis and retrieved chunk text. |
| redundant_open_question | 2 | Medium | remote_2_weeks_approved | Tighten filter_redundant_open_questions in tools.py. |
| wrong_answer_type | 1 | Medium | explain_approval_matrix | Improve answer_routing.py patterns and ambiguity detection. |
| missing_expected_section | 1 | Medium | gift_cash_3000 | Improve retrieval query building and section ID matching in answers. |
| missing_required_approval | 1 | Medium | data_vendor_prod_logs | Align decision_rules required_approvals with AM matrix sections. |
| boundary_failure | 1 | High | rag_refund_policy | Return explicit no-policy-found response when corpus has no match. |

## Worst Failing Cases

| Case ID | Question | Expected | Actual | Failure modes |
| --- | --- | --- | --- | --- |
| rag_refund_policy | What is my company's refund policy? | n/a | n/a | boundary_failure |
| gift_cricket_tickets | A vendor offered me tickets to a cricket match but they will not attend. Can ... | ['Needs approval', 'Escalate', 'Needs more information'] | Allowed | wrong_decision |
| travel_alcohol | Can I reimburse alcohol from a client dinner? | ['Needs approval', 'Not allowed'] | Needs more information | wrong_decision |
| travel_personal_card_ok | I paid for a client meal with my personal card. Is that okay? | ['Allowed', 'Needs approval'] | Needs more information | wrong_decision |
| reimb_late_100_days | I submitted an expense 100 days late. Can I still claim it? | ['Needs approval', 'Not allowed', 'Needs more information'] | Allowed | wrong_decision |
| reimb_duplicate_taxi | Can I submit the same taxi expense twice if the first one was rejected? | ['Not allowed', 'Needs approval'] | Needs more information | wrong_decision |
| reimb_personal_purchase | Can I claim a personal purchase if I used it during work? | ['Not allowed', 'Needs approval'] | Allowed | wrong_decision |
| data_hr_vendor | Can I send employee HR data to an external analytics vendor? | Escalate | Needs approval | wrong_decision |
| data_finance_access | Can I access finance reports if I am not on the Finance team? | Needs approval | Allowed | wrong_decision |
| data_already_sent | I already sent customer data to a vendor before Security approval. What shoul... | Escalate | Needs approval | wrong_decision |

## Product-Level Observations

- No dominant failure cluster; review worst failing cases individually.

## Recommended Phase 4 Build Plan

### Phase 4.1 Grounding and Rule Extraction Fixes
- missing_expected_section (1 cases): Improve retrieval query building and section ID matching in answers.
- low_grounding (3 cases): Include must_include concepts from policy_basis and retrieved chunk text.

### Phase 4.2 Intent and Answer-Type Routing
- wrong_answer_type (1 cases): Improve answer_routing.py patterns and ambiguity detection.

### Phase 4.3 Memory and Follow-Up Handling
- redundant_open_question (2 cases): Tighten filter_redundant_open_questions in tools.py.

### Phase 4.4 Safety and Boundary Handling
- boundary_failure (1 cases): Return explicit no-policy-found response when corpus has no match.


## Recommended Immediate Fixes

1. **wrong_decision** - Ground decision_rules.py in extracted policy rules and corpus thresholds.
2. **low_grounding** - Include must_include concepts from policy_basis and retrieved chunk text.
3. **redundant_open_question** - Tighten filter_redundant_open_questions in tools.py.
4. **wrong_answer_type** - Improve answer_routing.py patterns and ambiguity detection.
5. **missing_expected_section** - Improve retrieval query building and section ID matching in answers.
6. **missing_required_approval** - Align decision_rules required_approvals with AM matrix sections.
7. **boundary_failure** - Return explicit no-policy-found response when corpus has no match.

## Testing Commands

```bash
python evals/run_phase4_quality_audit.py
python evals/run_phase4_quality_audit.py --mock
python evals/run_agent_evals.py
python -m unittest tests.test_phase4_audit -v
```