# Architecture - Enterprise AI Policy RAG Assistant

## Overview

This document describes the RAG pipeline architecture, data flow, and implementation status.

## Full Pipeline

```
PDFs -> Ingestion -> Chunking -> Embeddings -> Chroma Vector Store -> Retrieval -> Generation TODO -> UI TODO -> Evaluation TODO
```

## Corpus Sources

| Document | Purpose |
|----------|---------|
| NIST AI RMF 1.0 | AI risk management framework and governance practices |
| NIST Generative AI Profile | Risk profile for generative AI systems |
| NIST CSF 2.0 | Cybersecurity framework applicable to AI systems |
| OWASP LLM Top 10 (2025) | Security risks specific to LLM applications |

All documents are stored as PDFs in `data/raw/`.

## Pipeline Stages

### 1. Ingestion (`src/ingest.py`) - Implemented

- Scans `data/raw/` for `*.pdf` files
- Uses LangChain `PyPDFLoader` to load one `Document` per page
- Normalizes metadata: `source_file`, `page`

### 2. Chunking (`src/chunk.py`) - Implemented

- Splits page documents with `RecursiveCharacterTextSplitter`
- Defaults: `chunk_size=900`, `chunk_overlap=150`
- Preserves `source_file` and `page`; adds `chunk_id`

### 3. Embedding (`src/embed.py`) - Implemented

Phase 2 converts text chunks into embeddings and stores them in Chroma.

**What is an embedding?**

An embedding is a list of numbers (a vector) that represents the meaning of a piece of text. Text about similar topics ends up with similar number patterns, even when the exact words differ.

**What is Chroma?**

Chroma is a vector database - a searchable store for those number-lists. It runs locally, persists to disk, and integrates with LangChain. We use it because it is lightweight and beginner-friendly for a prototype.

**How Phase 2 fits between chunking and retrieval**

- Phase 1 produces text chunks with metadata.
- Phase 2 sends each chunk to OpenAI's embedding model and saves the resulting vectors in Chroma.
- Phase 3 (retrieval) searches this index to find the most relevant chunks for a user question.
- Phase 4 (generation) will use those chunks to write an answer with citations.

You cannot retrieve or generate good answers until the vector index exists - that is why embeddings come first.

**Implementation details**

| Setting | Value |
|---------|-------|
| Embedding model | `text-embedding-3-small` (OpenAI) |
| Vector store | Chroma (persistent, local) |
| Storage path | `data/processed/chroma` |
| Collection name | `ai_governance_docs` |
| Metadata preserved | `source_file`, `page`, `chunk_id` |
| API key | Required in local `.env` (`OPENAI_API_KEY`) |

**Idempotent behavior**

- `python -m src.embed` - builds the index if missing, otherwise loads the existing one
- `python -m src.embed --rebuild` - deletes and recreates the index from scratch
- `chunk_id` is used as the Chroma document ID to prevent duplicate chunks

### 4. Retrieval (`src/retrieve.py`) - Implemented

Phase 3 loads the existing Chroma index and returns the most relevant chunks for a question.

**What retrieval does in RAG**

Retrieval is the "R" in RAG. Before any LLM writes an answer, the system must find the right passages from the policy documents. Retrieval takes a user question and returns ranked chunks that are semantically similar in meaning.

**How similarity search works**

1. The question is converted to a vector using the same embedding model (`text-embedding-3-small`).
2. Chroma compares that vector to all stored chunk vectors.
3. The closest matches (highest similarity) are returned as the top-k results.

**Why the same embedding model matters**

Indexing and querying must use the same model. Different models produce vectors in different "meaning spaces," so search results would be unreliable if models differed.

**What good retrieval output looks like**

- Relevant preview text that actually addresses the question
- Correct `source_file` (e.g. OWASP for prompt injection, NIST AI 600-1 for generative AI risks)
- Valid `page` and `chunk_id` for every result
- Consistent metadata on all ranked chunks

**Why validate retrieval before generation**

If retrieval returns wrong or empty chunks, the LLM may hallucinate or cite the wrong source. Testing retrieval alone (Phase 3) confirms the search layer works before adding answer generation.

**Implementation details**

| Setting | Value |
|---------|-------|
| Entry point | `python -m src.retrieve` |
| Default top-k | 5 chunks per question |
| Functions | `get_vectorstore()`, `retrieve_context()`, `format_retrieved_chunks()` |
| Prerequisite | Chroma index from `python -m src.embed --rebuild` |
| API key | Required (embeds each question for search) |

### 5. Generation (`src/generate.py`) - Planned

- Pass retrieved chunks + question to an OpenAI chat model
- Produce an answer with inline or footnote citations (`source_file`, `page`)

### 6. UI (`app/streamlit_app.py`) - Planned

- Streamlit chat interface for interactive Q&A

### 7. Evaluation (`src/evaluate.py`) - Planned

- Run pipeline against `evals/gold_questions.csv`
- Measure retrieval hit rate and answer quality

## Metadata Schema

| Field | Type | Example | Set by |
|-------|------|---------|--------|
| `source_file` | str | `nist-ai-100-1.pdf` | ingest |
| `page` | int (str in Chroma) | `12` | ingest |
| `chunk_id` | str | `nist-ai-100-1.pdf_p12_c003` | chunk |

Metadata matters because retrieval returns chunks, but users need `source_file` and `page` to trust and verify answers.

## Data Directories

| Path | Contents | Git tracked |
|------|----------|-------------|
| `data/raw/` | Source PDFs | Yes |
| `data/processed/chroma/` | Chroma vector database | No (gitignored via `data/processed/`) |

## Configuration (`src/config.py`)

- `RAW_DATA_DIR`, `PROCESSED_DATA_DIR` - resolved from project root
- `CHUNK_SIZE`, `CHUNK_OVERLAP` - splitter defaults
- `CHROMA_PERSIST_DIR`, `CHROMA_COLLECTION_NAME`, `EMBEDDING_MODEL` - vector store settings
- `load_dotenv()` - loads `OPENAI_API_KEY` from local `.env`

## Security Notes

- `.env` is gitignored; only `.env.example` with placeholders is committed
- Phase 1 (ingest/chunk) runs fully offline
- Phases 2 and 3 call the OpenAI API - requires a real API key in local `.env` only
