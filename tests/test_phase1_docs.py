from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ARTIFACTS = [
    "docs/PROJECT_BRIEF.md",
    "docs/ARCHITECTURE.md",
    "docs/spec.md",
    "docs/tasks.md",
    "docs/CODEX_PROMPT.md",
    "docs/IMPLEMENTATION_CONTRACT.md",
    "docs/DECISION_LOG.md",
    "docs/IMPLEMENTATION_JOURNAL.md",
    "docs/COST_BUDGET.md",
    "docs/EVIDENCE_INDEX.md",
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


def test_tasks_acceptance_criteria_have_verification_fields() -> None:
    tasks = (ROOT / "docs/tasks.md").read_text().splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in tasks:
        if line.startswith("## T"):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)

    missing: list[str] = []
    for block in blocks:
        task_id = block[0].split(":", 1)[0].strip("# ")
        ac_positions = [idx for idx, line in enumerate(block) if line.strip().startswith("- id:")]
        for offset, start in enumerate(ac_positions):
            end = ac_positions[offset + 1] if offset + 1 < len(ac_positions) else len(block)
            ac_text = "\n".join(block[start:end])
            if "test:" not in ac_text and "verify:" not in ac_text:
                missing.append(f"{task_id} criterion at line {start + 1}")

    assert missing == []
