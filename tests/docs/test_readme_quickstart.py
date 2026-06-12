from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_root_readme_covers_required_sections() -> None:
    readme = _read("README.md")

    for required_text in (
        "## What This Is",
        "## Why Eval-First Matters",
        "## What Works Today",
        "## Quickstart: Seeded Smoke",
        "## Quickstart: gdev-agent Eval",
        "## Architecture",
        "## Known Gaps",
        "## Roadmap",
        "local-first regression evaluation framework",
        "unsafe auto-approval",
        "run-gdev-agent",
    ):
        assert required_text in readme


def test_root_readme_links_core_evidence() -> None:
    readme = _read("README.md")

    for required_link in (
        "docs/ARCHITECTURE.md",
        "docs/EVIDENCE_INDEX.md",
        "reports/v1/evidence_report.md",
        "#known-gaps",
    ):
        assert required_link in readme


def test_readme_avoids_production_overclaim() -> None:
    readme = _read("README.md")
    docs_readme = _read("docs/README.md")
    combined = f"{readme}\n{docs_readme}"

    assert "local integration proof, not a production eval platform" in combined
    assert "hosted SaaS" in combined
    assert "production-ready" not in combined.lower()
    assert "enterprise eval saas" not in combined.lower()


def test_readme_cli_examples_are_supported() -> None:
    readme = _read("README.md")

    for command in (
        "python -m eval_ground_truth_lab.cli seeded-smoke",
        "python -m eval_ground_truth_lab.cli run-gdev-agent",
    ):
        assert command in readme


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
