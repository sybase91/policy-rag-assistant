"""Retrieve relevant chunks from the Chroma vector store.

Retrieval means finding the passages most relevant to a user question.
Similarity search converts the question into a vector and finds the closest
stored chunk vectors. We use the same embedding model as indexing so both
live in the same meaning space. Metadata (source_file, page, chunk_id) lets
us cite sources and debug results. We validate retrieval before adding LLM
answer generation because bad retrieval leads to bad or hallucinated answers.
"""

from __future__ import annotations

import sys

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import CHROMA_COLLECTION_NAME, CHROMA_PERSIST_DIR
from src.embed import get_embeddings, validate_api_key

PREVIEW_LENGTH = 300

DEMO_QUESTIONS = [
    "What is prompt injection?",
    "What are the core functions of the NIST AI Risk Management Framework?",
    "What risks are specific to generative AI systems?",
    "How does cybersecurity governance connect to AI governance?",
]


def _ensure_index_exists() -> None:
    """Confirm the Chroma index from Phase 2 exists before searching."""
    if not CHROMA_PERSIST_DIR.exists():
        print("No Chroma index found. Run python -m src.embed --rebuild first.")
        sys.exit(1)

    try:
        store = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(CHROMA_PERSIST_DIR),
        )
        if store._collection.count() == 0:
            print("No Chroma index found. Run python -m src.embed --rebuild first.")
            sys.exit(1)
    except Exception:
        print("No Chroma index found. Run python -m src.embed --rebuild first.")
        sys.exit(1)


def get_vectorstore() -> Chroma:
    """Load and return the existing Chroma vector store."""
    # Step 1: Validate API key (needed to embed the question for search).
    validate_api_key()

    # Step 2: Confirm the index built in Phase 2 is present.
    _ensure_index_exists()

    # Step 3: Load Chroma with the same embedding model used during indexing.
    return Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_PERSIST_DIR),
    )


def retrieve_context(question: str, k: int = 5) -> list[Document]:
    """Search the vector store for the top-k chunks most relevant to the question.

    Return LangChain Document objects.
    """
    vectorstore = get_vectorstore()

    # Step 4: Embed the question and run similarity search against stored chunks.
    return vectorstore.similarity_search(question, k=k)


def format_retrieved_chunks(chunks: list[Document]) -> list[dict]:
    """Convert retrieved chunks into a clean list of dictionaries.

    Each dict contains: rank, source_file, page, chunk_id, preview.
    """
    formatted: list[dict] = []
    for rank, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        preview = chunk.page_content[:PREVIEW_LENGTH].replace("\n", " ")
        if len(chunk.page_content) > PREVIEW_LENGTH:
            preview += "..."

        formatted.append(
            {
                "rank": rank,
                "source_file": metadata.get("source_file", "unknown"),
                "page": metadata.get("page", "unknown"),
                "chunk_id": metadata.get("chunk_id", "unknown"),
                "preview": preview,
            }
        )
    return formatted


def print_retrieval_results(question: str, chunks: list[Document]) -> None:
    """Print retrieval results in a beginner-friendly terminal format."""
    print(f"\nQuestion: {question}")
    print("-" * 60)

    if not chunks:
        print("No chunks retrieved.")
        return

    # Step 5: Format and display ranked results with citation metadata.
    for item in format_retrieved_chunks(chunks):
        print(f"\n[{item['rank']}] rank={item['rank']}")
        print(f"    source_file={item['source_file']}")
        print(f"    page={item['page']}")
        print(f"    chunk_id={item['chunk_id']}")
        print(f"    text: {item['preview']}")


if __name__ == "__main__":
    print("Phase 3 Retrieval Demo")
    print(f"Chroma path: {CHROMA_PERSIST_DIR.resolve()}")
    print(f"Collection: {CHROMA_COLLECTION_NAME}")
    print("=" * 60)

    for question in DEMO_QUESTIONS:
        chunks = retrieve_context(question, k=5)
        print_retrieval_results(question, chunks)
        print("\n" + "=" * 60)
