from __future__ import annotations

from eval_ground_truth_lab.adapters.gdev_normalizer import normalize_gdev_response


def test_normalizer_supports_core_paths() -> None:
    paths = [
        ("executed", False, False),
        ("pending", True, False),
        ("blocked", True, True),
        ("error", True, False),
    ]

    for status, requires_human, guard_blocked in paths:
        normalized = normalize_gdev_response(
            case_id=f"case-{status}",
            response_body={
                "status": status,
                "category": "billing",
                "confidence": 0.82,
                "requires_human": requires_human,
                "risk_reason": f"{status} path",
                "guard_blocked": guard_blocked,
            },
        )

        assert normalized.case_id == f"case-{status}"
        assert normalized.status == status
        assert normalized.category == "billing"
        assert normalized.confidence == 0.82
        assert normalized.requires_human is requires_human
        assert normalized.guard_blocked is guard_blocked
        assert normalized.invalid_structured_output is False
        assert normalized.adapter_error is (status == "error")


def test_missing_fields_fail_closed() -> None:
    normalized = normalize_gdev_response(
        case_id="gdev-billing-refund-001",
        response_body={
            "status": "executed",
            "category": "billing",
        },
    )

    assert normalized.status == "error"
    assert normalized.category == "invalid_structured_output"
    assert normalized.confidence == 0.0
    assert normalized.requires_human is True
    assert normalized.invalid_structured_output is True
    assert "missing required fields" in normalized.risk_reason


def test_http_error_response_normalizes_to_eval_failure() -> None:
    normalized = normalize_gdev_response(
        case_id="gdev-webhook-error-001",
        response_body={"error": "service unavailable"},
        http_status=503,
        latency_ms=711.4,
    )

    assert normalized.status == "error"
    assert normalized.category == "adapter_error"
    assert normalized.confidence == 0.0
    assert normalized.requires_human is True
    assert normalized.adapter_error is True
    assert normalized.invalid_structured_output is False
    assert normalized.latency_ms == 711.4


def test_latency_and_cost_are_preserved() -> None:
    normalized = normalize_gdev_response(
        case_id="gdev-billing-refund-002",
        response_body={
            "status": "pending",
            "category": "billing",
            "confidence": 0.91,
            "requires_human": True,
            "usage": {"estimated_cost_usd": 0.003},
            "latency_ms": 420,
        },
    )

    assert normalized.cost_usd == 0.003
    assert normalized.latency_ms == 420.0
    assert normalized.to_mapping()["cost_usd"] == 0.003
