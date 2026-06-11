from __future__ import annotations

from eval_ground_truth_lab.compare import ComparisonReport
from eval_ground_truth_lab.reports import render_markdown_report
from eval_ground_truth_lab.runs import CaseResult, RunRecord


def test_markdown_report_contains_required_sections() -> None:
    baseline = _run_record("baseline-001", case_results=())
    candidate = _run_record(
        "candidate-001",
        case_results=(
            CaseResult(
                case_id="case-001",
                output={"correct": False},
                validator_results=(
                    {
                        "validator_id": "structured_output.required_fields",
                        "passed": False,
                        "category": "invalid_structured_output",
                        "message": "missing answer",
                    },
                ),
                cost_usd=0.02,
                latency_ms=125.0,
            ),
        ),
    )
    comparison = ComparisonReport(
        baseline_run_id=baseline.run_id,
        candidate_run_id=candidate.run_id,
        dataset_hash="dataset-sha",
        accuracy_delta=-0.2,
        invalid_output_rate_delta=0.1,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=25.0,
        cost_per_case_delta=0.01,
        threshold_status={
            "accuracy_delta": "fail",
            "invalid_output_rate": "fail",
            "unsafe_auto_approval_rate": "pass",
            "latency_ms_p95_delta": "fail",
            "cost_per_case_delta": "fail",
        },
    )

    report = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "baseline run": "runs/baseline-001.json",
            "candidate run": "runs/candidate-001.json",
            "threshold config": "thresholds/v1.json",
        },
    )

    assert "## Run Metadata" in report
    assert "## Threshold Summary" in report
    assert "## Top Failure Categories" in report
    assert "## Case-Level Failures" in report
    assert "## Raw Artifact Links" in report
    assert "`dataset-sha`" in report
    assert "`invalid_structured_output`" in report
    assert "`accuracy_regression`" in report
    assert "`cost_regression`" in report
    assert "`case-001`" in report
    assert "runs/candidate-001.json" in report


def _run_record(run_id: str, *, case_results: tuple[CaseResult, ...]) -> RunRecord:
    return RunRecord(
        run_id=run_id,
        run_type="candidate",
        dataset_hash="dataset-sha",
        candidate_version=f"{run_id}-version",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
        status="completed",
        started_at="2026-06-11T00:00:00+00:00",
        completed_at="2026-06-11T00:01:00+00:00",
        cost_total_usd=sum(case.cost_usd for case in case_results),
        cost_per_case_usd=0.02 if case_results else 0.0,
        latency_ms_p50=100.0 if case_results else 0.0,
        latency_ms_p95=125.0 if case_results else 0.0,
        case_results=case_results,
    )
