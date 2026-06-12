from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab import cli
from eval_ground_truth_lab.cost import check_budget
from eval_ground_truth_lab.judging.telemetry import CostTelemetryEntry, JsonlTelemetrySink


def test_budget_check_exits_one_on_overrun() -> None:
    rollup = {
        "total_cost_usd": 2.5,
        "judge_call_count": 11,
        "cost_by_case": {"case-1": 0.2, "case-2": 1.25},
    }
    policy = {
        "per_run_budget_usd": 2.0,
        "monthly_project_budget_usd": 2.4,
        "cost_per_case_ceiling": 1.0,
        "judge_call_count_ceiling": 10,
    }

    result = check_budget(rollup, policy)

    assert result.passed is False
    assert {failure.gate for failure in result.failures} == {
        "per_run_budget_usd",
        "monthly_project_budget_usd",
        "cost_per_case_ceiling",
        "judge_call_count_ceiling",
    }


def test_budget_check_uses_fixture_telemetry(
    tmp_path: Path,
    capsys,
) -> None:  # noqa: ANN001
    telemetry_path = tmp_path / "fixture-telemetry.jsonl"
    rollup_path = tmp_path / "latest-rollup.json"
    policy_path = tmp_path / "cost-policy.json"
    sink = JsonlTelemetrySink(telemetry_path)
    sink.emit(
        CostTelemetryEntry(
            project="eval-ground-truth-lab",
            workflow="ci-fixture",
            role="judge",
            model="fixture-judge",
            environment="ci",
            case_id="case-1",
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.001,
            latency_ms=50.0,
            retry_count=0,
            tool_call_count=0,
            quality_outcome="accepted",
        )
    )
    policy_path.write_text(
        json.dumps(
            {
                "per_run_budget_usd": 0.01,
                "monthly_project_budget_usd": 1.0,
                "cost_per_case_ceiling": 0.01,
                "judge_call_count_ceiling": 2,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    rollup_exit = cli.main(
        [
            "cost-rollup",
            "--telemetry",
            str(telemetry_path),
            "--out",
            str(rollup_path),
        ]
    )
    budget_exit = cli.main(
        [
            "budget-check",
            "--rollup",
            str(rollup_path),
            "--policy",
            str(policy_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert rollup_exit == 0
    assert budget_exit == 0
    assert rollup_path.exists()
    assert output["passed"] is True
    assert output["failures"] == []
