from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab.runs import RunRecord

ROOT = Path(__file__).resolve().parents[2]


def test_baseline_report_generated_from_run_artifact() -> None:
    run = _load_run()
    report = _read_report()

    assert run.status == "completed"
    assert run.run_id in report
    assert run.dataset_hash in report
    assert run.candidate_version in report
    assert f"`{run.cost_per_case_usd:.4f}`" in report
    assert f"`{run.latency_ms_p95:.0f}`" in report
    failing_case_ids = [
        result.case_id
        for result in run.case_results
        for validator in result.validator_results
        if validator.get("passed") is False
    ]
    assert failing_case_ids
    for case_id in failing_case_ids:
        assert case_id in report


def test_baseline_run_cases_match_source_dataset() -> None:
    run = _load_run()
    dataset_cases = _load_dataset_cases()

    for result in run.case_results:
        assert result.case_id in dataset_cases
        has_wrong_category_failure = any(
            validator.get("category") == "wrong_category" and validator.get("passed") is False
            for validator in result.validator_results
        )
        if has_wrong_category_failure:
            continue
        assert result.output["category"] == dataset_cases[result.case_id]["expected"]["category"]


def test_baseline_report_contains_required_sections() -> None:
    report = _read_report()

    for required_text in (
        "## Summary",
        "## Dataset Hash",
        "## Environment",
        "## Candidate Version",
        "## Metrics",
        "## Threshold Summary",
        "## Failure Taxonomy",
        "## Case-Level Failures",
        "## Known Limits",
        "## Reproduction Command",
        "classification_accuracy",
        "risk_routing_recall",
        "human_escalation_recall",
        "unsafe_auto_approval_rate",
        "invalid_structured_output_rate",
        "guard_block_rate",
        "cost_per_case_usd",
        "latency_p95_ms",
        "adapter_error_rate",
    ):
        assert required_text in report


def test_baseline_report_labels_scope_and_limits() -> None:
    report = _read_report()
    report_lower = report.lower()

    assert "synthetic/local deterministic" in report
    assert "not production quality" in report
    assert "not a production eval platform claim" in report
    assert "production-ready" not in report_lower
    assert "enterprise eval saas" not in report_lower


def test_evidence_index_links_baseline_report() -> None:
    evidence_index = (ROOT / "docs/EVIDENCE_INDEX.md").read_text(encoding="utf-8")

    assert "reports/gdev-agent/baseline_report.md" in evidence_index
    assert "reports/gdev-agent/baseline_run.json" in evidence_index


def _load_run() -> RunRecord:
    with (ROOT / "reports/gdev-agent/baseline_run.json").open(encoding="utf-8") as run_file:
        return RunRecord.from_mapping(json.load(run_file))


def _load_dataset_cases() -> dict[str, dict[str, object]]:
    cases: dict[str, dict[str, object]] = {}
    with (ROOT / "datasets/gdev_agent/triage_v1.jsonl").open(encoding="utf-8") as dataset_file:
        for line in dataset_file:
            case = json.loads(line)
            cases[case["id"]] = case
    return cases


def _read_report() -> str:
    return (ROOT / "reports/gdev-agent/baseline_report.md").read_text(encoding="utf-8")
