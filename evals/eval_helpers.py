"""Shared helpers for PolicyOps evaluation runners."""

from __future__ import annotations

from unittest.mock import MagicMock

CATEGORY_MOCK_SECTIONS: dict[str, list[str]] = {
    "policy_explanation": ["RW-001", "RW-003", "GH-001", "RE-001", "TE-001", "DA-001", "AM-001"],
    "gifts_hospitality": ["GH-003", "GH-004", "GH-007", "GH-016", "AM-010"],
    "remote_work": ["RW-001", "RW-003", "RW-004", "RW-005", "AM-011"],
    "travel_expense": ["TE-004", "TE-006", "TE-011", "AM-008"],
    "reimbursement": ["RE-004", "RE-005", "TE-030", "AM-009"],
    "data_access": ["DA-003", "DA-004", "DA-007", "DA-018", "AM-012"],
    "multi_turn_memory": ["GH-003", "GH-016", "RW-003", "RW-005", "TE-004", "TE-006"],
    "ambiguity": ["AM-001", "RE-001", "TE-001"],
    "general": ["AM-001", "RE-001", "TE-001", "GH-001"],
    "contradiction_correction": ["GH-003", "RW-003", "DA-003"],
    "prompt_injection": ["GH-003", "DA-003"],
    "retrieval_boundary": [],
    "standard_rag": [],
}


def mock_chunk(
    section_id: str,
    text: str | None = None,
    source: str = "acme_policy.md",
    score: float = 0.84,
) -> dict:
    """Build a normalized mock retrieved chunk."""
    return {
        "text": text or f"Policy text for {section_id}.",
        "source": source,
        "section": f"{section_id} Example Section",
        "section_id": section_id,
        "score": score,
    }


def mock_vectorstore_for_sections(sections: list[str] | None) -> MagicMock:
    """Return a MagicMock vectorstore returning chunks for section IDs."""
    if not sections:
        chunks = []
    else:
        chunks = [mock_chunk(section_id) for section_id in sections]
    docs = []
    for chunk in chunks:
        doc = MagicMock()
        doc.page_content = chunk["text"]
        doc.metadata = {
            "source_file": chunk["source"],
            "section_id": chunk["section_id"],
            "section_title": "Example",
        }
        distance = 1.0 - float(chunk["score"])
        docs.append((doc, distance))
    vectorstore = MagicMock()
    vectorstore.similarity_search_with_score.return_value = docs
    return vectorstore


def mock_vectorstore_for_case(case: dict) -> MagicMock:
    """Build a mock vectorstore from golden or phase4 case fields."""
    sections = case.get("mock_sections")
    if sections is None:
        sections = case.get("expected_sections_any")
    if sections is None:
        must_cite = case.get("must_cite_sections")
        if must_cite:
            sections = must_cite
    if sections is None:
        sections = CATEGORY_MOCK_SECTIONS.get(case.get("category", ""), ["GH-003"])
    if case.get("category") == "retrieval_boundary":
        sections = []
    expanded: list[str] = []
    for section in sections:
        if section.endswith("-"):
            expanded.append(f"{section}001")
        elif len(section) <= 3 and section.isalpha():
            expanded.append(f"{section}-003")
        else:
            expanded.append(section)
    return mock_vectorstore_for_sections(expanded)
