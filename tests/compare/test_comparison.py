from __future__ import annotations

import pytest

from eval_ground_truth_lab.compare import DatasetHashMismatchError, ThresholdConfig, compare_runs
from eval_ground_truth_lab.runs import CaseResult, RunRecord


def test_rejects_mismatched_dataset_hashes() -> None:
    baseline = _run_record(
        run_id="baseline",
        dataset_hash="dataset-a",
        case_results=(_case("case-1", correct=True),),
    )
    candidate = _run_record(
        run_id="candidate",
        dataset_hash="dataset-b",
        case_results=(_case("case-1", correct=True),),
    )

    with pytest.raises(DatasetHashMismatchError):
        compare_runs(
            baseline=baseline,
            candidate=candidate,
            thresholds=ThresholdConfig(version="thresholds-v1"),
        )


def test_comparison_outputs_required_metrics() -> None:
    baseline = _run_record(
        run_id="baseline",
        dataset_hash="dataset-a",
        cost_per_case_usd=0.10,
        latency_ms_p95=100.0,
        case_results=(
            _case("case-1", correct=True, cost_usd=0.10, latency_ms=100.0),
            _case("case-2", correct=True, cost_usd=0.10, latency_ms=100.0),
        ),
    )
    candidate = _run_record(
        run_id="candidate",
        dataset_hash="dataset-a",
        cost_per_case_usd=0.18,
        latency_ms_p95=130.0,
        case_results=(
            _case("case-1", correct=True, cost_usd=0.18, latency_ms=130.0),
            _case(
                "case-2",
                correct=False,
                cost_usd=0.18,
                latency_ms=130.0,
                invalid=True,
                unsafe=True,
            ),
        ),
    )

    report = compare_runs(
        baseline=baseline,
        candidate=candidate,
        thresholds=ThresholdConfig(
            max_accuracy_drop=0.1,
            max_invalid_output_rate_increase=0.2,
            max_unsafe_auto_approval_rate_increase=0.2,
            max_latency_p95_delta_ms=20.0,
            max_cost_per_case_delta_usd=0.05,
            version="thresholds-v1",
        ),
    )

    assert report.accuracy_delta == -0.5
    assert report.invalid_output_rate_delta == 0.5
    assert report.unsafe_auto_approval_rate_delta == 0.5
    assert report.latency_ms_p95_delta == 30.0
    assert report.cost_per_case_delta == pytest.approx(0.08)
    assert report.threshold_status == {
        "accuracy_delta": "fail",
        "invalid_output_rate": "fail",
        "unsafe_auto_approval_rate": "fail",
        "latency_ms_p95_delta": "fail",
        "cost_per_case_delta": "fail",
    }


def _run_record(
    *,
    run_id: str,
    dataset_hash: str,
    cost_per_case_usd: float = 0.0,
    latency_ms_p95: float = 0.0,
    case_results: tuple[CaseResult, ...] = (),
) -> RunRecord:
    costs = [case.cost_usd for case in case_results]
    latencies = sorted(case.latency_ms for case in case_results)
    return RunRecord(
        run_id=run_id,
        run_type="candidate",
        dataset_hash=dataset_hash,
        candidate_version=f"{run_id}-version",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
        status="completed",
        started_at="2026-06-11T00:00:00+00:00",
        completed_at="2026-06-11T00:00:01+00:00",
        cost_total_usd=sum(costs),
        cost_per_case_usd=cost_per_case_usd,
        latency_ms_p50=latencies[0] if latencies else 0.0,
        latency_ms_p95=latency_ms_p95,
        case_results=case_results,
    )


def _case(
    case_id: str,
    *,
    correct: bool,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    invalid: bool = False,
    unsafe: bool = False,
) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        output={"correct": correct},
        validator_results=(
            {
                "validator_id": "structured_output.required_fields",
                "passed": not invalid,
                "category": "invalid_structured_output" if invalid else "none",
            },
            {
                "validator_id": "safety.unsafe_auto_approval",
                "passed": not unsafe,
                "category": "unsafe_auto_approval" if unsafe else "none",
            },
        ),
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
