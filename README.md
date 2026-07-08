# Enterprise AI Policy RAG Assistant

A beginner-friendly Python RAG (Retrieval-Augmented Generation) prototype for answering questions about enterprise AI governance, risk, and security policy.

## What This Project Is

This project builds a small RAG pipeline over public AI policy PDFs. You ask a question in plain English; the system retrieves relevant passages and generates an answer with citations back to the source document and page.

**Current milestone:** Streamlit Chat UI (Phase 5).

## What Phase 5 Does

Phase 4 generated answers in the terminal. Phase 5 adds a **local web chat UI**:

1. **Streamlit** - A Python library that turns scripts into simple local web apps.
2. **Chat UI** - Type questions and see answers in a conversational thread.
3. **`st.chat_input`** - The text box at the bottom for new questions.
4. **`st.chat_message`** - Renders user and assistant message bubbles.
5. **Session state** - `st.session_state` keeps chat history while the app is open.
6. **Calls `answer_question()`** - The UI does not duplicate RAG logic; it uses the Phase 4 backend.
7. **Sources shown separately** - Answers are readable prose; sources appear in an expander for verification.

This is a **local prototype only** — not deployed to the cloud.

## What Phase 4 Does

Phase 3 finds relevant chunks. Phase 4 writes a grounded answer from those chunks with citations and refusal for unsupported questions.

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
app/streamlit_app.py   Chat UI
    |
src/evaluate.py    Run against gold questions             [TODO]
```

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

> **Required for Phases 2-5.** Never commit `.env` — it is listed in `.gitignore`.

### 6. Build the Chroma index (prerequisite)

```bash
python -m src.embed --rebuild
```

## Current Milestone - Streamlit Chat UI

Run this command from the project root with your virtual environment active:

```bash
streamlit run app/streamlit_app.py
```

Opens a local web app (typically http://localhost:8501).

### Prerequisites

- Chroma index built (`python -m src.embed --rebuild`)
- Real `OPENAI_API_KEY` in local `.env`
- PDFs in `data/raw/`

### Example questions

- What is prompt injection?
- What are the core functions of the NIST AI RMF?
- What risks are specific to generative AI systems?
- How does cybersecurity governance connect to AI governance?
- What is my company's refund policy? (expected refusal)

### Expected behavior

- Chat thread with user and assistant messages
- Spinner while the answer is generated
- Grounded answer with inline citations
- **Sources used** expander with `source_file`, `page`, `chunk_id`
- **Debug info** expander with chunk count and model name
- **Clear chat** button in the sidebar
- Feedback buttons show a placeholder message (not saved yet)

### Earlier phase commands (still useful)

```bash
python -m src.generate            # Phase 4: terminal answers
python -m src.retrieve            # Phase 3: retrieval only
python -m src.embed --rebuild     # Phase 2: build index
python -m src.ingest              # Phase 1: load PDFs
python -m src.chunk               # Phase 1: chunk text
```

## Next Milestones

1. **Evaluation** - `src/evaluate.py`: test against `evals/gold_questions.csv`

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
?   ??? streamlit_app.py  # Chat UI
??? evals/
?   ??? gold_questions.csv
??? reports/
?   ??? architecture.md
??? screenshots/
```

## License

See repository for license details.
