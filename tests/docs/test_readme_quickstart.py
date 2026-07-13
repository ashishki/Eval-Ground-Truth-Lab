from __future__ import annotations

from pathlib import Path

import pytest

from eval_ground_truth_lab.cli import main

ROOT = Path(__file__).resolve().parents[2]


def test_root_readme_covers_required_sections() -> None:
    readme = _read("README.md")

    for required_text in (
        "## What This Is",
        "## Why Eval-First Matters",
        "## What Works Today",
        "## Quickstart: Seeded Smoke",
        "## Quickstart: gdev-agent Eval",
        "## Quickstart: gdev-agent Challenge",
        "## Architecture",
        "## Known Gaps",
        "## Roadmap",
        "local-first regression gate",
        "## Current Maturity",
        "## Relationship to the Portfolio",
        "## Product Boundary and Non-Goals",
        "unsafe auto-approval",
        "run-gdev-agent",
        "verify-evidence",
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

    supported_commands = (
        ("seeded-smoke", "python -m eval_ground_truth_lab.cli seeded-smoke"),
        ("run-gdev-agent", "python -m eval_ground_truth_lab.cli run-gdev-agent"),
        ("run-gdev-agent-challenge", "eval-ground-truth-lab run-gdev-agent-challenge"),
        ("verify-evidence", "eval-ground-truth-lab verify-evidence"),
    )

    for command, example in supported_commands:
        assert example in readme
        with pytest.raises(SystemExit) as exc:
            main([command, "--help"])
        assert exc.value.code == 0


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
