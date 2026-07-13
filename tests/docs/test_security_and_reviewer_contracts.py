from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_SHA = "93cb6efe18208431cddfb8368fd83d5badbf9bfd"
SETUP_PYTHON_SHA = "ece7cb06caefa5fff74198d8649806c4678c61a1"


def test_ci_uses_least_privilege_and_exact_action_commits() -> None:
    workflow_path = ROOT / ".github/workflows/ci.yml"
    source = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)

    assert workflow["permissions"] == {"contents": "read"}
    steps = workflow["jobs"]["test"]["steps"]
    action_steps = [step for step in steps if "uses" in step]
    assert [step["uses"] for step in action_steps] == [
        f"actions/checkout@{CHECKOUT_SHA}",
        f"actions/setup-python@{SETUP_PYTHON_SHA}",
        "./",
    ]
    assert re.findall(r"uses:\s+[^\s@]+@([^\s#]+)", source) == [
        CHECKOUT_SHA,
        SETUP_PYTHON_SHA,
    ]
    assert action_steps[0]["with"]["persist-credentials"] is False
    assert (ROOT / "action.yml").is_file()


def test_reviewer_path_bootstraps_python3_before_module_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## 5-Minute Reviewer Path", 1)[1].split(
        "## Quickstart: Seeded Smoke", 1
    )[0]
    ordered_commands = (
        "git clone https://github.com/ashishki/Eval-Ground-Truth-Lab.git",
        "cd Eval-Ground-Truth-Lab",
        "python3 -m venv .venv",
        ".venv/bin/python -m pip install -r requirements-dev.txt -e .",
        ".venv/bin/python -m eval_ground_truth_lab.cli seeded-smoke",
        'test "$smoke_status" -eq 1',
        ".venv/bin/python -m eval_ground_truth_lab.cli verify-evidence",
    )

    positions = [section.index(command) for command in ordered_commands]
    assert positions == sorted(positions)
    assert "\npython -m " not in section
    assert "verified: true" in section
    assert "eight artifacts" in section
