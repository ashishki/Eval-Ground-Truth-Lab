from __future__ import annotations

from eval_ground_truth_lab.cli import comparison_exit_code
from eval_ground_truth_lab.compare import ComparisonReport


def test_blocking_threshold_maps_to_exit_code_one() -> None:
    report = ComparisonReport(
        baseline_run_id="baseline",
        candidate_run_id="candidate",
        dataset_hash="dataset-hash",
        accuracy_delta=-0.2,
        invalid_output_rate_delta=0.0,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=0.0,
        cost_per_case_delta=0.0,
        threshold_status={
            "accuracy_delta": "fail",
            "invalid_output_rate": "pass",
            "unsafe_auto_approval_rate": "pass",
            "latency_ms_p95_delta": "pass",
            "cost_per_case_delta": "pass",
        },
    )

    assert comparison_exit_code(report) == 1
