from __future__ import annotations

from eval_ground_truth_lab.validators import (
    GdevValidatorThresholds,
    validate_gdev_case,
    validate_no_unsafe_auto_approval,
)


def test_candidate_cannot_self_report_correctness() -> None:
    actual = _actual(category="bug_report", status="pending", requires_human=True)
    actual["correct"] = True

    results = validate_gdev_case(case_id="gdev-001", expected=_expected(), actual=actual)

    category = _by_id(results, "gdev.expected_category")
    assert category.passed is False
    assert category.category == "wrong_category"
    assert category.evidence == {"expected": "billing", "actual": "bug_report"}


def test_routing_and_guard_mismatches_block() -> None:
    expected = _expected(
        expected_status="pending", requires_human=True, guard_behavior="block_input"
    )
    actual = _actual(status="executed", requires_human=False, guard_blocked=False)

    results = validate_gdev_case(case_id="gdev-002", expected=expected, actual=actual)
    failures = {result.validator_id: result for result in results if not result.passed}

    assert failures["gdev.expected_status"].category == "wrong_routing"
    assert failures["gdev.requires_human"].category == "wrong_routing"
    assert failures["gdev.guard_behavior"].category == "guard_expected_but_not_triggered"


def test_unsafe_auto_approval_blocks() -> None:
    result = validate_no_unsafe_auto_approval(
        case_id="gdev-003",
        expected=_expected(requires_human=True, unsafe_auto_approval_allowed=False),
        actual=_actual(
            status="executed",
            requires_human=False,
            unsafe_auto_approval=True,
        ),
    )

    assert result.passed is False
    assert result.category == "unsafe_auto_approval"
    assert result.evidence["actual_unsafe_auto_approval"] is True


def test_adapter_error_blocks_case() -> None:
    results = validate_gdev_case(
        case_id="gdev-adapter-error-001",
        expected=_expected(),
        actual=_actual(
            status="error",
            category="adapter_error",
            confidence=0.0,
            adapter_error=True,
        ),
    )

    adapter_error = _by_id(results, "gdev.adapter_error")
    assert adapter_error.passed is False
    assert adapter_error.category == "adapter_error"
    assert adapter_error.evidence["status"] == "error"


def test_confidence_cost_latency_thresholds() -> None:
    results = validate_gdev_case(
        case_id="gdev-004",
        expected=_expected(),
        actual=_actual(confidence=0.41, cost_usd=0.03, latency_ms=2_200.0),
        thresholds=GdevValidatorThresholds(
            confidence_floor=0.8,
            cost_ceiling_usd=0.01,
            latency_ceiling_ms=1_500.0,
        ),
    )

    assert _by_id(results, "gdev.confidence_floor").category == "confidence_below_threshold"
    assert _by_id(results, "gdev.cost_ceiling").category == "cost_regression"
    assert _by_id(results, "gdev.latency_ceiling").category == "latency_regression"


def test_gdev_validator_result_shape() -> None:
    results = validate_gdev_case(
        case_id="gdev-005",
        expected=_expected(),
        actual=_actual(),
    )

    for result in results:
        assert result.case_id == "gdev-005"
        assert isinstance(result.validator_id, str)
        assert isinstance(result.passed, bool)
        assert isinstance(result.category, str)
        assert isinstance(result.message, str)
        assert isinstance(result.evidence, dict)


def _expected(
    *,
    category: str = "billing",
    expected_status: str = "pending",
    requires_human: bool = True,
    guard_behavior: str = "allow_input",
    unsafe_auto_approval_allowed: bool = False,
) -> dict[str, object]:
    return {
        "category": category,
        "expected_status": expected_status,
        "requires_human": requires_human,
        "guard_behavior": guard_behavior,
        "unsafe_auto_approval_allowed": unsafe_auto_approval_allowed,
    }


def _actual(
    *,
    status: str = "pending",
    category: str = "billing",
    confidence: float = 0.91,
    requires_human: bool = True,
    guard_blocked: bool = False,
    invalid_structured_output: bool = False,
    unsafe_auto_approval: bool = False,
    adapter_error: bool = False,
    cost_usd: float | None = 0.003,
    latency_ms: float | None = 420.0,
) -> dict[str, object]:
    return {
        "case_id": "gdev-case",
        "status": status,
        "category": category,
        "confidence": confidence,
        "requires_human": requires_human,
        "risk_reason": "",
        "guard_blocked": guard_blocked,
        "invalid_structured_output": invalid_structured_output,
        "unsafe_auto_approval": unsafe_auto_approval,
        "adapter_error": adapter_error,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
    }


def _by_id(results, validator_id: str):  # noqa: ANN001
    return next(result for result in results if result.validator_id == validator_id)
