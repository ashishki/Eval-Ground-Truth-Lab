from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ARTIFACTS = [
    "docs/PROJECT_BRIEF.md",
    "docs/ARCHITECTURE.md",
    "docs/spec.md",
    "docs/DECISION_LOG.md",
    "docs/COST_BUDGET.md",
    "docs/EVIDENCE_INDEX.md",
    "docs/KNOWN_LIMITS.md",
    "docs/STACK_OVERVIEW.md",
    "docs/README.md",
    ".github/workflows/ci.yml",
]


def test_required_phase1_artifacts_exist() -> None:
    missing = [path for path in REQUIRED_ARTIFACTS if not (ROOT / path).exists()]
    assert missing == []


def test_no_unresolved_template_placeholders() -> None:
    scanned_paths = [
        *Path(ROOT / "docs").rglob("*.md"),
        ROOT / ".github/workflows/ci.yml",
        ROOT / "pyproject.toml",
    ]
    offenders = {
        str(path.relative_to(ROOT)): re.findall(r"\{\{[^}]+\}\}", path.read_text())
        for path in scanned_paths
        if path.is_file() and re.search(r"\{\{[^}]+\}\}", path.read_text())
    }
    assert offenders == {}


def test_ci_workflow_declares_required_steps() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert 'python-version: "3.12"' in ci
    assert "ruff check src tests" in ci
    assert "ruff format --check src tests" in ci
    assert "python -m pytest tests -q --tb=short" in ci
