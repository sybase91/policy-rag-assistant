# PolicyOps Agent

## What This Project Is

Enterprise AI proof-of-work project demonstrating two assistant modes in one Streamlit app: **Standard RAG Chat** over public AI governance documents (NIST, OWASP), and **PolicyOps Agent** for scenario-based workplace policy review over a synthetic Acme Corp corpus. The agent uses LangGraph orchestration, multi-turn memory, policy rule extraction, deterministic decision rules, citation verification, and an evaluation harness with a Phase 4 quality audit loop.

## Demo Modes

| Mode | Use case | Output |
|------|----------|--------|
| Standard RAG Chat | Knowledge-base Q&A | Source-grounded answer with citations |
| PolicyOps Agent | Workplace policy scenario review | Decision (or policy explanation), policy basis, approvals, citations, trace |

## Architecture at a Glance

```text
Documents -> Chunks -> Embeddings -> Vector Store -> Retriever
  -> LangGraph Agent -> Policy Rule Extractor -> Decision Engine
  -> Citation Verifier -> Answer Formatter -> Eval Dashboard
```

## Phase Summary

| Phase | What was built | Key files |
|-------|----------------|-----------|
| 0 | Synthetic Acme policy corpus | `data/policies/mock/` |
| 1 | Agent foundation | `agent/state.py`, `agent/nodes.py` |
| 2 | Grounded decision engine | `agent/decision_rules.py` |
| 2.5 | Answer and citation UI cleanup | `agent/answer_formatter.py` |
| 3 | LangGraph, memory, golden evals | `agent/langgraph_workflow.py`, `evals/` |
| 3.5 | Corpus enrichment and grounded answers | `agent/policy_rule_extractor.py`, `agent/answer_routing.py` |
| 4 | Quality audit and failure-mode plan | `evals/run_phase4_quality_audit.py`, `reports/phase4_failure_modes.md` |
| 4.1 | Audit failure fixes (parsing, routing, rules, RAG boundary) | `tests/test_phase41_fixes.py`, `agent/decision_rules.py`, `src/generate.py` |

## Phase 4.1 — What Changed and Why

Phase 4.1 targeted the dominant audit failure mode: **`wrong_decision`** (13 cases at baseline). Live retrieval was working (`retrieved_count: 5` on failures); the problem was **fact extraction → routing → decision logic**, not empty Chroma.

```text
parse_scenario_tool  →  route_after_missing_info  →  decision_rules.py
        │                        │                           │
   missing flags          clarify-before-decide         general Allowed fallback
```

### Baseline vs after Phase 4.1

| Suite | Before | After (mock) | After (live, with API + ingest) |
|-------|--------|--------------|----------------------------------|
| Phase 4 audit (75 cases) | 61/75 (81.3%) | **75/75 (100%)** | Re-run after ingest (see below) |
| Golden evals (20 cases) | 17/20 (85%) | **20/20 (100%)** | Same |
| Top failure mode | `wrong_decision` (13) | `low_grounding` (9, non-blocking) | — |

### Root causes fixed

| Layer | Problem | Fix |
|-------|---------|-----|
| **Parsing** | Tickets, late claims, duplicates, ChatGPT, personal email, public links not extracted | 11+ heuristics in `parse_scenario_tool`; amount-last-wins on correction |
| **Routing** | Missing `amount` forced `provisional_clarify` → hard-coded NMI, skipping rules | Non-blocking amount when alcohol/duplicate/personal card/etc.; `can_decide_without_amount()` |
| **Decision rules** | `evaluate_general_policy_case` returned **Allowed** for flagged scenarios | Branches for gifts, reimbursement, data access, travel; narrowed general fallback |
| **Standard RAG** | Refund-policy questions answered from reimbursement chunks | Similarity threshold + topic-mismatch refusal in `src/generate.py` |
| **Golden evals** | `travel_002` decision on explanation; `ambig_001` empty mock; `gift_005` missing gift-value question | Eval alignment + `eval_helpers` fix + notebook/branded gift parser |

### Cases that were failing and now pass (mock audit)

`gift_cricket_tickets`, `travel_alcohol`, `travel_personal_card_ok`, `reimb_late_100_days`, `reimb_duplicate_taxi`, `reimb_personal_purchase`, `data_hr_vendor`, `data_finance_access`, `data_already_sent`, `data_chatgpt`, `data_personal_gmail`, `data_public_link`, `contradiction_gift_amount`, `rag_refund_policy`

### Remaining soft issues (passed but noted)

- **`low_grounding`** (9 cases) — rationale could include more `must_include_concepts` from chunk text (e.g. cumulative gifts).
- **`redundant_open_question`** (1 case) — multi-turn remote work still asks manager approval when already stated.

## Synthetic Acme Policy Corpus

Fictional Acme Corp policies for demo-safe RAG and agent evaluation (not legal, HR, finance, or compliance advice).

| Policy | Covers |
|--------|--------|
| Approval Matrix | Cross-functional approvals |
| Gifts and Hospitality | Thresholds, public officials, procurement blackout |
| Travel and Expense | Meals, lodging, alcohol, upgrades |
| Reimbursement | Claims, receipts, late submissions |
| Remote Work | Short-term, medical, cross-border |
| Data Access | Classification, external sharing, AI tools |

Re-ingest after corpus edits:

```bash
python scripts/ingest_mock_policies.py --replace
```

## How It Works

1. Policy documents are ingested into Chroma with section-level metadata.
2. The user asks a question in Standard RAG or PolicyOps mode.
3. PolicyOps classifies the answer type (explanation vs scenario decision).
4. The retriever finds relevant policy sections.
5. The policy rule extractor turns chunks into structured rules.
6. The decision engine applies deterministic rules to scenario facts.
7. The citation verifier ensures only retrieved sections are cited.
8. The answer formatter produces a readable response by answer type.
9. The eval dashboard and Phase 4 audit measure quality and failure modes.

## Key Technical Concepts

- **RAG** — Retrieve relevant chunks before answering instead of guessing from training data.
- **Embeddings** — Vector representations of text for similarity search.
- **Vector DB** — Chroma stores embedded policy chunks.
- **LangGraph** — Stateful workflow graph with conditional routing.
- **Agent state** — Shared memory for facts, decisions, citations, and trace per turn.
- **Memory** — Merges prior scenario facts with follow-up user replies.
- **Policy rule extraction** — Deterministic parsing of thresholds and approvals from chunks.
- **Citation verification** — Citations must come from retrieved chunks only.
- **Eval harness** — Golden cases plus Phase 4 quality audit with failure-mode taxonomy.

## How to Run

```bash
cd policy-rag-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Load API key from .env (OPENAI_API_KEY=sk-...)
export $(grep -v '^#' .env | xargs)

python scripts/ingest_mock_policies.py --replace
streamlit run app/streamlit_app.py
```

### Verify Phase 4.1 fixes

```bash
# Unit tests (includes Phase 4.1 regression suite)
python -m unittest tests.test_phase2_agent tests.test_phase3_agent tests.test_phase35_agent tests.test_phase4_audit tests.test_phase41_fixes -v

# Golden evals (20 cases)
python evals/run_agent_evals.py

# Phase 4 quality audit — offline (CI-safe, uses mock retrieval)
python evals/run_phase4_quality_audit.py --mock

# Phase 4 quality audit — live (requires .env OPENAI_API_KEY + ingested Chroma)
python evals/run_phase4_quality_audit.py
```

Set `OPENAI_API_KEY` in `.env` for embeddings, live retrieval, and optional LLM parsing. If live audit shows zero retrieved chunks, re-ingest and confirm the API key:

```bash
python scripts/ingest_mock_policies.py --replace
python evals/run_phase4_quality_audit.py
```

## Example Questions

**PolicyOps Agent**

- What is the work from home policy?
- Can I accept an INR 5,000 gift from a vendor?
- Can I accept an INR 12,000 gift from a vendor?
- Am I allowed to work from home for two weeks with manager approval?
- Can I share customer data with an external vendor?
- I lost my receipt for a taxi ride. Can I still claim reimbursement?
- Can I reimburse a client dinner for INR 18,000?

**Standard RAG Chat**

- What is prompt injection?
- What are the core functions of the NIST AI RMF?
- What risks are specific to generative AI systems?

## Evaluation and Quality

- **Golden evals** (`evals/golden_policy_cases.json`, 20 cases) — regression gate for decisions, citations, and answer types. **20/20 pass** after Phase 4.1.
- **Phase 4 quality audit** (`evals/phase4_quality_questions.json`, 75 cases) — comprehensive failure-mode testing across explanation, scenario, multi-turn, injection, boundary, and Standard RAG separation. **75/75 pass** under `--mock` after Phase 4.1.
- **Phase 4.1 regression tests** — `tests/test_phase41_fixes.py` covers parsing, routing, decision rules, answer routing, and RAG boundary refusal.
- **Failure-mode report** — generated at `reports/phase4_failure_modes.md` after each audit run.
- **Legacy NIST RAG baseline** — see `reports/evaluation_report.md` (v0.1, 10 questions).

```bash
python evals/run_phase4_quality_audit.py          # live retrieval (needs .env + ingest)
python evals/run_phase4_quality_audit.py --mock   # offline / CI (recommended for quick verify)
python evals/run_agent_evals.py                   # golden 20-case gate
```

**Insight:** Mock audit validates decision/routing logic; live audit additionally validates embedding retrieval quality. Run both before release.

## Known Limitations

- Synthetic Acme policies only; not legal, HR, finance, or tax advice.
- No real approval workflow integration or case management.
- No authentication or multi-tenant SaaS features.
- Simplified deterministic decision rules; complex prose may need LLM polish.
- LLM scenario parsing can fail and fall back to heuristics.
- Live retrieval requires OpenAI embeddings and a local Chroma index.
- Heuristic parsers do not cover every phrasing variant; new audit cases may expose gaps.
- `low_grounding` can still appear on passing cases when rationale omits expected keywords.

## Push to GitHub

```bash
cd policy-rag-assistant
source .venv/bin/activate

# Verify first (see commands above), then:
git add agent/ evals/ src/ tests/test_phase41_fixes.py reports/ README.md
git status
git commit -m "$(cat <<'EOF'
Fix Phase 4.1 audit failures: parsing, routing, decision rules, and RAG boundary.

Improves mock audit from 81% to 100% and golden evals to 20/20 by fixing clarify-before-decide routing, scenario fact extraction, and Standard RAG refusal for out-of-corpus topics.
EOF
)"
git push origin main
```

## Roadmap

- Human-in-the-loop approval queue
- Case management and audit logs
- Prompt-injection and boundary guardrails
- Observability and production monitoring
- Enterprise integrations (ServiceNow, SAP, identity providers)

## Safety Note

Demo assistant using synthetic Acme Corp policies and public governance documents. Confirm real decisions with the relevant internal team.
