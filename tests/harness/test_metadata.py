from __future__ import annotations

import pytest

from eval_ground_truth_lab.compare import ComparisonReport, ValidatorReceiptRegression
from eval_ground_truth_lab.harness.metadata import (
    HarnessConfig,
    HarnessMetadataMismatchError,
    HarnessRunMetadata,
    TraceCompletenessValidator,
    build_harness_comparison_report,
)


def test_harness_config_round_trips_versioned_boundary() -> None:
    config = HarnessConfig(
        harness_id="gdev-agent",
        harness_version="harness-v1",
        model_class="demo",
        prompt_version="prompt-v1",
        tool_registry_version="tools-v1",
        memory_policy_version="none",
        permission_policy_version="permissions-v1",
        recovery_policy_version="recovery-v1",
        trace_schema_version="trace-v1",
        environment_id="local-ci",
    )

    assert HarnessConfig.from_mapping(config.to_mapping()) == config


def test_trace_completeness_validator_reports_missing_events() -> None:
    validator = TraceCompletenessValidator(
        required_event_types=("run_start", "model_call", "permission_decision", "run_end")
    )

    report = validator.validate(
        (
            {"event_type": "run_start"},
            {"event_type": "model_call"},
            {"event_type": "run_end"},
        )
    )

    assert report.is_complete is False
    assert report.missing_event_types == ("permission_decision",)
    assert report.event_count == 3


def test_harness_comparison_includes_trace_and_budget_context() -> None:
    validator = TraceCompletenessValidator(("run_start", "model_call", "run_end"))
    trace = validator.validate(
        (
            {"event_type": "run_start"},
            {"event_type": "model_call"},
            {"event_type": "run_end"},
        )
    )

    report = build_harness_comparison_report(
        metric_report=_comparison_report(),
        baseline_metadata=_metadata(run_id="baseline", budget_usd=1.0, harness_version="h1"),
        candidate_metadata=_metadata(run_id="candidate", budget_usd=1.5, harness_version="h2"),
        baseline_trace=trace,
        candidate_trace=trace,
    )

    assert report.cost_budget_delta_usd == pytest.approx(0.5)
    assert report.has_blocking_failure is False
    assert report.to_mapping()["candidate_harness"]["harness_version"] == "h2"


def test_harness_comparison_rejects_scorer_mismatch() -> None:
    trace = TraceCompletenessValidator(("run_start",)).validate(({"event_type": "run_start"},))
    baseline = _metadata(run_id="baseline", scorer_version="scorer-v1")
    candidate = _metadata(run_id="candidate", scorer_version="scorer-v2")

    with pytest.raises(HarnessMetadataMismatchError):
        build_harness_comparison_report(
            metric_report=_comparison_report(),
            baseline_metadata=baseline,
            candidate_metadata=candidate,
            baseline_trace=trace,
            candidate_trace=trace,
        )


def test_harness_comparison_serializes_generic_validator_regression_reason() -> None:
    trace = TraceCompletenessValidator(("run_start",)).validate(({"event_type": "run_start"},))
    metric_report = _comparison_report(
        validator_receipt_regressions=(
            ValidatorReceiptRegression(
                case_id="case-2",
                validator_id="validator-z",
                candidate_category="adapter_error",
            ),
            ValidatorReceiptRegression(
                case_id="case-1",
                validator_id="validator-a",
                candidate_category="evidence_mismatch",
            ),
        )
    )
    report = build_harness_comparison_report(
        metric_report=metric_report,
        baseline_metadata=_metadata(run_id="baseline"),
        candidate_metadata=_metadata(run_id="candidate"),
        baseline_trace=trace,
        candidate_trace=trace,
    )

    serialized = report.to_mapping()

    assert serialized["has_blocking_failure"] is True
    assert serialized["validator_receipt_regression_count"] == 2
    assert serialized["validator_receipt_regressions"] == [
        {
            "case_id": "case-2",
            "validator_id": "validator-z",
            "candidate_category": "adapter_error",
        },
        {
            "case_id": "case-1",
            "validator_id": "validator-a",
            "candidate_category": "evidence_mismatch",
        },
    ]


def _metadata(
    *,
    run_id: str,
    budget_usd: float = 1.0,
    harness_version: str = "harness-v1",
    scorer_version: str = "scorer-v1",
) -> HarnessRunMetadata:
    return HarnessRunMetadata(
        run_id=run_id,
        dataset_hash="dataset-123",
        scorer_version=scorer_version,
        budget_usd=budget_usd,
        harness=HarnessConfig(
            harness_id="gdev-agent",
            harness_version=harness_version,
            model_class="demo",
            prompt_version="prompt-v1",
        ),
    )


def _comparison_report(
    *,
    validator_receipt_regressions: tuple[ValidatorReceiptRegression, ...] = (),
) -> ComparisonReport:
    return ComparisonReport(
        baseline_run_id="baseline",
        candidate_run_id="candidate",
        dataset_hash="dataset-123",
        accuracy_delta=0.0,
        invalid_output_rate_delta=0.0,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=0.0,
        cost_per_case_delta=0.0,
        threshold_status={
            "accuracy_delta": "pass",
            "invalid_output_rate": "pass",
            "unsafe_auto_approval_rate": "pass",
            "latency_ms_p95_delta": "pass",
            "cost_per_case_delta": "pass",
        },
        validator_receipt_regressions=validator_receipt_regressions,
    )
