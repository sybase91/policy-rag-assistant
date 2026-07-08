# Enterprise AI Policy RAG Assistant

A beginner-friendly but enterprise-oriented RAG (Retrieval-Augmented Generation) prototype that answers questions from public AI governance and LLM security PDFs - with source citations, grounded responses, a local Streamlit chat UI, and a basic evaluation harness.

**Status:** Phases 1-6 complete. Current milestone: Basic RAG evaluation (Phase 6).

---

## 1. Project overview

This project implements a full RAG pipeline over curated public policy documents. You ask a question in plain English; the system finds relevant passages and generates an answer grounded in those sources.

The assistant uses:

- **PDF ingestion** - load public policy PDFs from `data/raw/`
- **Chunking** - split pages into overlapping text segments with metadata
- **Embeddings** - convert chunks into meaning vectors via OpenAI
- **Local Chroma vector store** - persist and search those vectors on disk
- **Retrieval** - find the most relevant chunks for a question
- **Grounded answer generation** - answer only from retrieved context, with citations
- **Streamlit UI** - ask questions in a local browser chat interface
- **Source citations** - show `source_file`, `page`, and `chunk_id` for verification
- **Basic evaluation** - score source hits, keyword coverage, and refusal behavior

This is a **local prototype** - not a cloud-deployed product yet.

---

## 2. Why I built this

This project is part of an **enterprise AI proof-of-work portfolio**.

It is **not** just a "chat with PDF" demo. It is a step-by-step implementation of an enterprise RAG system with:

- Clean document preparation and source metadata
- A real vector index (not a one-off notebook demo)
- Grounded answers with refusal for out-of-corpus questions
- A usable local UI for demos and review
- A simple **v0.1 evaluation harness** that measures source hits, keyword coverage, and refusal accuracy

The goal is to show how AI governance knowledge can be turned into a trustworthy assistant - not merely a generative chatbot.

---

## 3. Knowledge base / corpus

Four public policy documents form the knowledge base:

| Local filename | Document | Why it is in the corpus |
|----------------|----------|-------------------------|
| `nist-ai-100-1.pdf` | [NIST AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf) | AI governance and risk management practices |
| `nist-ai-600-1.pdf` | [NIST AI 600-1 Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | GenAI-specific risks and controls |
| `owasp-llm-top-10-v2025.pdf` | [OWASP Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf) | LLM security risks (e.g. prompt injection) |
| `nist-cswp-29.pdf` | [NIST Cybersecurity Framework 2.0](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf) | Cybersecurity governance linked to AI risk |

**Why this corpus is useful**

- **AI governance** - how organizations manage AI risk responsibly
- **GenAI risk** - risks specific to generative systems
- **LLM security** - application-layer threats for LLM products
- **Cybersecurity governance** - how security frameworks connect to AI programs
- **Enterprise risk management** - practical language leaders and risk teams already use

All PDFs live under `data/raw/`. See [reports/architecture.md](reports/architecture.md) for deeper pipeline detail.

---

## 4. End-to-end architecture

```
PDFs
-> Ingestion
-> Chunking
-> Embeddings
-> Chroma Vector Store
-> Retrieval
-> Grounded Generation
-> Streamlit UI
-> Evaluation
```

| Layer | Simple explanation |
|-------|--------------------|
| **Ingestion** | Read PDFs and turn each page into a text document with source metadata. |
| **Chunking** | Split long pages into smaller overlapping pieces so search and context windows work better. |
| **Embeddings** | Convert each chunk into a list of numbers that represent meaning. |
| **Chroma Vector Store** | Save those numbers locally so similar text can be found quickly. |
| **Retrieval** | Embed the user question and find the closest stored chunks. |
| **Grounded Generation** | Ask the LLM to answer using only those chunks, with citations and refusal when unsupported. |
| **Streamlit UI** | Present the same backend as a browser chat app. |
| **Evaluation** | Measure whether retrieval and answers meet simple gold-question checks (Phase 6). |

```
policy-rag-assistant/
??? data/
?   ??? raw/                 # Source PDFs
?   ??? processed/           # Chroma vector store (gitignored)
??? src/
?   ??? config.py            # Paths and defaults
?   ??? ingest.py            # PDF loading
?   ??? chunk.py             # Text splitting
?   ??? embed.py             # Embeddings + Chroma indexing
?   ??? retrieve.py          # Similarity search
?   ??? generate.py          # Grounded answer generation
?   ??? evaluate.py          # Basic RAG evaluation (v0.1)
??? app/
?   ??? streamlit_app.py     # Streamlit chat UI
??? evals/
?   ??? gold_questions.csv
?   ??? eval_results.csv     # Generated by python -m src.evaluate
??? reports/
?   ??? architecture.md
?   ??? evaluation_report.md # Generated by python -m src.evaluate
??? screenshots/
```

---

## 5. Build phases completed

| Phase | Status | What was built | Why it matters | Main files | Test / run command |
|-------|--------|----------------|----------------|------------|--------------------|
| **Phase 1 - PDF ingestion and chunking** | Complete | Loaded PDFs from `data/raw`; parsed into page-level documents; split into smaller chunks; preserved `source_file`, `page`, and `chunk_id` | RAG quality starts with clean document preparation; metadata enables citations later | `src/ingest.py`, `src/chunk.py` | `python -m src.ingest` · `python -m src.chunk` |
| **Phase 2 - Embeddings and Chroma vector store** | Complete | Converted chunks into OpenAI embeddings; stored them locally in Chroma; added rebuild / load-existing behavior; tested semantic search for "What is prompt injection?" | Embeddings turn text into searchable meaning vectors; Chroma is the local vector database | `src/config.py`, `src/embed.py` | `python -m src.embed --rebuild` · `python -m src.embed` |
| **Phase 3 - Retrieval layer** | Complete | Loaded the existing Chroma index; implemented question-based similarity search; returned top relevant chunks with metadata; tested across OWASP, NIST AI RMF, NIST GenAI Profile, and NIST CSF questions | Retrieval is the evidence-finding step in RAG; bad retrieval leads to bad answers | `src/retrieve.py` | `python -m src.retrieve` |
| **Phase 4 - Grounded answer generation with citations** | Complete | Added LLM-based answer generation from retrieved chunks; strict prompt rules to answer only from context; refusal for unsupported questions; returned answers with source information | This is the generation step in RAG - grounded, cited answers instead of raw chunks only | `src/generate.py` | `python -m src.generate` |
| **Phase 5 - Streamlit chat UI** | Complete | Local web chat interface; grounded answers in the browser; sources expander; example questions, sidebar context, feedback placeholders, and Clear chat | Converts terminal RAG into a demo-friendly local UI | `app/streamlit_app.py` | `streamlit run app/streamlit_app.py` |
| **Phase 6 - Basic RAG evaluation** | Complete / Current | Gold question set; evaluation script; source hit rate; keyword hit rate; refusal accuracy; pass rate; results CSV and markdown report | Moves the project from "it works" to "we can measure whether it works" | `src/evaluate.py`, `evals/gold_questions.csv`, `evals/eval_results.csv`, `reports/evaluation_report.md` | `python -m src.evaluate` |

### What Phase 6 does

Phase 6 adds a **simple v0.1 evaluation harness** (not RAGAS, not LLM-as-judge):

1. Loads labeled **gold questions** from `evals/gold_questions.csv`
2. Calls `answer_question()` for each question (same backend as Phase 4/5)
3. Scores each row for source hit, keyword coverage, and correct refusal
4. Writes `evals/eval_results.csv` and `reports/evaluation_report.md`
5. Prints a clean terminal summary of pass rate and related metrics

**Metrics explained**

| Metric | Meaning |
|--------|---------|
| **source_hit_rate** | Share of questions where the expected PDF appears in returned sources (for refuse/`none` rows: refusal text is present) |
| **keyword_hit_rate** | Average share of expected phrases found in generated answers (answerable rows) |
| **refusal_accuracy** | Share of unsupported questions that include the grounded refusal message |
| **pass_rate** | Share of gold questions that meet the v0.1 pass rule |

**Pass rule (v0.1)**

- For `answer` rows: `source_hit` is True **and** `keyword_hit_rate >= 0.5`
- For `refuse` rows: answer contains `I don't know based on the provided documents.`

### Phase highlights (quick read)

**Phase 1** prepares trustworthy source units. **Phase 2** makes them searchable. **Phase 3** finds evidence. **Phase 4** writes grounded answers. **Phase 5** makes the system showcaseable in a browser. **Phase 6** measures quality with a transparent rule-based harness.

---

## 6. Beginner-friendly concept explanations

**What is RAG?**  
Retrieval-Augmented Generation. Instead of asking a model to answer from memory alone, the system first finds relevant documents, then generates an answer using that evidence.

**What is chunking?**  
Splitting long documents into smaller overlapping pieces. Smaller chunks improve search precision and fit better into the model's context window.

**What is an embedding?**  
A list of numbers that represents the meaning of text. Similar ideas get similar number patterns, even when the wording differs.

**What is a vector database?**  
A store optimized for similarity search over embeddings. This project uses **Chroma** locally so the index persists on disk.

**What is retrieval?**  
The step that finds the most relevant chunks for a user question - the evidence-gathering step before generation.

**What is grounded generation?**  
Answering only from the retrieved context, not inventing outside facts. Unsupported questions should be refused.

**Why do citations matter?**  
Citations let reviewers verify claims against the original PDF, page, and chunk - essential for governance and trust.

**Why evaluation matters?**  
A demo can look good and still fail quietly. Evaluation measures retrieval quality, groundedness, and refusal behavior with repeatable metrics.

**What is a gold question?**  
A labeled test item with an expected source, expected keywords, and expected behavior (`answer` or `refuse`).

---

## 7. Setup instructions

### 1. Clone the repository

```bash
git clone https://github.com/sybase91/policy-rag-assistant.git
cd policy-rag-assistant
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download the policy PDFs (if not already present)

```bash
mkdir -p data/raw

curl -L -o data/raw/nist-ai-100-1.pdf \
  "https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf"

curl -L -o data/raw/nist-ai-600-1.pdf \
  "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf"

curl -L -o data/raw/nist-cswp-29.pdf \
  "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf"

curl -L -o data/raw/owasp-llm-top-10-v2025.pdf \
  "https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf"
```

### 5. Create local `.env`

```bash
cp .env.example .env
```

Edit `.env` and set your key (use a **placeholder** in documentation; put your real key only in the local file):

```
OPENAI_API_KEY=your_openai_api_key_here
```

**Never commit `.env`.** It is ignored by `.gitignore`. Phases 2-6 require a real key for OpenAI embeddings and chat.

### 6. Build or rebuild the vector index

```bash
python -m src.embed --rebuild
```

### 7. Run the terminal generation test

```bash
python -m src.generate
```

### 8. Run the Streamlit app

```bash
streamlit run app/streamlit_app.py
```

Opens a local web app (typically http://localhost:8501).

### 9. Run the Phase 6 evaluation harness

```bash
python -m src.evaluate
```

This calls the live RAG backend for each gold question, then writes:

- `evals/eval_results.csv`
- `reports/evaluation_report.md`

Expect API cost and latency for about 10 generation calls.

### Optional phase commands

```bash
python -m src.ingest              # Phase 1: load PDFs
python -m src.chunk               # Phase 1: chunk text
python -m src.embed               # Phase 2: load existing index if present
python -m src.retrieve            # Phase 3: retrieval demo
python -m src.generate            # Phase 4: grounded answers in the terminal
streamlit run app/streamlit_app.py  # Phase 5: chat UI
python -m src.evaluate            # Phase 6: basic evaluation
```

---

## 8. Example questions

Try these in the Streamlit UI, via `python -m src.generate`, or as part of `python -m src.evaluate`:

- What is prompt injection?
- What are the core functions of the NIST AI Risk Management Framework?
- What risks are specific to generative AI systems?
- How does cybersecurity governance connect to AI governance?
- What is my company's refund policy?

The last question should be **refused**, because refund policy is outside the provided documents. A good RAG assistant says it does not know when the corpus does not support the answer.

**Expected UI behavior (Phase 5)**

- Chat thread with user and assistant messages
- Spinner while searching and generating
- Grounded answer with citations
- **Sources used** expander (`source_file`, `page`, `chunk_id`)
- **Debug info** expander (chunk count and model name)
- **Clear chat** in the sidebar
- Feedback buttons are placeholders for a later phase

---

## 9. Current capabilities

- Loads public AI governance PDFs
- Splits them into metadata-rich chunks
- Creates embeddings with OpenAI
- Stores vectors in a local Chroma index
- Retrieves relevant chunks for a question
- Generates grounded answers from retrieved context
- Shows citations / sources for verification
- Provides a local Streamlit chat UI for demos
- Runs a basic v0.1 evaluation harness against gold questions

---

## 10. Current limitations

- Evaluation is rule-based (v0.1), not RAGAS / LLM-as-judge
- Small gold set (10 questions)
- No reranking yet
- No hybrid search yet
- No deployed hosted app yet
- No user authentication
- No PDF upload UI
- Citation quality is basic (file + page + chunk metadata)

---

## 11. Roadmap

1. **Phase 7** - README polish, screenshots, demo recording
2. **Phase 8** - Retrieval quality improvements
3. **Phase 9** - Reranking / hybrid search
4. **Phase 10** - Deployment
5. **Phase 11** - FastAPI + Next.js version
6. **Phase 12** - Lead-capture website integration

---

## 12. Portfolio note

This project is part of a broader **enterprise AI proof-of-work roadmap** covering RAG systems, evaluation, agentic workflows, MLOps, AI governance, cloud architecture, and AI product strategy.

The intent is to demonstrate not only "I can call an LLM," but also how to design a system leaders can trust: grounded retrieval, citation metadata, clear limitations, and measurable quality.

---

## 13. Safety note

- The OpenAI API key should only live in a **local** `.env` file
- `.env` is ignored by Git - never commit secrets
- `data/processed/` is ignored because it contains local Chroma database files
- Use placeholders in docs and examples (for example `your_openai_api_key_here`)
- Never paste real API keys into README, commits, screenshots, or chat logs

---

## License

See the repository for license details.
