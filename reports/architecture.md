# Architecture — Enterprise AI Policy RAG Assistant

## Overview

This document describes the RAG pipeline architecture, data flow, and implementation status.

## Corpus Sources

| Document | Purpose |
|----------|---------|
| NIST AI RMF 1.0 | AI risk management framework and governance practices |
| NIST Generative AI Profile | Risk profile for generative AI systems |
| NIST CSF 2.0 | Cybersecurity framework applicable to AI systems |
| OWASP LLM Top 10 (2025) | Security risks specific to LLM applications |

All documents are stored as PDFs in `data/raw/`.

## Pipeline Stages

### 1. Ingestion (`src/ingest.py`) — Implemented

- Scans `data/raw/` for `*.pdf` files
- Uses LangChain `PyPDFLoader` to load one `Document` per page
- Normalizes metadata: `source_file`, `page`

### 2. Chunking (`src/chunk.py`) — Implemented

- Splits page documents with `RecursiveCharacterTextSplitter`
- Defaults: `chunk_size=900`, `chunk_overlap=150`
- Preserves `source_file` and `page`; adds `chunk_id`

### 3. Embedding (`src/embed.py`) — Planned

- Embed chunks with OpenAI `text-embedding-3-small` (or similar)
- Persist vectors in ChromaDB under `data/processed/`

### 4. Retrieval (`src/retrieve.py`) — Planned

- Accept a user query, embed it, run similarity search
- Return top-k chunks with metadata for citation

### 5. Generation (`src/generate.py`) — Planned

- Pass retrieved chunks + question to an OpenAI chat model
- Produce an answer with inline or footnote citations (`source_file`, `page`)

### 6. UI (`app/streamlit_app.py`) — Planned

- Streamlit chat interface for interactive Q&A

### 7. Evaluation (`src/evaluate.py`) — Planned

- Run pipeline against `evals/gold_questions.csv`
- Measure retrieval hit rate and answer quality

## Metadata Schema

| Field | Type | Example | Set by |
|-------|------|---------|--------|
| `source_file` | str | `nist-ai-100-1.pdf` | ingest |
| `page` | int | `12` | ingest |
| `chunk_id` | str | `nist-ai-100-1.pdf_p12_c003` | chunk |

## Data Directories

| Path | Contents | Git tracked |
|------|----------|-------------|
| `data/raw/` | Source PDFs | Yes |
| `data/processed/` | Chroma DB, cached chunks | No (gitignored) |

## Configuration (`src/config.py`)

- `RAW_DATA_DIR`, `PROCESSED_DATA_DIR` — resolved from project root
- `CHUNK_SIZE`, `CHUNK_OVERLAP` — splitter defaults
- `load_dotenv()` — loads `OPENAI_API_KEY` for future phases

## Security Notes

- `.env` is gitignored; only `.env.example` with placeholders is committed
- No API calls in Phase 1 (ingest/chunk run fully offline)
