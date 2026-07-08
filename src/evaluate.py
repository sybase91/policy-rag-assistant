"""Phase 6: basic v0.1 RAG evaluation harness.

A gold question is a labeled test item with an expected source, keywords,
and behavior (answer vs refuse). Evaluation matters because a demo can look
good while retrieval or grounding fails silently.

This script is intentionally simple (v0.1):
- source hit rate checks whether the expected PDF appears in returned sources
- keyword hit rate counts expected phrases found in the answer text
- refusal behavior checks that unsupported questions are refused clearly

It is not RAGAS, not an LLM-as-judge, and not a perfect quality auditor.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from src.config import CHROMA_PERSIST_DIR
from src.generate import REFUSAL_MESSAGE, answer_question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLD_CSV_PATH = PROJECT_ROOT / "evals" / "gold_questions.csv"
RESULTS_CSV_PATH = PROJECT_ROOT / "evals" / "eval_results.csv"
REPORT_MD_PATH = PROJECT_ROOT / "reports" / "evaluation_report.md"

_PLACEHOLDER_API_KEYS = {
    "",
    "your_openai_api_key_here",
    "replace_this_with_your_real_key_locally",
    "your_real_key_here",
}

RESULT_FIELDS = [
    "id",
    "question",
    "expected_source",
    "expected_behavior",
    "source_hit",
    "keyword_hit_count",
    "keyword_total",
    "keyword_hit_rate",
    "refused_correctly",
    "passed",
    "retrieved_context_count",
    "answer",
]


def get_setup_error() -> str | None:
    """Return a setup error message, or None if evaluation can run."""
    if not GOLD_CSV_PATH.exists():
        return (
            f"Gold questions file not found: {GOLD_CSV_PATH}\n"
            "Create evals/gold_questions.csv before running evaluation."
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key in _PLACEHOLDER_API_KEYS:
        return (
            "OpenAI API key is missing or still a placeholder.\n"
            "Edit your local .env file and set OPENAI_API_KEY, then retry."
        )

    chroma_db_file = CHROMA_PERSIST_DIR / "chroma.sqlite3"
    if not CHROMA_PERSIST_DIR.exists() or not chroma_db_file.exists():
        return (
            "No Chroma index found.\n"
            "Run: python -m src.embed --rebuild"
        )

    return None


def load_gold_questions(path: Path) -> list[dict]:
    """Load gold questions and parse pipe-separated expected keywords."""
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "id",
            "question",
            "expected_source",
            "expected_keywords",
            "expected_behavior",
        }
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "gold_questions.csv is missing required columns: "
                "id, question, expected_source, expected_keywords, expected_behavior"
            )

        for raw in reader:
            keywords_raw = (raw.get("expected_keywords") or "").strip()
            keywords = [
                part.strip()
                for part in keywords_raw.split("|")
                if part.strip()
            ]
            rows.append(
                {
                    "id": (raw.get("id") or "").strip(),
                    "question": (raw.get("question") or "").strip(),
                    "expected_source": (raw.get("expected_source") or "").strip(),
                    "expected_keywords": keywords,
                    "expected_behavior": (raw.get("expected_behavior") or "").strip().lower(),
                }
            )
    return rows


def check_source_hit(
    expected_source: str,
    sources: list[dict],
    answer: str,
) -> bool:
    """Return True if the expected source was retrieved (or refuse when none)."""
    if expected_source.lower() == "none":
        return REFUSAL_MESSAGE.lower() in answer.lower()

    source_files = [
        str(item.get("source_file", "")).lower()
        for item in sources
    ]
    expected = expected_source.lower()
    return any(expected in source_file for source_file in source_files)


def score_keywords(answer: str, keywords: list[str]) -> tuple[int, int, float]:
    """Count case-insensitive keyword hits in the answer text."""
    total = len(keywords)
    if total == 0:
        return 0, 0, 0.0

    answer_lower = answer.lower()
    hit_count = sum(1 for keyword in keywords if keyword.lower() in answer_lower)
    return hit_count, total, hit_count / total


def check_refused_correctly(expected_behavior: str, answer: str) -> bool:
    """True when a refuse row contains the grounded refusal message."""
    if expected_behavior != "refuse":
        return False
    return REFUSAL_MESSAGE.lower() in answer.lower()


def row_passed(
    expected_behavior: str,
    source_hit: bool,
    keyword_hit_rate: float,
    refused_correctly: bool,
) -> bool:
    """Apply v0.1 pass rules for answer vs refuse rows."""
    if expected_behavior == "refuse":
        return refused_correctly
    return source_hit and keyword_hit_rate >= 0.5


def evaluate_one(gold: dict) -> dict:
    """Run one gold question through answer_question and score the result."""
    question = gold["question"]
    expected_behavior = gold["expected_behavior"]
    expected_source = gold["expected_source"]
    keywords = gold["expected_keywords"]

    try:
        result = answer_question(question)
        answer = str(result.get("answer", ""))
        sources = result.get("sources", []) or []
        retrieved_context_count = int(result.get("retrieved_context_count", 0))
    except Exception as exc:  # noqa: BLE001 - keep eval run going
        print(f"  ERROR on {gold['id']}: {exc}")
        answer = f"ERROR: {exc}"
        sources = []
        retrieved_context_count = 0

    source_hit = check_source_hit(expected_source, sources, answer)
    keyword_hit_count, keyword_total, keyword_hit_rate = score_keywords(
        answer, keywords
    )
    refused_correctly = check_refused_correctly(expected_behavior, answer)
    passed = row_passed(
        expected_behavior,
        source_hit,
        keyword_hit_rate,
        refused_correctly,
    )

    return {
        "id": gold["id"],
        "question": question,
        "expected_source": expected_source,
        "expected_behavior": expected_behavior,
        "source_hit": source_hit,
        "keyword_hit_count": keyword_hit_count,
        "keyword_total": keyword_total,
        "keyword_hit_rate": round(keyword_hit_rate, 4),
        "refused_correctly": refused_correctly,
        "passed": passed,
        "retrieved_context_count": retrieved_context_count,
        "answer": answer,
    }


def write_results_csv(rows: list[dict], path: Path) -> None:
    """Save detailed per-question metrics to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in RESULT_FIELDS})


def _failure_reason(row: dict) -> str:
    """Short reason for a failed row (used in the markdown report)."""
    if str(row.get("answer", "")).startswith("ERROR:"):
        return "Runtime error while calling answer_question()"
    if row["expected_behavior"] == "refuse":
        return "Expected refusal message was missing"
    reasons: list[str] = []
    if not row["source_hit"]:
        reasons.append("expected source not in retrieved sources")
    if float(row["keyword_hit_rate"]) < 0.5:
        reasons.append(
            f"keyword_hit_rate {row['keyword_hit_rate']} < 0.5"
        )
    return "; ".join(reasons) if reasons else "Did not meet pass criteria"


def write_report_md(rows: list[dict], metrics: dict, path: Path) -> None:
    """Write a beginner-friendly evaluation report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    failed = [row for row in rows if not row["passed"]]
    timestamp = metrics["timestamp"]

    lines = [
        "# RAG Evaluation Report (v0.1)",
        "",
        f"**Evaluation date/time:** {timestamp}",
        "",
        "## What was tested",
        "",
        "This report covers a simple Phase 6 evaluation harness for the",
        "Enterprise AI Policy RAG Assistant. For each gold question, the",
        "script called `answer_question()` and scored:",
        "",
        "- Whether the expected source PDF appeared in retrieved sources",
        "- How many expected keywords appeared in the generated answer",
        "- Whether unsupported questions were refused correctly",
        "",
        "This is a **v0.1 / simple harness**. It is not RAGAS and not an",
        "LLM-as-judge. It uses transparent rules so beginners can understand",
        "and debug failures.",
        "",
        "## Dataset size",
        "",
        f"- Total gold questions: **{metrics['total']}**",
        f"- Answerable questions: **{metrics['answer_count']}**",
        f"- Refuse questions: **{metrics['refuse_count']}**",
        "",
        "## Metrics explained (beginner-friendly)",
        "",
        "| Metric | Meaning |",
        "|--------|---------|",
        "| **Source hit rate** | Share of questions where the expected source check passed "
        "(for refuse/`none` rows: refusal text present). |",
        "| **Keyword hit rate** | Average share of expected phrases found in answers "
        "(computed on answerable rows only). |",
        "| **Refusal accuracy** | Share of refuse questions that included the exact "
        "grounded refusal message. |",
        "| **Pass rate** | Share of questions that met the v0.1 pass rule. |",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total questions | {metrics['total']} |",
        f"| Total passed | {metrics['passed']} |",
        f"| Pass rate | {metrics['pass_rate']:.2%} |",
        f"| Source hit rate | {metrics['source_hit_rate']:.2%} |",
        f"| Average keyword hit rate | {metrics['avg_keyword_hit_rate']:.2%} |",
        f"| Refusal accuracy | {metrics['refusal_accuracy']:.2%} |",
        "",
        "## Failed cases",
        "",
    ]

    if not failed:
        lines.append("None. All gold questions passed the v0.1 rules.")
        lines.append("")
    else:
        lines.extend(
            [
                "| ID | Expected behavior | Reason |",
                "|----|-------------------|--------|",
            ]
        )
        for row in failed:
            lines.append(
                f"| {row['id']} | {row['expected_behavior']} | {_failure_reason(row)} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Limitations",
            "",
            "- Keyword matching is case-insensitive substring matching, not semantic.",
            "- Source hit checks filename presence, not page-level citation quality.",
            "- Refusal checks a fixed refusal string, not all valid refuse phrasings.",
            "- Small gold set (10 questions); not statistically strong.",
            "- No RAGAS / faithfulness / LLM-as-judge scoring yet.",
            "",
            "## Next improvements",
            "",
            "- Expand the gold set and add more refusal edge cases",
            "- Add page-level citation checks",
            "- Add retrieval-only metrics before generation",
            "- Consider RAGAS or LLM-as-judge later for richer scoring",
            "- Track evaluation history across model/prompt changes",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def compute_metrics(rows: list[dict]) -> dict:
    """Aggregate pass / source / keyword / refusal metrics."""
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    source_hits = sum(1 for row in rows if row["source_hit"])

    answer_rows = [row for row in rows if row["expected_behavior"] == "answer"]
    refuse_rows = [row for row in rows if row["expected_behavior"] == "refuse"]

    if answer_rows:
        avg_keyword = sum(float(row["keyword_hit_rate"]) for row in answer_rows) / len(
            answer_rows
        )
    else:
        avg_keyword = 0.0

    if refuse_rows:
        refusal_accuracy = sum(
            1 for row in refuse_rows if row["refused_correctly"]
        ) / len(refuse_rows)
    else:
        refusal_accuracy = 0.0

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": passed,
        "pass_rate": (passed / total) if total else 0.0,
        "source_hit_rate": (source_hits / total) if total else 0.0,
        "avg_keyword_hit_rate": avg_keyword,
        "refusal_accuracy": refusal_accuracy,
        "answer_count": len(answer_rows),
        "refuse_count": len(refuse_rows),
        "failed_ids": [row["id"] for row in rows if not row["passed"]],
    }


def print_summary(metrics: dict) -> None:
    """Print a clean terminal summary of the evaluation run."""
    failed = metrics["failed_ids"]
    failed_text = ", ".join(failed) if failed else "(none)"

    print("Phase 6 RAG Evaluation (v0.1)")
    print(f"Total questions: {metrics['total']}")
    print(f"Passed: {metrics['passed']}")
    print(f"Pass rate: {metrics['pass_rate']:.2%}")
    print(f"Source hit rate: {metrics['source_hit_rate']:.2%}")
    print(f"Average keyword hit rate: {metrics['avg_keyword_hit_rate']:.2%}")
    print(f"Refusal accuracy: {metrics['refusal_accuracy']:.2%}")
    print(f"Failed question IDs: {failed_text}")
    print(f"Wrote: {RESULTS_CSV_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {REPORT_MD_PATH.relative_to(PROJECT_ROOT)}")


def main() -> None:
    """Run the Phase 6 evaluation harness end to end."""
    setup_error = get_setup_error()
    if setup_error:
        print(setup_error, file=sys.stderr)
        sys.exit(1)

    gold_rows = load_gold_questions(GOLD_CSV_PATH)
    if not gold_rows:
        print("gold_questions.csv has no data rows.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(gold_rows)} gold questions from {GOLD_CSV_PATH.name}")
    print("Running answer_question() for each gold item...\n")

    result_rows: list[dict] = []
    for index, gold in enumerate(gold_rows, start=1):
        print(f"[{index}/{len(gold_rows)}] {gold['id']}: {gold['question']}")
        result_rows.append(evaluate_one(gold))

    metrics = compute_metrics(result_rows)
    write_results_csv(result_rows, RESULTS_CSV_PATH)
    write_report_md(result_rows, metrics, REPORT_MD_PATH)
    print()
    print_summary(metrics)


if __name__ == "__main__":
    main()
