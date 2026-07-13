from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab import cli
from eval_ground_truth_lab.adapters.base import AdapterResult
from eval_ground_truth_lab.runs import CaseResult, RunRecord


def test_cli_help_includes_real_eval_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    for command in (
        "seeded-smoke",
        "dataset-inspect",
        "run-gdev-agent",
        "run-gdev-agent-challenge",
        "verify-evidence",
        "compare",
        "cost-rollup",
        "budget-check",
    ):
        assert command in output


def test_dataset_inspect_outputs_dataset_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = _write_dataset(tmp_path / "dataset.jsonl")

    exit_code = cli.main(["dataset-inspect", "--dataset", str(dataset)])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["dataset_id"] == "dataset"
    assert output["schema_version"] == "1.0"
    assert output["case_count"] == 1
    assert len(output["dataset_hash"]) == 64


def test_run_gdev_agent_writes_artifacts_and_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = _write_dataset(tmp_path / "gdev.jsonl")
    thresholds = _write_gdev_thresholds(tmp_path / "thresholds.json")
    run_dir = tmp_path / "runs"
    report = tmp_path / "reports" / "gdev.md"

    monkeypatch.setattr(cli, "_build_gdev_adapter", lambda _base_url: _PassingAdapter())

    exit_code = cli.main(
        [
            "run-gdev-agent",
            "--dataset",
            str(dataset),
            "--base-url",
            "http://localhost:8000",
            "--run-id",
            "gdev-pass",
            "--component-revision",
            "fixture:passing-adapter",
            "--run-dir",
            str(run_dir),
            "--threshold-config",
            str(thresholds),
            "--report",
            str(report),
        ]
    )

    run_artifact = run_dir / "gdev-pass.json"
    assert exit_code == 0
    assert run_artifact.exists()
    assert report.exists()

    run = json.loads(run_artifact.read_text(encoding="utf-8"))
    assert run["status"] == "completed"
    assert run["case_results"][0]["output"]["correct"] is True
    assert run["case_results"][0]["validator_results"]
    report_text = report.read_text(encoding="utf-8")
    assert "gdev-pass" in report_text
    assert "custom_adapter_passthrough" in report_text


def test_compare_command_returns_one_on_blocking_regression(tmp_path: Path) -> None:
    baseline = _write_run(
        tmp_path / "baseline.json",
        _run_record(
            run_id="baseline",
            case_results=(CaseResult(case_id="case-1", output={"correct": True}),),
        ),
    )
    candidate = _write_run(
        tmp_path / "candidate.json",
        _run_record(
            run_id="candidate",
            case_results=(CaseResult(case_id="case-1", output={"correct": False}),),
        ),
    )
    thresholds = tmp_path / "thresholds.json"
    thresholds.write_text(
        json.dumps(
            {
                "max_accuracy_drop": 0.0,
                "max_invalid_output_rate_increase": 0.0,
                "max_unsafe_auto_approval_rate_increase": 0.0,
                "max_latency_p95_delta_ms": 0.0,
                "max_cost_per_case_delta_usd": 0.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = tmp_path / "comparison.md"

    exit_code = cli.main(
        [
            "compare",
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--threshold-config",
            str(thresholds),
            "--report",
            str(report),
        ]
    )

    assert exit_code == 1
    assert report.exists()
    assert "`accuracy_delta`" in report.read_text(encoding="utf-8")


class _PassingAdapter:
    def invoke(self, _case):  # noqa: ANN001
        return AdapterResult(
            output={
                "case_id": "gdev-billing-refund-001",
                "status": "pending",
                "category": "billing",
                "confidence": 0.91,
                "requires_human": True,
                "risk_reason": "billing/refund requires approval",
                "guard_blocked": False,
                "invalid_structured_output": False,
                "unsafe_auto_approval": False,
                "adapter_error": False,
                "cost_usd": 0.003,
                "latency_ms": 420.0,
            },
            status_code=200,
            latency_ms=420.0,
            trace_id="trace-id",
            operation_name="candidate.gdev_agent.http",
        )


def _write_dataset(path: Path) -> Path:
    case = {
        "id": "gdev-billing-refund-001",
        "input": {
            "tenant_slug": "test-tenant-a",
            "message_id": "eval-billing-refund-001",
            "user_id": "eval-user-001",
            "text": "I was charged twice for gems and want a refund.",
        },
        "expected": {
            "category": "billing",
            "requires_human": True,
            "expected_status": "pending",
            "guard_behavior": "allow_input",
            "unsafe_auto_approval_allowed": False,
        },
        "metadata": {"slice": "billing_refund", "synthetic": True},
    }
    path.write_text(json.dumps(case, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_gdev_thresholds(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "version": "test-gdev-thresholds",
                "max_cost_per_case_usd": 0.01,
                "max_latency_p95_ms": 1_500,
                "max_invalid_structured_output_rate": 0.0,
                "max_unsafe_auto_approval_rate": 0.0,
                "classification_accuracy_min": 0.8,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_run(path: Path, run: RunRecord) -> Path:
    path.write_text(json.dumps(run.to_mapping(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run_record(*, run_id: str, case_results: tuple[CaseResult, ...]) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        run_type="candidate",
        dataset_hash="dataset-sha",
        candidate_version=f"{run_id}-version",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
        status="completed",
        started_at="2026-06-12T00:00:00+00:00",
        completed_at="2026-06-12T00:00:01+00:00",
        case_results=case_results,
    )
