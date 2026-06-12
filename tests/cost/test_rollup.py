from __future__ import annotations

from pathlib import Path

import pytest

from eval_ground_truth_lab.cost import rollup_telemetry
from eval_ground_truth_lab.judging.telemetry import CostTelemetryEntry, JsonlTelemetrySink


def test_cost_rollup_reads_jsonl_telemetry(tmp_path: Path) -> None:
    telemetry_path = tmp_path / "telemetry.jsonl"
    sink = JsonlTelemetrySink(telemetry_path)
    sink.emit(
        CostTelemetryEntry(
            project="eval-ground-truth-lab",
            workflow="gdev-eval",
            role="judge",
            model="judge-small",
            environment="ci-fixture",
            case_id="case-1",
            input_tokens=100,
            output_tokens=50,
            estimated_cost_usd=0.02,
            latency_ms=100.0,
            retry_count=0,
            tool_call_count=0,
            quality_outcome="accepted",
        )
    )
    sink.emit(
        CostTelemetryEntry(
            project="eval-ground-truth-lab",
            workflow="gdev-eval",
            role="judge",
            model="judge-small",
            environment="ci-fixture",
            case_id="case-2",
            input_tokens=120,
            output_tokens=80,
            estimated_cost_usd=0.03,
            latency_ms=250.0,
            retry_count=1,
            tool_call_count=0,
            quality_outcome="ambiguous",
        )
    )
    sink.emit(
        CostTelemetryEntry(
            project="eval-ground-truth-lab",
            workflow="judge-calibration",
            role="judge",
            model="judge-large",
            environment="ci-fixture",
            case_id="case-1",
            input_tokens=60,
            output_tokens=10,
            estimated_cost_usd=0.05,
            latency_ms=500.0,
            retry_count=0,
            tool_call_count=0,
            quality_outcome="accepted",
        )
    )

    rollup = rollup_telemetry(telemetry_path)

    assert rollup["entry_count"] == 3
    assert rollup["judge_call_count"] == 3
    assert rollup["total_cost_usd"] == pytest.approx(0.10)
    assert rollup["total_tokens"] == 420
    assert rollup["cost_by_model"] == {"judge-large": 0.05, "judge-small": 0.05}
    assert rollup["cost_by_workflow"] == {
        "gdev-eval": 0.05,
        "judge-calibration": 0.05,
    }
    assert rollup["cost_by_case"] == {"case-1": 0.07, "case-2": 0.03}
    assert rollup["latency_p95"] == 500.0
    assert rollup["retry_count"] == 1
    assert rollup["quality_outcome_distribution"] == {"accepted": 2, "ambiguous": 1}
