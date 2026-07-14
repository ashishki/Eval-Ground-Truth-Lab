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


def test_markdown_report_escapes_every_caller_controlled_context() -> None:
    baseline = _run_record("baseline", case_results=())
    candidate = _run_record(
        "candidate",
        case_results=(
            CaseResult(
                case_id="case|forged`\n\u2028\u2029## FORGED CASE",
                output={"correct": False},
                validator_results=(
                    {
                        "validator_id": "validator|forged`",
                        "passed": False,
                        "category": "wrong|category`",
                        "message": "<b>PASS</b>|cell\n\u2028\u2029## FORGED RESULT",
                    },
                ),
            ),
        ),
    )
    comparison = ComparisonReport(
        baseline_run_id="baseline",
        candidate_run_id="candidate",
        dataset_hash="hash|forged`<b>PASS</b>",
        accuracy_delta=-1.0,
        invalid_output_rate_delta=0.0,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=0.0,
        cost_per_case_delta=0.0,
        threshold_status={"accuracy_delta": "fail"},
    )

    report = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "baseline|name": "runs/baseline`\n## FORGED ARTIFACT.json",
        },
    )

    assert "\n## FORGED CASE" not in report
    assert "\n## FORGED RESULT" not in report
    assert "\n## FORGED ARTIFACT" not in report
    assert "\u2028" not in report
    assert "\u2029" not in report
    assert "<b>PASS</b>" not in report
    assert "hash&#124;forged&#96;&lt;b&gt;PASS&lt;/b&gt;" in report
    assert r"case&#124;forged&#96;\n\u2028\u2029## FORGED CASE" in report
    assert (
        "&lt;b&gt;PASS&lt;&#47;b&gt;&#124;cell&#92;n&#92;u2028&#92;u2029&#35;&#35; FORGED RESULT"
    ) in report
    assert "baseline&#124;name" in report


def test_markdown_plain_text_cannot_create_links_images_or_escape_sequences() -> None:
    baseline = _run_record("baseline", case_results=())
    candidate = _run_record(
        "candidate",
        case_results=(
            CaseResult(
                case_id="case-1",
                output={"correct": False},
                validator_results=(
                    {
                        "validator_id": "validator-1",
                        "passed": False,
                        "category": "adapter_error",
                        "message": (
                            r"[forged](https://evil.example) "
                            r"\[escaped](https://evil.example/second) "
                            "https://bare.evil/path operator@evil.example "
                            "left\u202eright\u2028middle\u2029end\nnext"
                        ),
                    },
                ),
            ),
        ),
    )
    comparison = ComparisonReport(
        baseline_run_id="baseline",
        candidate_run_id="candidate",
        dataset_hash="dataset-sha",
        accuracy_delta=0.0,
        invalid_output_rate_delta=0.0,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=0.0,
        cost_per_case_delta=0.0,
        threshold_status={"accuracy_delta": "pass"},
    )

    report = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "![beacon](https://evil.example/pixel)": "runs/candidate.json",
        },
    )

    assert "[forged](https://evil.example)" not in report
    assert r"\[escaped](https://evil.example/second)" not in report
    assert "![beacon](https://evil.example/pixel)" not in report
    assert "https://evil.example" not in report
    assert "https://bare.evil/path" not in report
    assert "operator@evil.example" not in report
    assert "\u202e" not in report
    assert "\u2028" not in report
    assert "\u2029" not in report
    assert "left\u202eright" not in report
    assert "right\nnext" not in report
    assert "](" not in report
    assert "![" not in report
    assert (
        "&#91;forged&#93;&#40;https&#58;&#47;&#47;evil&#46;example&#41; "
        "&#92;&#91;escaped&#93;&#40;https&#58;&#47;&#47;evil&#46;example&#47;second&#41; "
        "https&#58;&#47;&#47;bare&#46;evil&#47;path operator&#64;evil&#46;example "
        "left&#92;u202eright&#92;u2028middle&#92;u2029end&#92;nnext"
    ) in report
    assert (
        "&#33;&#91;beacon&#93;&#40;https&#58;&#47;&#47;evil&#46;example&#47;pixel&#41;"
    ) in report


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
