#!/usr/bin/env python3
"""Add or replace Acme Corp mock policies in the Chroma vector index.

By default this script is additive: it only inserts chunks whose chunk_id is new.
Use --replace to delete existing acme_policy chunks before re-ingesting updated
policy text. This does not rebuild or delete the NIST PDF index.

Run python -m src.embed --rebuild first if no Chroma index exists yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.embed import validate_api_key
from src.ingest_policies import chunk_policy_documents, load_markdown_policies
from src.retrieve import get_vectorstore

SMOKE_QUERY = "client dinner reimbursement 18000 INR"


def _existing_chunk_ids(vectorstore) -> set[str]:
    """Return chunk IDs already stored in the collection."""
    try:
        result = vectorstore._collection.get(include=["metadatas"])
        ids = result.get("ids") or []
        return set(ids)
    except Exception:
        return set()


def _delete_acme_policy_chunks(vectorstore) -> int:
    """Delete all chunks tagged as acme_policy from the collection."""
    try:
        result = vectorstore._collection.get(include=["metadatas"])
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []
        remove_ids = [
            chunk_id
            for chunk_id, metadata in zip(ids, metadatas)
            if (metadata or {}).get("doc_type") == "acme_policy"
        ]
        if remove_ids:
            vectorstore._collection.delete(ids=remove_ids)
        return len(remove_ids)
    except Exception:
        return 0


def main() -> None:
    """Load mock policies, optionally replace existing policy chunks, and ingest."""
    parser = argparse.ArgumentParser(description="Ingest Acme Corp mock policies into Chroma")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing acme_policy chunks before ingesting updated policy files",
    )
    args = parser.parse_args()

    validate_api_key()

    policy_docs = load_markdown_policies()
    if not policy_docs:
        print("No mock policy files found in data/policies/mock/.")
        sys.exit(1)

    chunks = chunk_policy_documents(policy_docs)
    if not chunks:
        print("No policy chunks were created.")
        sys.exit(1)

    vectorstore = get_vectorstore()
    removed_count = 0
    if args.replace:
        removed_count = _delete_acme_policy_chunks(vectorstore)
        print(f"Removed existing acme_policy chunks: {removed_count}")

    existing_ids = _existing_chunk_ids(vectorstore)
    new_chunks = [
        chunk for chunk in chunks if chunk.metadata.get("chunk_id") not in existing_ids
    ]

    if new_chunks:
        new_ids = [chunk.metadata["chunk_id"] for chunk in new_chunks]
        vectorstore.add_documents(new_chunks, ids=new_ids)

    total_count = vectorstore._collection.count()
    file_count = len({doc.metadata["source_file"] for doc in policy_docs})

    print("Acme Corp mock policy ingestion complete")
    print(f"Policy files loaded: {file_count}")
    print(f"Policy sections loaded: {len(policy_docs)}")
    print(f"Chunks created from policies: {len(chunks)}")
    print(f"New chunks added this run: {len(new_chunks)}")
    print(f"Total chunks in collection: {total_count}")

    print(f'\nSmoke retrieval query: "{SMOKE_QUERY}"')
    results = vectorstore.similarity_search(SMOKE_QUERY, k=3)
    if not results:
        print("No retrieval results returned.")
        return

    for index, doc in enumerate(results, start=1):
        metadata = doc.metadata
        preview = doc.page_content[:180].replace("\n", " ")
        print(
            f"\n[{index}] {metadata.get('source_file')} | "
            f"{metadata.get('section_id')} {metadata.get('section_title')}"
        )
        print(f"    {preview}...")


if __name__ == "__main__":
    main()
