from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SETUP_PYTHON_SHA = "ece7cb06caefa5fff74198d8649806c4678c61a1"


def test_composite_action_is_pinned_and_keeps_inputs_out_of_shell_source() -> None:
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))

    assert action["runs"]["using"] == "composite"
    assert set(action["outputs"]) == {"report", "conclusion"}
    setup = action["runs"]["steps"][0]
    assert setup["uses"] == f"actions/setup-python@{SETUP_PYTHON_SHA}"
    for step in action["runs"]["steps"]:
        assert "${{ inputs." not in step.get("run", "")
        assert "pip install" not in step.get("run", "")


def test_action_documentation_states_security_and_claim_boundaries() -> None:
    documentation = (ROOT / "docs/GITHUB_ACTION.md").read_text(encoding="utf-8").lower()

    for required in (
        "permissions",
        "persist-credentials: false",
        "github_workspace",
        "synthetic",
        "not a production",
        "case-id sets must match",
        "finite",
        "status `completed`",
        "failure-only or",
        "cannot produce an action pass",
        "validator_receipt_regression",
        "regardless of the candidate failure category",
        "already failing in the baseline",
        "candidate recovery",
        "byte-identical",
        "threshold `version` must equal",
        "runstore-safe",
        "raw-html injection",
        "origin authenticity remain outside",
        "9007199254740991",
        "pre-helper setup failures",
        "action error or missing conclusion",
        "conclusion=error` is never",
        "publishable evidence",
        "writable workspace",
        "report",
        "conclusion",
    ):
        assert required in documentation
