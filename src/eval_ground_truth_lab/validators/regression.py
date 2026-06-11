from __future__ import annotations

from eval_ground_truth_lab.validators.result import ValidationResult


def validate_metric_regression(
    *,
    case_id: str,
    metric_name: str,
    baseline_value: float,
    candidate_value: float,
    max_allowed_delta: float,
    validator_id: str,
    category: str,
) -> ValidationResult:
    delta = candidate_value - baseline_value
    passed = delta <= max_allowed_delta
    threshold_status = "pass" if passed else "fail"
    return ValidationResult(
        case_id=case_id,
        validator_id=validator_id,
        passed=passed,
        category=category if not passed else "none",
        message=(
            f"{metric_name} delta {delta:.6g} is {threshold_status}; "
            f"baseline={baseline_value:.6g}, candidate={candidate_value:.6g}, "
            f"max_allowed_delta={max_allowed_delta:.6g}"
        ),
        evidence={
            "metric": metric_name,
            "baseline": baseline_value,
            "candidate": candidate_value,
            "delta": delta,
            "max_allowed_delta": max_allowed_delta,
            "threshold_status": threshold_status,
        },
    )


def validate_cost_regression(
    *,
    case_id: str,
    baseline_cost_usd: float,
    candidate_cost_usd: float,
    max_allowed_delta_usd: float,
) -> ValidationResult:
    return validate_metric_regression(
        case_id=case_id,
        metric_name="cost_usd",
        baseline_value=baseline_cost_usd,
        candidate_value=candidate_cost_usd,
        max_allowed_delta=max_allowed_delta_usd,
        validator_id="regression.cost",
        category="cost_regression",
    )


def validate_latency_regression(
    *,
    case_id: str,
    baseline_latency_ms: float,
    candidate_latency_ms: float,
    max_allowed_delta_ms: float,
) -> ValidationResult:
    return validate_metric_regression(
        case_id=case_id,
        metric_name="latency_ms",
        baseline_value=baseline_latency_ms,
        candidate_value=candidate_latency_ms,
        max_allowed_delta=max_allowed_delta_ms,
        validator_id="regression.latency",
        category="latency_regression",
    )
