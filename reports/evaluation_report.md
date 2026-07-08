# RAG Evaluation Report (v0.1)

**Evaluation date/time:** 2026-07-08 18:36:11

## What was tested

This report covers a simple Phase 6 evaluation harness for the
Enterprise AI Policy RAG Assistant. For each gold question, the
script called `answer_question()` and scored:

- Whether the expected source PDF appeared in retrieved sources
- How many expected keywords appeared in the generated answer
- Whether unsupported questions were refused correctly

This is a **v0.1 / simple harness**. It is not RAGAS and not an
LLM-as-judge. It uses transparent rules so beginners can understand
and debug failures.

## Dataset size

- Total gold questions: **10**
- Answerable questions: **7**
- Refuse questions: **3**

## Metrics explained (beginner-friendly)

| Metric | Meaning |
|--------|---------|
| **Source hit rate** | Share of questions where the expected source check passed (for refuse/`none` rows: refusal text present). |
| **Keyword hit rate** | Average share of expected phrases found in answers (computed on answerable rows only). |
| **Refusal accuracy** | Share of refuse questions that included the exact grounded refusal message. |
| **Pass rate** | Share of questions that met the v0.1 pass rule. |

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 10 |
| Total passed | 9 |
| Pass rate | 90.00% |
| Source hit rate | 90.00% |
| Average keyword hit rate | 85.71% |
| Refusal accuracy | 100.00% |

## Failed cases

| ID | Expected behavior | Reason |
|----|-------------------|--------|
| q04 | answer | expected source not in retrieved sources; keyword_hit_rate 0.0 < 0.5 |

## Limitations

- Keyword matching is case-insensitive substring matching, not semantic.
- Source hit checks filename presence, not page-level citation quality.
- Refusal checks a fixed refusal string, not all valid refuse phrasings.
- Small gold set (10 questions); not statistically strong.
- No RAGAS / faithfulness / LLM-as-judge scoring yet.

## Next improvements

- Expand the gold set and add more refusal edge cases
- Add page-level citation checks
- Add retrieval-only metrics before generation
- Consider RAGAS or LLM-as-judge later for richer scoring
- Track evaluation history across model/prompt changes
