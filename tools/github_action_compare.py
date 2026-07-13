"""Fail-closed runner for the repository's composite comparison action."""

from __future__ import annotations

import html
import json
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
    with path.open(encoding="utf-8") as run_file:
        raw = json.load(run_file)
    if not isinstance(raw, dict):
        raise ValueError("run artifact must be a JSON object")
    return RunRecord.from_mapping(raw)


def _read_thresholds(path: Path) -> ThresholdConfig:
    with path.open(encoding="utf-8") as threshold_file:
        raw: Any = json.load(threshold_file)
    if not isinstance(raw, Mapping):
        raise ValueError("threshold config must be a JSON object")
    if "max_accuracy_drop" not in raw:
        accuracy_min = float(raw.get("classification_accuracy_min", 1.0))
        return ThresholdConfig(
            max_accuracy_drop=max(0.0, 1.0 - accuracy_min),
            max_invalid_output_rate_increase=float(
                raw.get("max_invalid_structured_output_rate", 0.0)
            ),
            max_unsafe_auto_approval_rate_increase=float(
                raw.get("max_unsafe_auto_approval_rate", 0.0)
            ),
            max_latency_p95_delta_ms=float(raw.get("max_latency_p95_ms", 0.0)),
            max_cost_per_case_delta_usd=float(raw.get("max_cost_per_case_usd", 0.0)),
        )
    return ThresholdConfig(
        max_accuracy_drop=float(raw["max_accuracy_drop"]),
        max_invalid_output_rate_increase=float(raw["max_invalid_output_rate_increase"]),
        max_unsafe_auto_approval_rate_increase=float(raw["max_unsafe_auto_approval_rate_increase"]),
        max_latency_p95_delta_ms=float(raw["max_latency_p95_delta_ms"]),
        max_cost_per_case_delta_usd=float(raw["max_cost_per_case_delta_usd"]),
    )


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
