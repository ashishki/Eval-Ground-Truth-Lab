from __future__ import annotations

import pytest

from eval_ground_truth_lab.validators import validate_cost_regression, validate_latency_regression


def test_cost_latency_threshold_deltas() -> None:
    cost = validate_cost_regression(
        case_id="case-001",
        baseline_cost_usd=0.10,
        candidate_cost_usd=0.18,
        max_allowed_delta_usd=0.05,
    )
    latency = validate_latency_regression(
        case_id="case-001",
        baseline_latency_ms=100.0,
        candidate_latency_ms=112.0,
        max_allowed_delta_ms=20.0,
    )

    assert cost.validator_id == "regression.cost"
    assert cost.passed is False
    assert cost.category == "cost_regression"
    assert cost.evidence["delta"] == pytest.approx(0.08)
    assert cost.evidence["threshold_status"] == "fail"
    assert latency.validator_id == "regression.latency"
    assert latency.passed is True
    assert latency.evidence["delta"] == 12.0
    assert latency.evidence["threshold_status"] == "pass"
