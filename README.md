# Enterprise AI Policy RAG Assistant

A beginner-friendly Python RAG (Retrieval-Augmented Generation) prototype for answering questions about enterprise AI governance, risk, and security policy.

## What This Project Is

This project builds a small RAG pipeline over public AI policy PDFs. You ask a question in plain English; the system retrieves relevant passages and generates an answer with citations back to the source document and page.

**Current milestone:** Grounded answer generation (Phase 4).

## What Phase 4 Does

Phase 3 finds relevant chunks. Phase 4 **writes** a grounded answer from those chunks:

1. **Generation in RAG** - The LLM turns retrieved passages into a readable answer.
2. **Grounded generation** - The answer must use only the retrieved context, not outside knowledge.
3. **Why pass chunks to the LLM** - The model has not read your PDFs; chunks are its only evidence.
4. **Citations** - Answers cite sources like `[owasp-llm-top-10-v2025.pdf, page 6]` so you can verify claims.
5. **Refusal** - Unsupported questions (e.g. refund policy) get a safe refusal instead of a made-up answer.
6. **Terminal only** - This phase runs in the terminal. A Streamlit UI comes later.

## What Phase 3 Does

Phase 2 built a searchable index. Phase 3 **finds** the right passages for a question:

1. **Retrieval** - Given a question, search the Chroma index for the most relevant policy chunks.
2. **Similarity search** - The question is embedded into numbers, then compared to stored chunk vectors.
3. **Metadata for citations** - Each result includes `source_file`, `page`, and `chunk_id`.

## What Phase 2 Does

Phase 1 turned PDFs into text chunks. Phase 2 gave those chunks **meaning** that a computer can search:

1. **Embedding** - Each chunk is sent to OpenAI, which returns a list of numbers representing the chunk's meaning.
2. **Vector database** - Those number-lists are stored in Chroma, a local database optimized for similarity search.

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
src/generate.py    Grounded answer with citations
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

> **Required for Phases 2, 3, and 4.** Embeddings, retrieval, and generation call the OpenAI API. Phase 1 (ingest/chunk) still works offline without a key.
>
> **Never commit `.env`.** It is listed in `.gitignore`.

### 6. Build the Chroma index (prerequisite for retrieval and generation)

```bash
python -m src.embed --rebuild
```

## Current Milestone - Grounded Generation

Run this command from the project root with your virtual environment active:

```bash
python -m src.generate
```

This is **terminal-based answer generation**, not a UI yet.

### Prerequisites

- Chroma index must exist (`python -m src.embed --rebuild` if missing)
- Real `OPENAI_API_KEY` in local `.env`

### Example questions tested

1. What is prompt injection?
2. What are the core functions of the NIST AI Risk Management Framework?
3. What risks are specific to generative AI systems?
4. How does cybersecurity governance connect to AI governance?
5. What is my company's refund policy? (expected refusal - not in corpus)

### Expected output

```
Phase 4 Grounded Generation Demo
Chat model: gpt-4o-mini (temperature=0)
============================================================

Question: What is prompt injection?

Answer:
Prompt injection is ... [owasp-llm-top-10-v2025.pdf, page 6]

Sources:
1. owasp-llm-top-10-v2025.pdf, page 6, chunk_id=owasp-llm-top-10-v2025.pdf_p6_c000
2. ...
```

For the refund policy question, expect a refusal such as:

`I don't know based on the provided documents.`

### Earlier phase commands (still useful)

```bash
python -m src.retrieve            # Phase 3: retrieval only
python -m src.embed --rebuild     # Phase 2: build index
python -m src.ingest              # Phase 1: load PDFs
python -m src.chunk               # Phase 1: chunk text
```

## Next Milestones

1. **Streamlit UI** - `app/streamlit_app.py`: interactive chat interface
2. **Evaluation** - `src/evaluate.py`: test against `evals/gold_questions.csv`

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
?   ??? generate.py       # Grounded answer generation
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
