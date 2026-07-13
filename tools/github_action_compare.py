"""Fail-closed runner for the repository's composite comparison action."""

from __future__ import annotations

import html
import json
import math
import os
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_ground_truth_lab.compare import ThresholdConfig, compare_runs
from eval_ground_truth_lab.reports import render_markdown_report
from eval_ground_truth_lab.runs import RunRecord

PASS = 0
BLOCKED = 1
ACTION_ERROR = 2
_MAX_SUMMARY_REPORT_CHARS = 120_000
_STANDARD_THRESHOLD_FIELDS = frozenset(
    {
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "max_latency_p95_delta_ms",
        "max_cost_per_case_delta_usd",
    }
)
_GDEV_THRESHOLD_FIELDS = frozenset(
    {
        "classification_accuracy_min",
        "max_invalid_structured_output_rate",
        "max_unsafe_auto_approval_rate",
        "max_latency_p95_ms",
        "max_cost_per_case_usd",
    }
)
_GDEV_OPTIONAL_THRESHOLD_FIELDS = frozenset(
    {
        "confidence_floor",
        "guard_block_rate_max",
        "human_escalation_recall_min",
        "risk_routing_recall_min",
    }
)
_RATE_THRESHOLD_FIELDS = frozenset(
    {
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "classification_accuracy_min",
        "max_invalid_structured_output_rate",
        "max_unsafe_auto_approval_rate",
        *_GDEV_OPTIONAL_THRESHOLD_FIELDS,
    }
)


class ActionConfigurationError(ValueError):
    """Raised when runner-controlled action configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class ActionPaths:
    workspace: Path
    baseline: Path
    candidate: Path
    thresholds: Path
    report: Path

    @property
    def report_relative(self) -> str:
        return self.report.relative_to(self.workspace).as_posix()


def main(environment: Mapping[str, str] | None = None) -> int:
    """Run the comparison, publish a fresh report, and preserve the gate status."""

    env = os.environ if environment is None else environment
    try:
        paths = _load_paths(env)
    except ActionConfigurationError as exc:
        _emit_error(env, str(exc))
        return ACTION_ERROR

    temporary_report: Path | None = None
    try:
        paths.report.unlink(missing_ok=True)
        paths.report.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=paths.report.parent,
            prefix=f".{paths.report.name}.",
            suffix=".tmp",
        )
        os.close(descriptor)
        temporary_report = Path(temporary_name)

        gate_status = _run_compare(paths, temporary_report)

        report_text = temporary_report.read_text(encoding="utf-8")
        if not report_text.strip():
            raise RuntimeError("compare did not produce a non-empty report")
        _publish_report(temporary_report, paths.report)
        temporary_report = None

        conclusion = "pass" if gate_status == PASS else "fail"
        _emit_outputs(env, report=paths.report_relative, conclusion=conclusion)
        _emit_decision_summary(
            env,
            report=paths.report_relative,
            conclusion=conclusion,
            report_text=report_text,
        )
        return gate_status
    except Exception as exc:  # fail closed before treating any report as fresh
        cleanup_error: OSError | None = None
        try:
            paths.report.unlink(missing_ok=True)
        except OSError as report_cleanup_error:
            cleanup_error = report_cleanup_error
        if cleanup_error is not None:
            exc = RuntimeError(
                f"{type(exc).__name__}: {exc}; could not remove report target: {cleanup_error}"
            )
        _emit_error(env, f"{type(exc).__name__}: {exc}")
        return ACTION_ERROR
    finally:
        if temporary_report is not None:
            temporary_report.unlink(missing_ok=True)


def _load_paths(env: Mapping[str, str]) -> ActionPaths:
    workspace_raw = _required_value(env, "GITHUB_WORKSPACE")
    try:
        workspace = Path(workspace_raw).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ActionConfigurationError("GITHUB_WORKSPACE does not exist") from exc
    if not workspace.is_dir():
        raise ActionConfigurationError("GITHUB_WORKSPACE must identify a directory")

    baseline = _input_path(env, "EVAL_LAB_BASELINE", workspace, must_exist=True)
    candidate = _input_path(env, "EVAL_LAB_CANDIDATE", workspace, must_exist=True)
    thresholds = _input_path(env, "EVAL_LAB_THRESHOLD_CONFIG", workspace, must_exist=True)
    report = _input_path(
        env,
        "EVAL_LAB_REPORT",
        workspace,
        must_exist=False,
        reject_leaf_symlink=True,
    )

    for label, path in (
        ("baseline", baseline),
        ("candidate", candidate),
        ("threshold config", thresholds),
    ):
        if not path.is_file():
            raise ActionConfigurationError(f"{label} must identify a regular file")

    if report == workspace:
        raise ActionConfigurationError("report must identify a file below GITHUB_WORKSPACE")
    if report.exists() and not report.is_file():
        raise ActionConfigurationError("report target must be a regular file or not exist")
    if report in {baseline, candidate, thresholds}:
        raise ActionConfigurationError("report must not overwrite an input file")

    return ActionPaths(
        workspace=workspace,
        baseline=baseline,
        candidate=candidate,
        thresholds=thresholds,
        report=report,
    )


def _required_value(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "")
    if not value:
        raise ActionConfigurationError(f"{name} is required")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ActionConfigurationError(f"{name} must be a single line without NUL bytes")
    return value


def _input_path(
    env: Mapping[str, str],
    name: str,
    workspace: Path,
    *,
    must_exist: bool,
    reject_leaf_symlink: bool = False,
) -> Path:
    raw = _required_value(env, name)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    if reject_leaf_symlink and candidate.is_symlink():
        raise ActionConfigurationError(f"{name} must not be a symbolic link")
    try:
        resolved = candidate.resolve(strict=must_exist)
    except FileNotFoundError as exc:
        raise ActionConfigurationError(f"{name} does not exist") from exc
    if not resolved.is_relative_to(workspace):
        raise ActionConfigurationError(f"{name} must stay inside GITHUB_WORKSPACE")
    return resolved


def _publish_report(temporary_report: Path, report: Path) -> None:
    with temporary_report.open("rb") as report_file:
        os.fsync(report_file.fileno())
    os.replace(temporary_report, report)
    try:
        directory_descriptor = os.open(report.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _run_compare(paths: ActionPaths, temporary_report: Path) -> int:
    baseline = _read_run(paths.baseline)
    candidate = _read_run(paths.candidate)
    _validate_comparison_runs(baseline, candidate)
    thresholds = _read_thresholds(paths.thresholds)
    comparison = compare_runs(
        baseline=baseline,
        candidate=candidate,
        thresholds=thresholds,
    )
    report_text = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "baseline run": paths.baseline.relative_to(paths.workspace).as_posix(),
            "candidate run": paths.candidate.relative_to(paths.workspace).as_posix(),
            "threshold config": paths.thresholds.relative_to(paths.workspace).as_posix(),
        },
    )
    temporary_report.write_text(report_text, encoding="utf-8")
    return BLOCKED if comparison.has_blocking_failure else PASS


def _read_run(path: Path) -> RunRecord:
    raw = _read_json_object(path, label="run artifact")
    _require_fields(
        raw,
        {
            "run_id",
            "run_type",
            "dataset_hash",
            "candidate_version",
            "validator_version",
            "threshold_config_version",
            "status",
            "started_at",
            "completed_at",
            "cost_total_usd",
            "cost_per_case_usd",
            "latency_ms_p50",
            "latency_ms_p95",
            "max_candidate_retries",
            "case_results",
        },
        label="run artifact",
    )
    for field in (
        "run_id",
        "run_type",
        "dataset_hash",
        "candidate_version",
        "validator_version",
        "threshold_config_version",
        "started_at",
        "completed_at",
    ):
        _require_nonempty_string(raw[field], field=field)
    if raw["status"] != "completed":
        raise ValueError("run artifact status must be exactly 'completed'")
    case_results = raw["case_results"]
    if not isinstance(case_results, list) or not case_results:
        raise ValueError("completed run artifact must contain at least one case result")

    for field in (
        "cost_total_usd",
        "cost_per_case_usd",
        "latency_ms_p50",
        "latency_ms_p95",
    ):
        _finite_nonnegative(raw[field], field=field)
    if float(raw["latency_ms_p95"]) < float(raw["latency_ms_p50"]):
        raise ValueError("latency_ms_p95 must be greater than or equal to latency_ms_p50")
    retries = raw["max_candidate_retries"]
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ValueError("max_candidate_retries must be a non-negative integer")

    for index, case_result in enumerate(case_results):
        if not isinstance(case_result, dict):
            raise ValueError(f"case_results[{index}] must be a JSON object")
        _require_fields(
            case_result,
            {"case_id", "output", "validator_results", "cost_usd", "latency_ms"},
            label=f"case_results[{index}]",
        )
        if not isinstance(case_result["case_id"], str) or not case_result["case_id"].strip():
            raise ValueError(f"case_results[{index}].case_id must be a non-empty string")
        if not isinstance(case_result["validator_results"], list):
            raise ValueError(f"case_results[{index}].validator_results must be a JSON array")
        _finite_nonnegative(case_result["cost_usd"], field=f"case_results[{index}].cost_usd")
        _finite_nonnegative(
            case_result["latency_ms"],
            field=f"case_results[{index}].latency_ms",
        )
    run = RunRecord.from_mapping(raw)
    _validate_aggregate_metrics(run)
    return run


def _read_thresholds(path: Path) -> ThresholdConfig:
    raw = _read_json_object(path, label="threshold config")
    keys = set(raw)
    if keys & _STANDARD_THRESHOLD_FIELDS:
        _require_fields(raw, _STANDARD_THRESHOLD_FIELDS, label="threshold config")
        _reject_unknown_fields(
            raw,
            _STANDARD_THRESHOLD_FIELDS | {"version"},
            label="threshold config",
        )
        return ThresholdConfig(
            max_accuracy_drop=_threshold_number(raw, "max_accuracy_drop"),
            max_invalid_output_rate_increase=_threshold_number(
                raw, "max_invalid_output_rate_increase"
            ),
            max_unsafe_auto_approval_rate_increase=_threshold_number(
                raw, "max_unsafe_auto_approval_rate_increase"
            ),
            max_latency_p95_delta_ms=_threshold_number(raw, "max_latency_p95_delta_ms"),
            max_cost_per_case_delta_usd=_threshold_number(raw, "max_cost_per_case_delta_usd"),
        )
    if keys & _GDEV_THRESHOLD_FIELDS:
        _require_fields(raw, _GDEV_THRESHOLD_FIELDS, label="threshold config")
        _reject_unknown_fields(
            raw,
            _GDEV_THRESHOLD_FIELDS | _GDEV_OPTIONAL_THRESHOLD_FIELDS | {"version"},
            label="threshold config",
        )
        for optional_field in _GDEV_OPTIONAL_THRESHOLD_FIELDS & keys:
            _threshold_number(raw, optional_field)
        accuracy_min = _threshold_number(raw, "classification_accuracy_min")
        return ThresholdConfig(
            max_accuracy_drop=1.0 - accuracy_min,
            max_invalid_output_rate_increase=_threshold_number(
                raw, "max_invalid_structured_output_rate"
            ),
            max_unsafe_auto_approval_rate_increase=_threshold_number(
                raw, "max_unsafe_auto_approval_rate"
            ),
            max_latency_p95_delta_ms=_threshold_number(raw, "max_latency_p95_ms"),
            max_cost_per_case_delta_usd=_threshold_number(raw, "max_cost_per_case_usd"),
        )
    raise ValueError("threshold config does not match a supported comparison schema")


def _validate_comparison_runs(baseline: RunRecord, candidate: RunRecord) -> None:
    baseline_ids = [case.case_id for case in baseline.case_results]
    candidate_ids = [case.case_id for case in candidate.case_results]
    if len(set(baseline_ids)) != len(baseline_ids):
        raise ValueError("baseline run contains duplicate case IDs")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate run contains duplicate case IDs")
    if set(baseline_ids) != set(candidate_ids):
        raise ValueError("baseline and candidate run artifacts must contain the same case IDs")
    if baseline.validator_version != candidate.validator_version:
        raise ValueError("baseline and candidate must use the same validator version")
    if baseline.run_type != candidate.run_type:
        raise ValueError("baseline and candidate must use the same run type")


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    def reject_nonstandard_constant(value: str) -> None:
        raise ValueError(f"{label} contains non-standard numeric constant {value}")

    with path.open(encoding="utf-8") as input_file:
        raw = json.load(
            input_file,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonstandard_constant,
        )
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be a JSON object")
    return raw


def _require_fields(
    raw: Mapping[str, Any],
    required: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"{label} is missing required fields: {', '.join(missing)}")


def _reject_unknown_fields(
    raw: Mapping[str, Any],
    allowed: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {', '.join(unknown)}")
    version = raw.get("version")
    if "version" in raw and (not isinstance(version, str) or not version.strip()):
        raise ValueError(f"{label} version must be a non-empty string")


def _threshold_number(raw: Mapping[str, Any], field: str) -> float:
    value = _finite_nonnegative(raw[field], field=field)
    if field in _RATE_THRESHOLD_FIELDS and value > 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return value


def _finite_nonnegative(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a JSON number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field} must be finite")
    if numeric < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return numeric


def _require_nonempty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _validate_aggregate_metrics(run: RunRecord) -> None:
    costs = [result.cost_usd for result in run.case_results]
    latencies = sorted(result.latency_ms for result in run.case_results)
    expected_total = sum(costs)
    expected_per_case = expected_total / len(costs)
    expected_p50 = _percentile(latencies, 0.50)
    expected_p95 = _percentile(latencies, 0.95)
    for field, actual, expected, tolerance in (
        ("cost_total_usd", run.cost_total_usd, expected_total, 1e-12),
        ("cost_per_case_usd", run.cost_per_case_usd, expected_per_case, 1e-12),
        ("latency_ms_p50", run.latency_ms_p50, expected_p50, 1e-9),
        ("latency_ms_p95", run.latency_ms_p95, expected_p95, 1e-9),
    ):
        if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=tolerance):
            raise ValueError(f"{field} does not match the complete case-result aggregate")


def _percentile(ordered_values: list[float], percentile: float) -> float:
    index = max(0, math.ceil(percentile * len(ordered_values)) - 1)
    return ordered_values[index]


def _emit_outputs(env: Mapping[str, str], *, report: str, conclusion: str) -> None:
    if any(character in report for character in ("\r", "\n")):
        raise RuntimeError("normalized report output must be a single line")
    _append_runner_file(
        env,
        "GITHUB_OUTPUT",
        f"report={report}\nconclusion={conclusion}\n",
    )


def _emit_decision_summary(
    env: Mapping[str, str],
    *,
    report: str,
    conclusion: str,
    report_text: str,
) -> None:
    excerpt = report_text[:_MAX_SUMMARY_REPORT_CHARS]
    truncation_note = ""
    if len(report_text) > len(excerpt):
        truncation_note = (
            "\n\n_Report preview truncated; the full workspace artifact is authoritative._\n"
        )
    safe_report_path = html.escape(report, quote=True)
    safe_excerpt = html.escape(excerpt, quote=True)
    summary = (
        "## Eval Ground Truth Lab release gate\n\n"
        f"Conclusion: **{conclusion.upper()}**  \n"
        f"Report: <code>{safe_report_path}</code>\n\n"
        "<details><summary>Fresh report preview</summary>\n\n"
        f"<pre>{safe_excerpt}</pre>\n\n"
        f"</details>{truncation_note}"
    )
    if not summary.endswith("\n"):
        summary += "\n"
    _append_runner_file(env, "GITHUB_STEP_SUMMARY", summary)


def _emit_error(env: Mapping[str, str], message: str) -> None:
    sanitized = message.replace("\x00", "?").replace("\r", " ").replace("\n", " ")
    safe_message = html.escape(sanitized, quote=True)
    try:
        _emit_outputs(env, report="", conclusion="error")
        _append_runner_file(
            env,
            "GITHUB_STEP_SUMMARY",
            "## Eval Ground Truth Lab release gate\n\n"
            f"Conclusion: **ERROR**  \n<code>{safe_message}</code>\n",
        )
    except (ActionConfigurationError, OSError):
        pass
    print(f"Eval release gate error: {sanitized}", file=sys.stderr)


def _append_runner_file(env: Mapping[str, str], name: str, content: str) -> None:
    path_raw = _required_value(env, name)
    path = Path(path_raw)
    with path.open("a", encoding="utf-8", newline="") as runner_file:
        runner_file.write(content)
        runner_file.flush()
        os.fsync(runner_file.fileno())


if __name__ == "__main__":
    raise SystemExit(main())
