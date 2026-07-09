"""Citation verification for PolicyOps Agent.

Only retrieved chunks may be cited. Weak citation coverage lowers confidence
but does not override a useful provisional decision when evidence exists.
"""

from __future__ import annotations

import re

SECTION_ID_REGEX = re.compile(r"\b(TE|RE|GH|RW|AM|DA)-\d{3}\b")


def clean_excerpt(text: str, max_chars: int = 220) -> str:
    """Strip markdown headings and truncate excerpt text for display."""
    cleaned = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


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

        section_title = section
        if section_id and section.startswith(section_id):
            section_title = section[len(section_id) :].strip(" -")

        verified.append(
            {
                "source": source,
                "section": section,
                "section_id": section_id,
                "section_title": section_title or section,
                "supporting_text_excerpt": clean_excerpt(chunk.get("text", ""), max_chars=220),
                "full_text": chunk.get("text", ""),
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

    if decision_result.get("decision") not in {"Needs more information"} and coverage < 0.34:
        warnings.append("Citation coverage is weak for the current decision.")

    return {
        "verified_citations": verified,
        "citation_warnings": warnings,
        "citation_coverage": round(coverage, 2),
    }


def apply_citation_adjustments(decision_result: dict, verification: dict) -> dict:
    """Lower confidence when citations are weak; avoid overriding provisional decisions."""
    adjusted = dict(decision_result)
    confidence = float(adjusted.get("confidence", 0.0))
    warnings = verification.get("citation_warnings", [])
    verified = verification.get("verified_citations", [])

    if warnings:
        confidence = max(0.12, confidence - 0.06 * len(warnings))

    if not verified and adjusted.get("decision") not in {
        "Needs more information",
        "Not allowed",
        "Escalate",
    }:
        confidence = min(confidence, 0.45)
        adjusted["decision"] = "Needs more information"
    elif verified and adjusted.get("decision") == "Needs more information":
        # Keep blocking decisions; do not auto-upgrade here.
        pass

    adjusted["confidence"] = round(confidence, 2)
    return adjusted
