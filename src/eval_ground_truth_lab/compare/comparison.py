from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.runs import CaseResult, RunRecord


class ComparisonError(RuntimeError):
    """Base error for baseline/candidate comparison failures."""


class DatasetHashMismatchError(ComparisonError):
    """Raised when baseline and candidate runs do not evaluate the same dataset."""


@dataclass(frozen=True)
class ThresholdConfig:
    max_accuracy_drop: float = 0.0
    max_invalid_output_rate_increase: float = 0.0
    max_unsafe_auto_approval_rate_increase: float = 0.0
    max_latency_p95_delta_ms: float = 0.0
    max_cost_per_case_delta_usd: float = 0.0


@dataclass(frozen=True)
class ComparisonReport:
    baseline_run_id: str
    candidate_run_id: str
    dataset_hash: str
    accuracy_delta: float
    invalid_output_rate_delta: float
    unsafe_auto_approval_rate_delta: float
    latency_ms_p95_delta: float
    cost_per_case_delta: float
    threshold_status: dict[str, str]

    @property
    def has_blocking_failure(self) -> bool:
        return any(status == "fail" for status in self.threshold_status.values())


def compare_runs(
    *,
    baseline: RunRecord,
    candidate: RunRecord,
    thresholds: ThresholdConfig,
) -> ComparisonReport:
    if baseline.dataset_hash != candidate.dataset_hash:
        raise DatasetHashMismatchError(
            f"Baseline run {baseline.run_id} dataset hash {baseline.dataset_hash} "
            f"does not match candidate run {candidate.run_id} dataset hash {candidate.dataset_hash}"
        )

    baseline_metrics = _run_metrics(baseline)
    candidate_metrics = _run_metrics(candidate)
    accuracy_delta = candidate_metrics["accuracy"] - baseline_metrics["accuracy"]
    invalid_output_rate_delta = (
        candidate_metrics["invalid_output_rate"] - baseline_metrics["invalid_output_rate"]
    )
    unsafe_auto_approval_rate_delta = (
        candidate_metrics["unsafe_auto_approval_rate"]
        - baseline_metrics["unsafe_auto_approval_rate"]
    )
    latency_ms_p95_delta = candidate.latency_ms_p95 - baseline.latency_ms_p95
    cost_per_case_delta = candidate.cost_per_case_usd - baseline.cost_per_case_usd

    threshold_status = {
        "accuracy_delta": _status(accuracy_delta >= -thresholds.max_accuracy_drop),
        "invalid_output_rate": _status(
            invalid_output_rate_delta <= thresholds.max_invalid_output_rate_increase
        ),
        "unsafe_auto_approval_rate": _status(
            unsafe_auto_approval_rate_delta <= thresholds.max_unsafe_auto_approval_rate_increase
        ),
        "latency_ms_p95_delta": _status(
            latency_ms_p95_delta <= thresholds.max_latency_p95_delta_ms
        ),
        "cost_per_case_delta": _status(
            cost_per_case_delta <= thresholds.max_cost_per_case_delta_usd
        ),
    }
    return ComparisonReport(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        dataset_hash=baseline.dataset_hash,
        accuracy_delta=accuracy_delta,
        invalid_output_rate_delta=invalid_output_rate_delta,
        unsafe_auto_approval_rate_delta=unsafe_auto_approval_rate_delta,
        latency_ms_p95_delta=latency_ms_p95_delta,
        cost_per_case_delta=cost_per_case_delta,
        threshold_status=threshold_status,
    )


def _run_metrics(run: RunRecord) -> dict[str, float]:
    case_count = len(run.case_results)
    if case_count == 0:
        return {
            "accuracy": 0.0,
            "invalid_output_rate": 0.0,
            "unsafe_auto_approval_rate": 0.0,
        }

    correct_count = sum(1 for result in run.case_results if _is_correct(result))
    invalid_count = sum(
        1
        for result in run.case_results
        if _has_failing_category(result, "invalid_structured_output")
    )
    unsafe_count = sum(
        1 for result in run.case_results if _has_failing_category(result, "unsafe_auto_approval")
    )
    return {
        "accuracy": correct_count / case_count,
        "invalid_output_rate": invalid_count / case_count,
        "unsafe_auto_approval_rate": unsafe_count / case_count,
    }


def _is_correct(case_result: CaseResult) -> bool:
    output = case_result.output
    return isinstance(output, dict) and output.get("correct") is True


def _has_failing_category(case_result: CaseResult, category: str) -> bool:
    return any(
        _result_category(result) == category and _result_passed(result) is False
        for result in case_result.validator_results
    )


def _result_category(result: dict[str, Any]) -> str | None:
    return result.get("category")


def _result_passed(result: dict[str, Any]) -> bool | None:
    passed = result.get("passed")
    return passed if isinstance(passed, bool) else None


def _status(passed: bool) -> str:
    return "pass" if passed else "fail"
