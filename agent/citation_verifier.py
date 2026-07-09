"""Citation verification for PolicyOps Agent Phase 2.

Only retrieved chunks may be cited. This reduces fabricated or unsupported references.
"""

from __future__ import annotations

import re

SECTION_ID_REGEX = re.compile(r"\b(TE|RE|GH|RW|AM|DA)-\d{3}\b")


def _chunk_key(chunk: dict) -> tuple[str, str]:
    return (
        str(chunk.get("source", "")),
        str(chunk.get("section_id") or ""),
    )


def verify_citations(decision_result: dict, retrieved_chunks: list[dict]) -> dict:
    """Verify citations against retrieved chunks only."""
    verified: list[dict] = []
    warnings: list[str] = []

    if not retrieved_chunks:
        warnings.append("No retrieved policy chunks were available for citation verification.")
        return {
            "verified_citations": [],
            "citation_warnings": warnings,
            "citation_coverage": 0.0,
        }

    seen: set[tuple[str, str]] = set()
    for chunk in retrieved_chunks:
        source = chunk.get("source", "unknown")
        section = chunk.get("section", "Unknown section")
        section_id = chunk.get("section_id")

        if not section_id:
            match = SECTION_ID_REGEX.search(section) or SECTION_ID_REGEX.search(
                chunk.get("text", "")
            )
            section_id = match.group(0) if match else None

        key = (source, section_id or section)
        if key in seen:
            continue
        seen.add(key)

        excerpt = (chunk.get("text") or "").strip().replace("\n", " ")
        if len(excerpt) > 180:
            excerpt = excerpt[:180] + "..."

        verified.append(
            {
                "source": source,
                "section": section,
                "section_id": section_id,
                "supporting_text_excerpt": excerpt,
            }
        )

    rationale_count = len(decision_result.get("rationale_bullets", []))
    if rationale_count and verified:
        coverage = min(1.0, len(verified) / max(rationale_count, 1))
    elif verified:
        coverage = 1.0
    else:
        coverage = 0.0

    if decision_result.get("decision") in {"Needs approval", "Allowed", "Escalate"} and not verified:
        warnings.append("Decision was made without verified supporting citations.")

    if decision_result.get("decision") != "Needs more information" and coverage < 0.34:
        warnings.append("Citation coverage is weak for the current decision.")

    return {
        "verified_citations": verified,
        "citation_warnings": warnings,
        "citation_coverage": round(coverage, 2),
    }


def apply_citation_adjustments(decision_result: dict, verification: dict) -> dict:
    """Lower confidence or adjust decision when citations are weak."""
    adjusted = dict(decision_result)
    confidence = float(adjusted.get("confidence", 0.0))
    warnings = verification.get("citation_warnings", [])
    coverage = float(verification.get("citation_coverage", 0.0))

    if warnings:
        confidence = max(0.1, confidence - 0.08 * len(warnings))

    if coverage < 0.34 and adjusted.get("decision") not in {"Needs more information"}:
        confidence = min(confidence, 0.55)
        if not verification.get("verified_citations"):
            adjusted["decision"] = "Needs more information"

    adjusted["confidence"] = round(confidence, 2)
    return adjusted
