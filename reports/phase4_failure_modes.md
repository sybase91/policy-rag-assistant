# Phase 4 Failure Mode Audit

## Summary

- Total cases: 75
- Passed: 75
- Failed: 0
- Average score: 99.2
- Pass rate: 100.0%
- Top failure mode: `low_grounding`

## Top Failure Modes

| Failure mode | Count | Severity | Example case | Recommended fix |
| --- | ---: | --- | --- | --- |
| low_grounding | 4 | Medium | gift_cumulative_quarter | Include must_include concepts from policy_basis and retrieved chunk text. |
| missing_expected_section | 1 | Medium | gift_cash_3000 | Improve retrieval query building and section ID matching in answers. |

## Worst Failing Cases

| Case ID | Question | Expected | Actual | Failure modes |
| --- | --- | --- | --- | --- |

## Product-Level Observations

- No dominant failure cluster; review worst failing cases individually.

## Recommended Phase 4 Build Plan

### Phase 4.1 Grounding and Rule Extraction Fixes
- missing_expected_section (1 cases): Improve retrieval query building and section ID matching in answers.
- low_grounding (4 cases): Include must_include concepts from policy_basis and retrieved chunk text.


## Recommended Immediate Fixes

1. **low_grounding** - Include must_include concepts from policy_basis and retrieved chunk text.
2. **missing_expected_section** - Improve retrieval query building and section ID matching in answers.

## Testing Commands

```bash
python evals/run_phase4_quality_audit.py
python evals/run_phase4_quality_audit.py --mock
python evals/run_agent_evals.py
python -m unittest tests.test_phase4_audit -v
```