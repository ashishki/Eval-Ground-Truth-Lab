from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval_ground_truth_lab import cli
from eval_ground_truth_lab.adapters.base import AdapterResult

ROOT = Path(__file__).resolve().parents[2]


def test_mocked_gdev_eval_smoke_passes_in_ci(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    monkeypatch.setattr(cli, "_build_gdev_adapter", lambda _base_url: _MockGdevAdapter())
    run_dir = tmp_path / "runs"
    report = tmp_path / "reports" / "mocked-gdev.md"

    exit_code = cli.main(
        [
            "run-gdev-agent",
            "--dataset",
            str(ROOT / "datasets/gdev_agent/triage_v1.jsonl"),
            "--base-url",
            "http://mocked-gdev-agent.invalid",
            "--run-id",
            "ci-mocked-gdev-pass",
            "--component-revision",
            "fixture:mocked-ci",
            "--run-dir",
            str(run_dir),
            "--threshold-config",
            str(ROOT / "datasets/gdev_agent/thresholds.json"),
            "--report",
            str(report),
        ]
    )

    run = _load_run(run_dir / "ci-mocked-gdev-pass.json")
    report_text = report.read_text(encoding="utf-8")

    assert exit_code == 0
    assert run["status"] == "completed"
    assert len(run["case_results"]) == 55
    assert all(result["output"]["correct"] is True for result in run["case_results"])
    assert "ci-mocked-gdev-pass" in report_text
    assert "Top Failure Categories" in report_text
    assert "custom_adapter_passthrough" in report_text


def test_mocked_unsafe_regression_exits_one(
    tmp_path: Path,
    monkeypatch,
) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        cli,
        "_build_gdev_adapter",
        lambda _base_url: _MockGdevAdapter(unsafe_case_id="gdev-billing-refund-001"),
    )
    run_dir = tmp_path / "runs"
    report = tmp_path / "reports" / "mocked-gdev-unsafe.md"

    exit_code = cli.main(
        [
            "run-gdev-agent",
            "--dataset",
            str(ROOT / "datasets/gdev_agent/triage_v1.jsonl"),
            "--base-url",
            "http://mocked-gdev-agent.invalid",
            "--run-id",
            "ci-mocked-gdev-unsafe",
            "--component-revision",
            "fixture:mocked-ci",
            "--run-dir",
            str(run_dir),
            "--threshold-config",
            str(ROOT / "datasets/gdev_agent/thresholds.json"),
            "--report",
            str(report),
        ]
    )

    run = _load_run(run_dir / "ci-mocked-gdev-unsafe.json")
    failure_categories = {
        validator["category"]
        for result in run["case_results"]
        for validator in result["validator_results"]
        if validator["passed"] is False
    }

    assert exit_code == 1
    assert "unsafe_auto_approval" in failure_categories
    assert "wrong_routing" in failure_categories
    assert "unsafe_auto_approval" in report.read_text(encoding="utf-8")


def test_docs_separate_ci_smoke_from_live_integration() -> None:
    adapter_docs = (ROOT / "docs/GDEV_AGENT_ADAPTER.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "## CI Mocked Smoke" in adapter_docs
    assert "not require Docker Compose" in adapter_docs
    assert "## Live Local Integration" in adapter_docs
    assert "requires a running `gdev-agent`" in adapter_docs
    assert "Mocked gdev-agent smoke" in workflow
    assert "tests/eval/test_gdev_agent_smoke.py" in workflow
    assert "docker compose" not in workflow


class _MockGdevAdapter:
    def __init__(self, *, unsafe_case_id: str | None = None) -> None:
        self.unsafe_case_id = unsafe_case_id

    def invoke(self, case: dict[str, Any]) -> AdapterResult:
        expected = case["expected"]
        if not isinstance(expected, dict):
            raise AssertionError("gdev smoke case expected field must be a mapping")

        case_id = str(case["id"])
        if case_id == self.unsafe_case_id:
            output = _unsafe_auto_approval_output(case_id=case_id, expected=expected)
        else:
            output = _passing_output(case_id=case_id, expected=expected)
        return AdapterResult(
            output=output,
            status_code=200,
            latency_ms=output["latency_ms"],
            trace_id=f"mock-trace-{case_id}",
            operation_name="candidate.gdev_agent.mocked_ci_smoke",
        )


def _passing_output(*, case_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    guard_blocked = expected.get("guard_behavior") == "block_input"
    return {
        "case_id": case_id,
        "status": expected["expected_status"],
        "category": expected["category"],
        "confidence": 0.97,
        "requires_human": expected["requires_human"],
        "risk_reason": "mocked CI smoke follows expected route",
        "guard_blocked": guard_blocked,
        "invalid_structured_output": False,
        "unsafe_auto_approval": False,
        "adapter_error": False,
        "cost_usd": 0.001,
        "latency_ms": 25.0,
    }


def _unsafe_auto_approval_output(*, case_id: str, expected: dict[str, Any]) -> dict[str, Any]:
    output = _passing_output(case_id=case_id, expected=expected)
    output.update(
        {
            "status": "executed",
            "requires_human": False,
            "risk_reason": "mocked unsafe auto-approval regression",
            "unsafe_auto_approval": True,
        }
    )
    return output


def _load_run(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as run_file:
        return json.load(run_file)
