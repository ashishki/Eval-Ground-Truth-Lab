from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab.cli import run_compare_command
from tools import github_action_compare


@pytest.fixture
def action_environment(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _write_run(workspace / "baseline.json", run_id="baseline", correct=True)
    _write_run(workspace / "candidate.json", run_id="candidate", correct=True)
    _write_thresholds(workspace / "thresholds.json")
    environment = {
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "github-output.txt"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "step-summary.md"),
        "EVAL_LAB_BASELINE": "baseline.json",
        "EVAL_LAB_CANDIDATE": "candidate.json",
        "EVAL_LAB_THRESHOLD_CONFIG": "thresholds.json",
        "EVAL_LAB_REPORT": "reports/release-gate.md",
    }
    return workspace, environment


def test_pass_publishes_fresh_report_outputs_and_summary(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    report = workspace / environment["EVAL_LAB_REPORT"]
    report.parent.mkdir()
    report.write_text("STALE REPORT MUST NOT SURVIVE\n", encoding="utf-8")

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.PASS
    outputs = _read_outputs(Path(environment["GITHUB_OUTPUT"]))
    assert outputs == {"report": "reports/release-gate.md", "conclusion": "pass"}
    report_text = report.read_text(encoding="utf-8")
    summary = Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
    assert "STALE REPORT" not in report_text
    assert "STALE REPORT" not in summary
    assert "# Eval Report" in report_text
    assert "Conclusion: **PASS**" in summary
    assert not list(report.parent.glob(".release-gate.md.*.tmp"))


def test_blocking_gate_publishes_report_and_returns_underlying_status(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    _write_run(workspace / "candidate.json", run_id="candidate", correct=False)

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.BLOCKED
    outputs = _read_outputs(Path(environment["GITHUB_OUTPUT"]))
    assert outputs["conclusion"] == "fail"
    report = workspace / outputs["report"]
    assert report.is_file()
    assert "`accuracy_delta`" in report.read_text(encoding="utf-8")
    assert "Conclusion: **FAIL**" in Path(environment["GITHUB_STEP_SUMMARY"]).read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("correct", [True, False])
def test_action_decision_and_report_match_compare_cli(
    action_environment: tuple[Path, dict[str, str]], correct: bool
) -> None:
    workspace, environment = action_environment
    _write_run(workspace / "candidate.json", run_id="candidate", correct=correct)

    action_status = github_action_compare.main(environment)
    cli_report = workspace / "reports/cli-report.md"
    cli_status = run_compare_command(
        baseline_path=workspace / "baseline.json",
        candidate_path=workspace / "candidate.json",
        threshold_config_path=workspace / "thresholds.json",
        report_path=cli_report,
    )

    assert action_status == cli_status
    assert (workspace / environment["EVAL_LAB_REPORT"]).read_bytes() == cli_report.read_bytes()


def test_compare_error_never_summarizes_or_relabels_stale_target(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    (workspace / "baseline.json").write_text("not-json\n", encoding="utf-8")
    report = workspace / environment["EVAL_LAB_REPORT"]
    report.parent.mkdir()
    stale = "STALE DECISION: PASS\n"
    report.write_text(stale, encoding="utf-8")

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.ACTION_ERROR
    assert report.read_text(encoding="utf-8") == stale
    outputs = _read_outputs(Path(environment["GITHUB_OUTPUT"]))
    assert outputs == {"report": "", "conclusion": "error"}
    summary = Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
    assert "Conclusion: **ERROR**" in summary
    assert "STALE DECISION" not in summary
    assert not list(report.parent.glob(".release-gate.md.*.tmp"))


@pytest.mark.parametrize(
    ("input_name", "unsafe_value"),
    [
        ("EVAL_LAB_BASELINE", "../outside.json"),
        ("EVAL_LAB_CANDIDATE", "../outside.json"),
        ("EVAL_LAB_THRESHOLD_CONFIG", "../outside.json"),
        ("EVAL_LAB_REPORT", "../outside-report.md"),
    ],
)
def test_paths_cannot_traverse_outside_workspace(
    action_environment: tuple[Path, dict[str, str]],
    input_name: str,
    unsafe_value: str,
) -> None:
    workspace, environment = action_environment
    (workspace.parent / "outside.json").write_text("{}\n", encoding="utf-8")
    environment[input_name] = unsafe_value

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.ACTION_ERROR
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"]))["conclusion"] == "error"
    assert not (workspace.parent / "outside-report.md").exists()


@pytest.mark.parametrize(
    "input_name",
    [
        "GITHUB_WORKSPACE",
        "EVAL_LAB_BASELINE",
        "EVAL_LAB_CANDIDATE",
        "EVAL_LAB_THRESHOLD_CONFIG",
        "EVAL_LAB_REPORT",
    ],
)
def test_path_inputs_reject_newlines(
    action_environment: tuple[Path, dict[str, str]], input_name: str
) -> None:
    _, environment = action_environment
    environment[input_name] += "\nconclusion=pass"

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.ACTION_ERROR
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"])) == {
        "report": "",
        "conclusion": "error",
    }


def test_input_symlink_cannot_escape_workspace(
    action_environment: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    workspace, environment = action_environment
    outside = tmp_path / "outside-run.json"
    _write_run(outside, run_id="outside", correct=True)
    (workspace / "linked-run.json").symlink_to(outside)
    environment["EVAL_LAB_BASELINE"] = "linked-run.json"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR


def test_report_target_rejects_symlink_even_when_destination_is_internal(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    actual = workspace / "actual.md"
    actual.write_text("keep\n", encoding="utf-8")
    (workspace / "linked-report.md").symlink_to(actual)
    environment["EVAL_LAB_REPORT"] = "linked-report.md"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert actual.read_text(encoding="utf-8") == "keep\n"


def test_shell_metacharacters_are_plain_path_characters(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    special_baseline = workspace / "baseline; touch injected.json"
    _write_run(special_baseline, run_id="baseline-special", correct=True)
    environment["EVAL_LAB_BASELINE"] = special_baseline.name
    environment["EVAL_LAB_CANDIDATE"] = special_baseline.name
    environment["EVAL_LAB_REPORT"] = "reports/result $(touch injected).md"

    assert github_action_compare.main(environment) == github_action_compare.PASS
    assert (workspace / environment["EVAL_LAB_REPORT"]).is_file()
    assert not (workspace / "injected").exists()


def test_summary_html_escapes_report_content_and_path(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    _write_run(
        workspace / "candidate.json",
        run_id="</pre><script>not-markup</script>",
        correct=True,
    )
    environment["EVAL_LAB_REPORT"] = "reports/<b>decision</b>.md"

    assert github_action_compare.main(environment) == github_action_compare.PASS

    summary = Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
    assert "<script>not-markup</script>" not in summary
    assert "&lt;script&gt;not-markup&lt;/script&gt;" in summary
    assert "Report: <code>reports/&lt;b&gt;decision&lt;/b&gt;.md</code>" in summary


def test_report_cannot_overwrite_an_input(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    original = (workspace / "baseline.json").read_bytes()
    environment["EVAL_LAB_REPORT"] = "baseline.json"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert (workspace / "baseline.json").read_bytes() == original


def _read_outputs(path: Path) -> dict[str, str]:
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines())


def _write_thresholds(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "max_accuracy_drop": 0.0,
                "max_invalid_output_rate_increase": 0.0,
                "max_unsafe_auto_approval_rate_increase": 0.0,
                "max_latency_p95_delta_ms": 0.0,
                "max_cost_per_case_delta_usd": 0.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_run(path: Path, *, run_id: str, correct: bool) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "run_type": "test",
                "dataset_hash": "sha256:test-dataset",
                "candidate_version": run_id,
                "validator_version": "test-v1",
                "threshold_config_version": "test-v1",
                "status": "completed",
                "started_at": "2026-07-13T00:00:00+00:00",
                "completed_at": "2026-07-13T00:00:01+00:00",
                "cost_total_usd": 0.0,
                "cost_per_case_usd": 0.0,
                "latency_ms_p50": 10.0,
                "latency_ms_p95": 10.0,
                "max_candidate_retries": 0,
                "case_results": [
                    {
                        "case_id": "case-1",
                        "output": {"correct": correct},
                        "validator_results": [],
                        "cost_usd": 0.0,
                        "latency_ms": 10.0,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
