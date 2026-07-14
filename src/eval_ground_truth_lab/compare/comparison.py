from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any

from eval_ground_truth_lab.compare.contracts import ThresholdConfig, validate_comparison_inputs
from eval_ground_truth_lab.runs import CaseResult, RunRecord


@dataclass(frozen=True, order=True)
class ValidatorReceiptRegression:
    """One validator that changed from passing to failing for the same case."""

    case_id: str
    validator_id: str
    candidate_category: str


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
    validator_receipt_regressions: tuple[ValidatorReceiptRegression, ...] = ()
    exact_deltas: dict[str, str] = field(default_factory=dict)
    exact_thresholds: dict[str, str] = field(default_factory=dict)

    @property
    def has_blocking_failure(self) -> bool:
        return bool(self.validator_receipt_regressions) or any(
            status == "fail" for status in self.threshold_status.values()
        )


def compare_runs(
    *,
    baseline: RunRecord,
    candidate: RunRecord,
    thresholds: ThresholdConfig,
) -> ComparisonReport:
    validate_comparison_inputs(baseline, candidate, thresholds)

    baseline_metrics = _run_decision_values(baseline)
    candidate_metrics = _run_decision_values(candidate)
    exact_values = {
        metric: candidate_metrics[metric] - baseline_metrics[metric] for metric in baseline_metrics
    }
    exact_limits = {
        "accuracy_delta": _threshold_fraction(thresholds, "max_accuracy_drop"),
        "invalid_output_rate": _threshold_fraction(thresholds, "max_invalid_output_rate_increase"),
        "unsafe_auto_approval_rate": _threshold_fraction(
            thresholds, "max_unsafe_auto_approval_rate_increase"
        ),
        "latency_ms_p95_delta": _threshold_fraction(thresholds, "max_latency_p95_delta_ms"),
        "cost_per_case_delta": _threshold_fraction(thresholds, "max_cost_per_case_delta_usd"),
    }
    validator_receipt_regressions = _validator_receipt_regressions(baseline, candidate)

    threshold_status = {
        "accuracy_delta": _status(
            exact_values["accuracy_delta"] >= -exact_limits["accuracy_delta"]
        ),
        "invalid_output_rate": _status(
            exact_values["invalid_output_rate"] <= exact_limits["invalid_output_rate"]
        ),
        "unsafe_auto_approval_rate": _status(
            exact_values["unsafe_auto_approval_rate"] <= exact_limits["unsafe_auto_approval_rate"]
        ),
        "latency_ms_p95_delta": _status(
            exact_values["latency_ms_p95_delta"] <= exact_limits["latency_ms_p95_delta"]
        ),
        "cost_per_case_delta": _status(
            exact_values["cost_per_case_delta"] <= exact_limits["cost_per_case_delta"]
        ),
    }
    return ComparisonReport(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        dataset_hash=baseline.dataset_hash,
        accuracy_delta=float(exact_values["accuracy_delta"]),
        invalid_output_rate_delta=float(exact_values["invalid_output_rate"]),
        unsafe_auto_approval_rate_delta=float(exact_values["unsafe_auto_approval_rate"]),
        latency_ms_p95_delta=float(exact_values["latency_ms_p95_delta"]),
        cost_per_case_delta=float(exact_values["cost_per_case_delta"]),
        threshold_status=threshold_status,
        validator_receipt_regressions=validator_receipt_regressions,
        exact_deltas={
            metric: _format_exact_fraction(
                value,
                prefer_decimal=metric
                in {
                    "latency_ms_p95_delta",
                    "cost_per_case_delta",
                },
            )
            for metric, value in exact_values.items()
        },
        exact_thresholds={
            "accuracy_delta": thresholds.exact_value("max_accuracy_drop"),
            "invalid_output_rate": thresholds.exact_value("max_invalid_output_rate_increase"),
            "unsafe_auto_approval_rate": thresholds.exact_value(
                "max_unsafe_auto_approval_rate_increase"
            ),
            "latency_ms_p95_delta": thresholds.exact_value("max_latency_p95_delta_ms"),
            "cost_per_case_delta": thresholds.exact_value("max_cost_per_case_delta_usd"),
        },
    )


def _validator_receipt_regressions(
    baseline: RunRecord,
    candidate: RunRecord,
) -> tuple[ValidatorReceiptRegression, ...]:
    baseline_passed = {
        case.case_id: {
            str(receipt["validator_id"]): bool(receipt["passed"])
            for receipt in case.validator_results
        }
        for case in baseline.case_results
    }
    regressions = (
        ValidatorReceiptRegression(
            case_id=case.case_id,
            validator_id=str(receipt["validator_id"]),
            candidate_category=str(receipt["category"]),
        )
        for case in candidate.case_results
        for receipt in case.validator_results
        if baseline_passed[case.case_id][str(receipt["validator_id"])] is True
        and receipt["passed"] is False
    )
    return tuple(sorted(regressions))


def _run_decision_values(run: RunRecord) -> dict[str, Fraction]:
    case_count = len(run.case_results)
    correct_count = sum(1 for result in run.case_results if _is_correct(result))
    invalid_count = sum(
        1
        for result in run.case_results
        if _has_failing_category(result, "invalid_structured_output")
    )
    unsafe_count = sum(
        1 for result in run.case_results if _has_failing_category(result, "unsafe_auto_approval")
    )
    case_costs = tuple(_canonical_fraction(result.cost_usd) for result in run.case_results)
    ordered_latencies = sorted(
        _canonical_fraction(result.latency_ms) for result in run.case_results
    )
    latency_p95_index = max(0, ((95 * case_count + 99) // 100) - 1)
    return {
        "accuracy_delta": Fraction(correct_count, case_count),
        "invalid_output_rate": Fraction(invalid_count, case_count),
        "unsafe_auto_approval_rate": Fraction(unsafe_count, case_count),
        "latency_ms_p95_delta": ordered_latencies[latency_p95_index],
        "cost_per_case_delta": sum(case_costs, start=Fraction()) / case_count,
    }


def _is_correct(case_result: CaseResult) -> bool:
    output = case_result.output
    return isinstance(output, Mapping) and output.get("correct") is True


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


def _threshold_fraction(thresholds: ThresholdConfig, field: str) -> Fraction:
    return Fraction(Decimal(thresholds.exact_value(field)))


def _canonical_fraction(value: float) -> Fraction:
    return Fraction(Decimal(str(value)))


def _format_exact_fraction(value: Fraction, *, prefer_decimal: bool) -> str:
    if value == 0:
        return "0"
    if value.denominator == 1:
        return str(value.numerator)
    if prefer_decimal:
        decimal = _terminating_decimal(value)
        if decimal is not None:
            return decimal
    return f"{value.numerator}/{value.denominator}"


def _terminating_decimal(value: Fraction) -> str | None:
    denominator = value.denominator
    twos = 0
    fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        return None
    scale = max(twos, fives)
    scaled = abs(value.numerator) * (10**scale // value.denominator)
    digits = str(scaled).rjust(scale + 1, "0")
    if scale:
        rendered = f"{digits[:-scale]}.{digits[-scale:]}".rstrip("0").rstrip(".")
    else:
        rendered = digits
    return f"-{rendered}" if value < 0 else rendered
