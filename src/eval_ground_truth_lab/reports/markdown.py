from __future__ import annotations

import html
import string
import unicodedata
from collections import Counter
from collections.abc import Mapping
from typing import Any

from eval_ground_truth_lab.compare import ComparisonReport
from eval_ground_truth_lab.runs import CaseResult, RunRecord

_ASCII_PUNCTUATION = frozenset(string.punctuation)


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
        f"| Dataset hash | {_code(comparison.dataset_hash)} |",
        f"| Baseline run | {_code(comparison.baseline_run_id)} |",
        f"| Candidate run | {_code(comparison.candidate_run_id)} |",
        f"| Baseline candidate version | {_code(baseline.candidate_version)} |",
        f"| Candidate version | {_code(candidate.candidate_version)} |",
        f"| Validator version | {_code(candidate.validator_version)} |",
        f"| Threshold config | {_code(candidate.threshold_config_version)} |",
        "",
        "## Threshold Summary",
        "",
        "| Metric | Exact delta | Gate | Status |",
        "|--------|-------------|------|--------|",
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
    if comparison.validator_receipt_regressions:
        lines.extend(_validator_receipt_regression_lines(comparison))
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
        f"| {_code(metric)} | {_code(comparison.exact_deltas.get(metric, str(value)))} | "
        f"{_code(_gate_rule(metric, comparison.exact_thresholds.get(metric)))} | "
        f"{_code(comparison.threshold_status.get(metric, 'n/a'))} |"
        for metric, value in metrics.items()
    ]


def _gate_rule(metric: str, exact_threshold: str | None) -> str:
    if exact_threshold is None:
        return "n/a"
    if metric == "accuracy_delta":
        minimum = "0" if exact_threshold == "0" else f"-{exact_threshold}"
        return f"delta ≥ {minimum}"
    return f"delta ≤ {exact_threshold}"


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
        f"| {_code(category)} | {count} |"
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
        f"| {_code(case_id)} | {_code(category)} | {_code(validator_id)} | "
        f"{_escape_markdown_plain_text(message)} |"
        for case_id, category, validator_id, message in failures
    )
    return lines


def _raw_artifact_lines(raw_artifact_links: Mapping[str, str]) -> list[str]:
    if not raw_artifact_links:
        return ["No raw artifact links recorded."]
    return [
        f"- {_escape_markdown_plain_text(name)}: {_code(location)}"
        for name, location in raw_artifact_links.items()
    ]


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


def _validator_receipt_regression_lines(comparison: ComparisonReport) -> list[str]:
    regressions = comparison.validator_receipt_regressions
    return [
        "## Validator Receipt Regressions",
        "",
        "| Gate | Status | Count |",
        "|------|--------|-------|",
        f"| `validator_receipt_regression` | `fail` | {len(regressions)} |",
        "",
        "| Case ID | Validator | Candidate category |",
        "|---------|-----------|--------------------|",
        *(
            f"| {_code(regression.case_id)} | {_code(regression.validator_id)} | "
            f"{_code(regression.candidate_category)} |"
            for regression in regressions
        ),
        "",
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


def _code(value: Any) -> str:
    return f"`{_escape_markdown_code(value)}`"


def _escape_markdown_code(value: Any) -> str:
    escaped: list[str] = []
    for character in str(value):
        if character in {"\u2028", "\u2029"} or unicodedata.category(character).startswith("C"):
            escaped.append(_visible_control_escape(character, plain_text=False))
        elif character in {"`", "|"}:
            escaped.append(f"&#{ord(character)};")
        else:
            escaped.append(html.escape(character, quote=True))
    return "".join(escaped)


def _escape_markdown_plain_text(value: Any) -> str:
    escaped: list[str] = []
    for character in str(value):
        if character in {"\u2028", "\u2029"} or unicodedata.category(character).startswith("C"):
            escaped.append(_visible_control_escape(character, plain_text=True))
        elif character in _ASCII_PUNCTUATION:
            if character in {"&", "<", ">"}:
                escaped.append(html.escape(character, quote=True))
            else:
                # Entities are parsed as text tokens after Markdown delimiter
                # recognition, so punctuation cannot form links, images,
                # emphasis, headings, autolinks, or escape another delimiter.
                escaped.append(f"&#{ord(character)};")
        else:
            escaped.append(character)
    return "".join(escaped)


def _visible_control_escape(character: str, *, plain_text: bool) -> str:
    named = {
        "\b": "b",
        "\t": "t",
        "\n": "n",
        "\v": "v",
        "\f": "f",
        "\r": "r",
    }
    codepoint = ord(character)
    suffix = named.get(character)
    if suffix is None:
        if codepoint <= 0xFF:
            suffix = f"x{codepoint:02x}"
        elif codepoint <= 0xFFFF:
            suffix = f"u{codepoint:04x}"
        else:
            suffix = f"U{codepoint:08x}"
    backslash = "&#92;" if plain_text else "\\"
    return f"{backslash}{suffix}"
