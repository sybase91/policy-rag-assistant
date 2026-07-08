# Enterprise AI Policy RAG Assistant

A beginner-friendly Python RAG (Retrieval-Augmented Generation) prototype for answering questions about enterprise AI governance, risk, and security policy.

## What This Project Is

This project builds a small RAG pipeline over public AI policy PDFs. You ask a question in plain English; the system retrieves relevant passages and generates an answer with citations back to the source document and page.

**Current milestone:** Retrieval (Phase 3).

## What Phase 3 Does

Phase 2 built a searchable index. Phase 3 **finds** the right passages for a question:

1. **Retrieval** - Given a question, search the Chroma index for the most relevant policy chunks.
2. **Similarity search** - The question is embedded into numbers, then compared to stored chunk vectors. Closest matches win.
3. **Same embedding model** - Uses `text-embedding-3-small`, the same model as indexing, so search results are meaningful.
4. **Metadata for citations** - Each result includes `source_file`, `page`, and `chunk_id` so you know where the text came from.
5. **Validate before generation** - We test retrieval alone first. If the wrong chunks are returned, the LLM would give bad answers later.

## What Phase 2 Does

Phase 1 turned PDFs into text chunks. Phase 2 gave those chunks **meaning** that a computer can search:

1. **Embedding** - Each chunk is sent to OpenAI, which returns a list of numbers representing the chunk's meaning.
2. **Vector database** - Those number-lists are stored in Chroma, a local database optimized for similarity search.
3. **Why Chroma** - It runs on your machine, saves to disk, and works well with LangChain. No separate database server needed.

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
    |
src/ingest.py      Load PDFs -> LangChain Documents (per page)
    |
src/chunk.py       Split into overlapping chunks with metadata
    |
src/embed.py       Embed chunks -> Chroma vector store
    |
src/retrieve.py    Similarity search over Chroma
    |
src/generate.py    RAG answer with citations                [TODO]
    |
app/streamlit_app.py   Chat UI                            [TODO]
    |
src/evaluate.py    Run against gold questions             [TODO]
```

### Metadata Schema

Each chunk carries:

- `source_file` - PDF filename (e.g. `nist-ai-100-1.pdf`)
- `page` - 0-based page number
- `chunk_id` - unique ID (e.g. `nist-ai-100-1.pdf_p12_c003`)

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

> **Required for Phases 2 and 3.** Embeddings and retrieval call the OpenAI API. Phase 1 (ingest/chunk) still works offline without a key.
>
> **Never commit `.env`.** It is listed in `.gitignore`.

### 6. Build the Chroma index (prerequisite for retrieval)

```bash
python -m src.embed --rebuild
```

## Current Milestone - Retrieval

Run this command from the project root with your virtual environment active:

```bash
python -m src.retrieve
```

### Prerequisites

- Chroma index must exist (`python -m src.embed --rebuild` if missing)
- Real `OPENAI_API_KEY` in local `.env`

### Expected output

The script runs 4 demo questions and prints the top 5 chunks for each:

```
Phase 3 Retrieval Demo
Chroma path: .../data/processed/chroma
Collection: ai_governance_docs
============================================================

Question: What is prompt injection?
------------------------------------------------------------

[1] rank=1
    source_file=owasp-llm-top-10-v2025.pdf
    page=3
    chunk_id=owasp-llm-top-10-v2025.pdf_p3_c001
    text: ...
```

Questions tested:

1. What is prompt injection?
2. What are the core functions of the NIST AI Risk Management Framework?
3. What risks are specific to generative AI systems?
4. How does cybersecurity governance connect to AI governance?

### Phase 2 commands (still useful)

```bash
python -m src.embed --rebuild   # first run or full refresh
python -m src.embed             # load existing index
```

### Phase 1 commands (still useful)

```bash
python -m src.ingest
python -m src.chunk
```

## Next Milestones

1. **Generation** - `src/generate.py`: RAG answers with source citations
2. **Streamlit UI** - `app/streamlit_app.py`: interactive chat interface
3. **Evaluation** - `src/evaluate.py`: test against `evals/gold_questions.csv`

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
?   ??? retrieve.py       # Similarity search
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
