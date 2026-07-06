# Enterprise AI Policy RAG Assistant

A beginner-friendly Python RAG (Retrieval-Augmented Generation) prototype for answering questions about enterprise AI governance, risk, and security policy.

## What This Project Is

This project builds a small RAG pipeline over public AI policy PDFs. You ask a question in plain English; the system retrieves relevant passages and generates an answer with citations back to the source document and page.

**Current milestone:** PDF ingestion and text chunking (Phase 1).

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
    ↓
src/ingest.py      Load PDFs → LangChain Documents (per page)
    ↓
src/chunk.py       Split into overlapping chunks with metadata
    ↓
src/embed.py       Embed chunks → Chroma vector store       [TODO]
    ↓
src/retrieve.py    Similarity search over Chroma            [TODO]
    ↓
src/generate.py    RAG answer with citations                [TODO]
    ↓
app/streamlit_app.py   Chat UI                            [TODO]
    ↓
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

Edit `.env` and replace the placeholder with your real OpenAI API key (needed in later phases, not for ingestion/chunking):

```
OPENAI_API_KEY=your_real_key_here
```

> **Never commit `.env`.** It is listed in `.gitignore`.

## Current Milestone — Ingestion and Chunking

Run these commands from the project root with your virtual environment active:

```bash
# Load PDFs and print page counts
python -m src.ingest

# Split pages into chunks and print sample output
python -m src.chunk
```

## Next Milestones

1. **Embeddings** — `src/embed.py`: embed chunks with OpenAI and store in ChromaDB
2. **Retrieval** — `src/retrieve.py`: similarity search over the vector store
3. **Generation** — `src/generate.py`: RAG answers with source citations
4. **Streamlit UI** — `app/streamlit_app.py`: interactive chat interface
5. **Evaluation** — `src/evaluate.py`: test against `evals/gold_questions.csv`

## Project Structure

```
policy-rag-assistant/
├── data/
│   ├── raw/              # Source PDFs
│   └── processed/        # Vector store output (gitignored)
├── src/
│   ├── config.py         # Paths and defaults
│   ├── ingest.py         # PDF loading
│   ├── chunk.py          # Text splitting
│   ├── embed.py          # [TODO]
│   ├── retrieve.py       # [TODO]
│   ├── generate.py       # [TODO]
│   └── evaluate.py       # [TODO]
├── app/
│   └── streamlit_app.py  # [TODO]
├── evals/
│   └── gold_questions.csv
├── reports/
│   └── architecture.md
└── screenshots/
```

## License

See repository for license details.
