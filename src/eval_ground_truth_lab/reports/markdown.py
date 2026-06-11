from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from eval_ground_truth_lab.compare import ComparisonReport
from eval_ground_truth_lab.runs import CaseResult, RunRecord


def render_markdown_report(
    *,
    baseline: RunRecord,
    candidate: RunRecord,
    comparison: ComparisonReport,
    raw_artifact_links: Mapping[str, str],
) -> str:
    """Render a markdown report from canonical run and comparison records."""

    lines = [
        "# Eval Report",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Dataset hash | `{comparison.dataset_hash}` |",
        f"| Baseline run | `{comparison.baseline_run_id}` |",
        f"| Candidate run | `{comparison.candidate_run_id}` |",
        f"| Baseline candidate version | `{baseline.candidate_version}` |",
        f"| Candidate version | `{candidate.candidate_version}` |",
        f"| Validator version | `{candidate.validator_version}` |",
        f"| Threshold config | `{candidate.threshold_config_version}` |",
        "",
        "## Threshold Summary",
        "",
        "| Metric | Delta | Status |",
        "|--------|-------|--------|",
        *_threshold_rows(comparison),
        "",
        "## Top Failure Categories",
        "",
        *_top_failure_category_lines(candidate.case_results, comparison),
        "",
        "## Case-Level Failures",
        "",
        *_case_failure_lines(candidate.case_results),
        "",
        "## Raw Artifact Links",
        "",
        *_raw_artifact_lines(raw_artifact_links),
        "",
    ]
    return "\n".join(lines)


def _threshold_rows(comparison: ComparisonReport) -> list[str]:
    metrics = {
        "accuracy_delta": comparison.accuracy_delta,
        "invalid_output_rate": comparison.invalid_output_rate_delta,
        "unsafe_auto_approval_rate": comparison.unsafe_auto_approval_rate_delta,
        "latency_ms_p95_delta": comparison.latency_ms_p95_delta,
        "cost_per_case_delta": comparison.cost_per_case_delta,
    }
    return [
        f"| `{metric}` | `{value:.6g}` | `{comparison.threshold_status.get(metric, 'n/a')}` |"
        for metric, value in metrics.items()
    ]


def _top_failure_category_lines(
    case_results: tuple[CaseResult, ...],
    comparison: ComparisonReport,
) -> list[str]:
    counts = Counter(
        [
            *_failure_categories(case_results),
            *_comparison_failure_categories(comparison),
        ]
    )
    if not counts:
        return ["No failures."]

    lines = ["| Category | Count |", "|----------|-------|"]
    lines.extend(
        f"| `{category}` | {count} |"
        for category, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )
    return lines


def _case_failure_lines(case_results: tuple[CaseResult, ...]) -> list[str]:
    failures = list(_case_failures(case_results))
    if not failures:
        return ["No case-level failures."]

    lines = [
        "| Case ID | Category | Validator | Message |",
        "|---------|----------|-----------|---------|",
    ]
    lines.extend(
        f"| `{case_id}` | `{category}` | `{validator_id}` | {message} |"
        for case_id, category, validator_id, message in failures
    )
    return lines


def _raw_artifact_lines(raw_artifact_links: Mapping[str, str]) -> list[str]:
    if not raw_artifact_links:
        return ["No raw artifact links recorded."]
    return [f"- {name}: `{location}`" for name, location in raw_artifact_links.items()]


def _failure_categories(case_results: tuple[CaseResult, ...]) -> list[str]:
    return [
        str(result.get("category"))
        for case_result in case_results
        for result in case_result.validator_results
        if _is_failure(result) and result.get("category")
    ]


def _comparison_failure_categories(comparison: ComparisonReport) -> list[str]:
    category_by_metric = {
        "accuracy_delta": "accuracy_regression",
        "invalid_output_rate": "invalid_structured_output",
        "unsafe_auto_approval_rate": "unsafe_auto_approval",
        "latency_ms_p95_delta": "latency_regression",
        "cost_per_case_delta": "cost_regression",
    }
    return [
        category
        for metric, category in category_by_metric.items()
        if comparison.threshold_status.get(metric) == "fail"
    ]


def _case_failures(case_results: tuple[CaseResult, ...]) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for case_result in case_results:
        for result in case_result.validator_results:
            if not _is_failure(result):
                continue
            rows.append(
                (
                    case_result.case_id,
                    str(result.get("category", "unknown")),
                    str(result.get("validator_id", "unknown")),
                    str(result.get("message", "")),
                )
            )
    return rows


def _is_failure(result: Mapping[str, Any]) -> bool:
    return result.get("passed") is False
