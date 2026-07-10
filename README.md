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
pip install -r requirements.txt
python scripts/ingest_mock_policies.py --replace
streamlit run app/streamlit_app.py
python evals/run_agent_evals.py
python evals/run_phase4_quality_audit.py
python -m unittest tests.test_phase2_agent tests.test_phase3_agent tests.test_phase35_agent tests.test_phase4_audit -v
```

Set `OPENAI_API_KEY` in `.env` for embeddings and optional LLM parsing. Live Phase 4 audit requires an ingested corpus and API access.

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

- **Golden evals** (`evals/golden_policy_cases.json`, 20 cases) — regression gate for decisions, citations, and answer types.
- **Phase 4 quality audit** (`evals/phase4_quality_questions.json`, 75 cases) — comprehensive failure-mode testing across explanation, scenario, multi-turn, injection, boundary, and Standard RAG separation.
- **Failure-mode report** — generated at `reports/phase4_failure_modes.md` after each audit run.
- **Legacy NIST RAG baseline** — see `reports/evaluation_report.md` (v0.1, 10 questions).

```bash
python evals/run_phase4_quality_audit.py          # live retrieval
python evals/run_phase4_quality_audit.py --mock   # offline / CI
```

## Known Limitations

- Synthetic Acme policies only; not legal, HR, finance, or tax advice.
- No real approval workflow integration or case management.
- No authentication or multi-tenant SaaS features.
- Simplified deterministic decision rules; complex prose may need LLM polish.
- LLM scenario parsing can fail and fall back to heuristics.
- Live retrieval requires OpenAI embeddings and a local Chroma index.

## Roadmap

- Human-in-the-loop approval queue
- Case management and audit logs
- Prompt-injection and boundary guardrails
- Observability and production monitoring
- Enterprise integrations (ServiceNow, SAP, identity providers)

## Safety Note

Demo assistant using synthetic Acme Corp policies and public governance documents. Confirm real decisions with the relevant internal team.
