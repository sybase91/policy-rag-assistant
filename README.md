# Enterprise AI Policy RAG Assistant

A beginner-friendly Python RAG (Retrieval-Augmented Generation) prototype for answering questions about enterprise AI governance, risk, and security policy.

## What This Project Is

This project builds a small RAG pipeline over public AI policy PDFs. You ask a question in plain English; the system retrieves relevant passages and generates an answer with citations back to the source document and page.

**Current milestone:** Embeddings and Chroma vector store (Phase 2).

## What Phase 2 Does

Phase 1 turned PDFs into text chunks. Phase 2 gives those chunks **meaning** that a computer can search:

1. **Embedding** — Each chunk is sent to OpenAI, which returns a list of numbers representing the chunk's meaning.
2. **Vector database** — Those number-lists are stored in Chroma, a local database optimized for similarity search.
3. **Why Chroma** — It runs on your machine, saves to disk, and works well with LangChain. No separate database server needed.
4. **Why metadata matters** — Each stored chunk keeps `source_file`, `page`, and `chunk_id` so future answers can cite the original PDF.
5. **Why before retrieval/generation** — Retrieval searches this index; generation reads the chunks retrieval finds. Without Phase 2, there is nothing to search.

## Corpus

Four public policy documents are used as the knowledge base:

| Local filename | Document | Source |
|----------------|----------|--------|
| `nist-ai-100-1.pdf` | NIST AI Risk Management Framework (AI RMF 1.0) | https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf |
| `nist-ai-600-1.pdf` | NIST Generative AI Profile | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf |
| `nist-cswp-29.pdf` | NIST Cybersecurity Framework 2.0 | https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf |
| `owasp-llm-top-10-v2025.pdf` | OWASP Top 10 for LLM Applications (2025) | https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf |

## Planned Architecture

```
data/raw/          PDF policy documents
    ?
src/ingest.py      Load PDFs ? LangChain Documents (per page)
    ?
src/chunk.py       Split into overlapping chunks with metadata
    ?
src/embed.py       Embed chunks ? Chroma vector store
    ?
src/retrieve.py    Similarity search over Chroma            [TODO]
    ?
src/generate.py    RAG answer with citations                [TODO]
    ?
app/streamlit_app.py   Chat UI                            [TODO]
    ?
src/evaluate.py    Run against gold questions             [TODO]
```

### Metadata Schema

Each chunk carries:

- `source_file` — PDF filename (e.g. `nist-ai-100-1.pdf`)
- `page` — 0-based page number
- `chunk_id` — unique ID (e.g. `nist-ai-100-1.pdf_p12_c003`)

See [reports/architecture.md](reports/architecture.md) for more detail.

## Setup

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

### 4. Download the policy PDFs

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

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder with your **real** OpenAI API key:

```
OPENAI_API_KEY=sk-your-real-key-here
```

> **Required for Phase 2.** Embeddings call the OpenAI API. Phases 1 (ingest/chunk) still work offline without a key.
>
> **Never commit `.env`.** It is listed in `.gitignore`.

## Current Milestone — Embeddings and Chroma

Run these commands from the project root with your virtual environment active.

### First-time build (or full refresh)

```bash
python -m src.embed --rebuild
```

Deletes any existing local index and rebuilds from the PDFs. Calls the OpenAI API once per chunk (~629 chunks).

### Load existing index

```bash
python -m src.embed
```

If `data/processed/chroma/` already exists, loads it and skips re-indexing. Still runs a test similarity search.

### Expected output

```
PDFs loaded: 4
Pages loaded: 189
Chunks created: 629
Chroma collection: ai_governance_docs
Chroma storage path: .../data/processed/chroma
Mode: rebuild
Chunks indexed: 629

--- Test search: "What is prompt injection?" ---

[1] source_file=owasp-llm-top-10-v2025.pdf
    page=...
    chunk_id=...
    text: ...
```

The test search should return chunks from OWASP or NIST documents about prompt injection.

### Phase 1 commands (still useful)

```bash
python -m src.ingest
python -m src.chunk
```

## Next Milestones

1. **Retrieval** — `src/retrieve.py`: similarity search over the vector store
2. **Generation** — `src/generate.py`: RAG answers with source citations
3. **Streamlit UI** — `app/streamlit_app.py`: interactive chat interface
4. **Evaluation** — `src/evaluate.py`: test against `evals/gold_questions.csv`

## Project Structure

```
policy-rag-assistant/
??? data/
?   ??? raw/              # Source PDFs
?   ??? processed/        # Chroma vector store (gitignored)
??? src/
?   ??? config.py         # Paths and defaults
?   ??? ingest.py         # PDF loading
?   ??? chunk.py          # Text splitting
?   ??? embed.py          # Embeddings + Chroma indexing
?   ??? retrieve.py       # [TODO]
?   ??? generate.py       # [TODO]
?   ??? evaluate.py       # [TODO]
??? app/
?   ??? streamlit_app.py  # [TODO]
??? evals/
?   ??? gold_questions.csv
??? reports/
?   ??? architecture.md
??? screenshots/
```

## License

See repository for license details.
