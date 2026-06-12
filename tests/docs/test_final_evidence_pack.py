from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_has_5_minute_reviewer_path() -> None:
    readme = _read("README.md")

    for required_text in (
        "## 5-Minute Reviewer Path",
        "seeded-smoke",
        "run-gdev-agent",
        "docs/EVIDENCE_INDEX.md",
        "docs/KNOWN_LIMITS.md",
        "reports/gdev-agent/baseline_report.md",
        "reports/gdev-agent/baseline_report.html",
        "Known Gaps",
    ):
        assert required_text in readme


def test_case_study_answers_required_questions() -> None:
    case_study = _read("docs/CASE_STUDY.md")

    for required_text in (
        "What Eval Lab Evaluates",
        "Dataset Versioning",
        "Baseline Candidate Comparison",
        "Deterministic Validators",
        "Unsafe Auto-Approval",
        "gdev-agent Eval",
        "Synthetic vs Real Integration",
        "Cost and Latency",
        "Non-Authoritative Judge",
        "Known Limits",
    ):
        assert required_text in case_study


def test_evidence_index_maps_final_claims() -> None:
    evidence_index = _read("docs/EVIDENCE_INDEX.md")

    for required_text in (
        "Final claim: dataset versioning",
        "Final claim: baseline candidate comparison",
        "Final claim: unsafe auto-approval",
        "Final claim: gdev-agent eval",
        "Final claim: cost and latency",
        "Final claim: non-authoritative judge",
        "Final claim: known limits",
        "reports/gdev-agent/baseline_report.html",
        "docs/CASE_STUDY.md",
        "docs/KNOWN_LIMITS.md",
    ):
        assert required_text in evidence_index


def test_docs_avoid_production_overclaim() -> None:
    combined = "\n".join(
        [
            _read("README.md"),
            _read("docs/CASE_STUDY.md"),
            _read("docs/KNOWN_LIMITS.md"),
            _read("docs/REPORTING.md"),
        ]
    )
    lower = combined.lower()

    assert "not a production eval platform" in lower
    assert "production-ready" not in lower
    assert "enterprise eval saas" not in lower


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
