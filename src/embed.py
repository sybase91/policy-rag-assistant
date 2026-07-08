"""Embed document chunks and store them in a persistent Chroma vector database.

An embedding converts text into a list of numbers that capture meaning.
A vector database stores those numbers so we can search by semantic similarity.
Chroma is a lightweight local vector DB that persists to disk on your machine.
Metadata (source_file, page, chunk_id) travels with each chunk so we can cite
sources later. Retrieval and answer generation depend on this index existing first.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from src.chunk import chunk_documents
from src.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    RAW_DATA_DIR,
)
from src.ingest import load_pdfs

# Placeholder values that mean the user has not set a real API key yet.
_PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "replace_this_with_your_real_key_locally",
    "your_real_key_here",
}

TEST_QUERY = "What is prompt injection?"


def validate_api_key() -> str:
    """Ensure OPENAI_API_KEY is set to a real value in the local .env file."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key in _PLACEHOLDER_API_KEYS:
        print(
            "\nERROR: OpenAI API key is missing or still set to a placeholder.\n"
            "\n"
            "Phase 2 sends text to OpenAI to create embeddings, so a real key is required.\n"
            "\n"
            "What to do:\n"
            "  1. Open the file:  .env\n"
            "  2. Replace the placeholder with your real OpenAI API key:\n"
            "       OPENAI_API_KEY=sk-...\n"
            "  3. Save the file and run this command again.\n"
            "\n"
            "Never commit .env to git. It is listed in .gitignore.\n"
        )
        sys.exit(1)
    return api_key


def get_embeddings() -> OpenAIEmbeddings:
    """Create the OpenAI embedding model that turns text chunks into vectors."""
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def _prepare_chunk_metadata(chunks: list[Document]) -> list[Document]:
    """Ensure metadata types are compatible with Chroma (page stored as string)."""
    prepared: list[Document] = []
    for chunk in chunks:
        metadata = dict(chunk.metadata)
        if "page" in metadata:
            metadata["page"] = str(metadata["page"])
        prepared.append(
            Document(page_content=chunk.page_content, metadata=metadata)
        )
    return prepared


def _collection_has_documents(persist_dir: Path, collection_name: str) -> bool:
    """Return True if a Chroma collection already exists with at least one document."""
    if not persist_dir.exists():
        return False

    try:
        store = Chroma(
            collection_name=collection_name,
            embedding_function=get_embeddings(),
            persist_directory=str(persist_dir),
        )
        return store._collection.count() > 0
    except Exception:
        return False


def _get_indexed_count(vectorstore: Chroma) -> int:
    """Return how many chunks are stored in the Chroma collection."""
    return vectorstore._collection.count()


def build_or_load_vectorstore(
    rebuild: bool = False,
) -> tuple[Chroma, dict]:
    """Build a new Chroma index or load an existing one (idempotent by default).

    Returns the vector store and a stats dictionary for logging.
    """
    stats: dict = {
        "mode": "",
        "pdf_count": 0,
        "page_count": 0,
        "chunk_count": 0,
        "indexed_count": 0,
    }

    # Step 1: Optionally delete the old index so we start fresh.
    if rebuild and CHROMA_PERSIST_DIR.exists():
        shutil.rmtree(CHROMA_PERSIST_DIR)
        stats["mode"] = "rebuild"

    elif (
        not rebuild
        and CHROMA_PERSIST_DIR.exists()
        and _collection_has_documents(CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME)
    ):
        # Step 2a: Load existing index; skip re-indexing to avoid duplicates.
        vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=str(CHROMA_PERSIST_DIR),
        )
        stats["mode"] = "load-existing"
        stats["indexed_count"] = _get_indexed_count(vectorstore)
        return vectorstore, stats

    if not stats["mode"]:
        stats["mode"] = "build-new"

    # Step 2b: Load PDFs and split them into chunks (reuses Phase 1 pipeline).
    pdf_paths = sorted(RAW_DATA_DIR.glob("*.pdf"))
    documents = load_pdfs()
    chunks = chunk_documents(documents)
    prepared_chunks = _prepare_chunk_metadata(chunks)

    stats["pdf_count"] = len(pdf_paths)
    stats["page_count"] = len(documents)
    stats["chunk_count"] = len(prepared_chunks)

    if not prepared_chunks:
        print("No chunks to index. Add PDFs to data/raw/ and try again.")
        sys.exit(1)

    # Step 3: Create embeddings and persist them in Chroma on disk.
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    embeddings = get_embeddings()
    chunk_ids = [chunk.metadata["chunk_id"] for chunk in prepared_chunks]

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    vectorstore.add_documents(prepared_chunks, ids=chunk_ids)

    stats["indexed_count"] = _get_indexed_count(vectorstore)
    return vectorstore, stats


def run_test_search(
    vectorstore: Chroma,
    query: str = TEST_QUERY,
    k: int = 3,
) -> list[Document]:
    """Run a similarity search to confirm the index can find relevant chunks."""
    return vectorstore.similarity_search(query, k=k)


def _print_stats(stats: dict) -> None:
    """Print beginner-friendly progress logs."""
    if stats.get("pdf_count"):
        print(f"PDFs loaded: {stats['pdf_count']}")
    if stats.get("page_count"):
        print(f"Pages loaded: {stats['page_count']}")
    if stats.get("chunk_count"):
        print(f"Chunks created: {stats['chunk_count']}")

    print(f"Chroma collection: {CHROMA_COLLECTION_NAME}")
    print(f"Chroma storage path: {CHROMA_PERSIST_DIR.resolve()}")
    print(f"Mode: {stats['mode']}")

    if stats["mode"] == "load-existing":
        print(f"Loaded existing index: {stats['indexed_count']} chunks")
    else:
        print(f"Chunks indexed: {stats['indexed_count']}")


def _print_search_results(results: list[Document], query: str) -> None:
    """Print the top retrieval results from the smoke-test query."""
    print(f'\n--- Test search: "{query}" ---')
    if not results:
        print("No results returned.")
        return

    for index, doc in enumerate(results, start=1):
        metadata = doc.metadata
        preview = doc.page_content[:300].replace("\n", " ")
        if len(doc.page_content) > 300:
            preview += "..."

        print(f"\n[{index}] source_file={metadata.get('source_file')}")
        print(f"    page={metadata.get('page')}")
        print(f"    chunk_id={metadata.get('chunk_id')}")
        print(f"    text: {preview}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed PDF chunks and store them in a local Chroma vector database."
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete and recreate the local Chroma index",
    )
    args = parser.parse_args()

    # Step 1: Validate that a real OpenAI API key is available locally.
    validate_api_key()

    # Steps 2-4: Build or load the Chroma vector store.
    vectorstore, stats = build_or_load_vectorstore(rebuild=args.rebuild)
    _print_stats(stats)

    # Step 5: Run a test similarity search to verify retrieval works.
    results = run_test_search(vectorstore)
    _print_search_results(results, TEST_QUERY)
