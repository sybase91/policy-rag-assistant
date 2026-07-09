"""Load and chunk Acme Corp mock policy Markdown files for vector indexing.

Markdown policies are split by section headers so each chunk keeps a stable
section_id for citations in the PolicyOps Agent workflow.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_OVERLAP, CHUNK_SIZE, MOCK_POLICY_DIR

# Match headers like: ## TE-004 Client Meal Thresholds
SECTION_HEADER_PATTERN = re.compile(
    r"^##\s+([A-Z]{2}-\d{3})\s+(.+)$",
    re.MULTILINE,
)


def _extract_policy_name(text: str, fallback: str) -> str:
    """Read the top-level Markdown title from the file."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_markdown_policies(policy_dir: Path | None = None) -> list[Document]:
    """Load Markdown policy files and split them into section-level documents."""
    directory = policy_dir or MOCK_POLICY_DIR
    if not directory.exists():
        return []

    documents: list[Document] = []
    for md_path in sorted(directory.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        policy_name = _extract_policy_name(text, md_path.stem.replace("_", " "))
        relative_source_path = str(md_path.relative_to(directory.parent.parent.parent))

        matches = list(SECTION_HEADER_PATTERN.finditer(text))
        if not matches:
            documents.append(
                Document(
                    page_content=text.strip(),
                    metadata={
                        "source_file": md_path.name,
                        "policy_name": policy_name,
                        "section_id": "FULL",
                        "section_title": policy_name,
                        "source_path": relative_source_path,
                        "doc_type": "acme_policy",
                    },
                )
            )
            continue

        for index, match in enumerate(matches):
            section_id = match.group(1)
            section_title = match.group(2).strip()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()

            documents.append(
                Document(
                    page_content=section_text,
                    metadata={
                        "source_file": md_path.name,
                        "policy_name": policy_name,
                        "section_id": section_id,
                        "section_title": section_title,
                        "source_path": relative_source_path,
                        "doc_type": "acme_policy",
                    },
                )
            )

    return documents


def chunk_policy_documents(
    documents: list[Document] | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Chunk policy sections while preserving section metadata and stable chunk IDs."""
    if documents is None:
        documents = load_markdown_policies()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[Document] = []
    for doc in documents:
        metadata = dict(doc.metadata)
        source_file = metadata.get("source_file", "unknown.md")
        section_id = metadata.get("section_id", "FULL")

        if len(doc.page_content) <= chunk_size:
            split_docs = [doc]
        else:
            split_docs = splitter.split_documents([doc])

        for chunk_index, chunk in enumerate(split_docs):
            chunk.metadata = dict(metadata)
            chunk.metadata["chunk_id"] = (
                f"{source_file}_s{section_id}_c{chunk_index:03d}"
            )
            chunks.append(chunk)

    return chunks
