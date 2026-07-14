from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eval_ground_truth_lab.cli import run_compare_command
from tools import github_action_compare

MAX_DECISION_MAGNITUDE = 2**53 - 1


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


@pytest.mark.parametrize(
    ("artifact", "status"),
    [
        ("baseline.json", "running"),
        ("baseline.json", "interrupted"),
        ("candidate.json", "running"),
        ("candidate.json", "interrupted"),
    ],
)
def test_non_completed_run_can_never_publish_a_pass(
    action_environment: tuple[Path, dict[str, str]], artifact: str, status: str
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / artifact, status=status)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("artifact", ["baseline.json", "candidate.json"])
def test_empty_completed_run_can_never_publish_a_pass(
    action_environment: tuple[Path, dict[str, str]], artifact: str
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / artifact, case_results=[])

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("completed_at", [None, "", "   "])
def test_completed_run_requires_completion_timestamp(
    action_environment: tuple[Path, dict[str, str]], completed_at: object
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / "candidate.json", completed_at=completed_at)

    _assert_action_error_removes_stale(workspace, environment)


def test_candidate_cannot_omit_a_failing_baseline_case(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    omitted = dict(baseline["case_results"][0])
    omitted["case_id"] = "case-omitted-by-candidate"
    omitted["output"] = {"correct": False}
    baseline["case_results"].append(omitted)
    _write_json(workspace / "baseline.json", baseline)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("artifact", ["baseline.json", "candidate.json"])
def test_duplicate_case_ids_are_rejected(
    action_environment: tuple[Path, dict[str, str]], artifact: str
) -> None:
    workspace, environment = action_environment
    run = _read_json(workspace / artifact)
    run["case_results"].append(dict(run["case_results"][0]))
    _write_json(workspace / artifact, run)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("case_id", ["", "   "])
def test_empty_case_ids_are_rejected(
    action_environment: tuple[Path, dict[str, str]], case_id: str
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["case_id"] = case_id
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


def test_mismatched_validator_versions_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / "candidate.json", validator_version="other-validator")

    _assert_action_error_removes_stale(workspace, environment)


def test_mismatched_threshold_config_versions_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / "candidate.json", threshold_config_version="other-thresholds")

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("version", ["", None, 7, "other-threshold-policy"])
def test_threshold_policy_version_must_match_both_runs(
    action_environment: tuple[Path, dict[str, str]], version: object
) -> None:
    workspace, environment = action_environment
    thresholds = _read_json(workspace / "thresholds.json")
    thresholds["version"] = version
    _write_json(workspace / "thresholds.json", thresholds)

    _assert_action_error_removes_stale(workspace, environment)


def test_threshold_policy_version_is_required(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    thresholds = _read_json(workspace / "thresholds.json")
    thresholds.pop("version")
    _write_json(workspace / "thresholds.json", thresholds)

    _assert_action_error_removes_stale(workspace, environment)


def test_candidate_cannot_drop_a_failing_validator_result(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    candidate = _read_json(workspace / "candidate.json")
    failing = {
        "validator_id": "test.unsafe_auto_approval",
        "passed": False,
        "category": "unsafe_auto_approval",
    }
    baseline["case_results"][0]["validator_results"].append(failing)
    _write_json(workspace / "baseline.json", baseline)
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


def test_candidate_cannot_drop_all_validator_results(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["validator_results"] = []
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


def test_both_runs_with_empty_validator_results_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        artifact = _read_json(workspace / filename)
        artifact["case_results"][0]["validator_results"] = []
        _write_json(workspace / filename, artifact)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "category",
    [
        "unsafe_auto_approval",
        "invalid_structured_output",
        "wrong_category",
        "adapter_error",
        "cost_regression",
        "evidence_mismatch",
    ],
)
def test_same_validator_failure_regression_returns_fresh_blocking_report(
    action_environment: tuple[Path, dict[str, str]], category: str
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate_result = candidate["case_results"][0]["validator_results"][0]
    candidate_result.update({"passed": False, "category": category})
    _write_json(workspace / "candidate.json", candidate)
    report = workspace / environment["EVAL_LAB_REPORT"]
    report.parent.mkdir()
    report.write_text("STALE PASS\n", encoding="utf-8")

    assert github_action_compare.main(environment) == github_action_compare.BLOCKED
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"])) == {
        "report": "reports/release-gate.md",
        "conclusion": "fail",
    }
    report_text = report.read_text(encoding="utf-8")
    assert "STALE PASS" not in report_text
    assert f"`{category}`" in report_text
    assert "`test.correctness`" in report_text
    assert "## Validator Receipt Regressions" in report_text
    assert "| `validator_receipt_regression` | `fail` | 1 |" in report_text
    assert f"| `case-1` | `test.correctness` | `{category}` |" in report_text
    if category not in {"unsafe_auto_approval", "invalid_structured_output"}:
        expected_gate_rules = {
            "accuracy_delta": "delta ≥ 0",
            "invalid_output_rate": "delta ≤ 0",
            "unsafe_auto_approval_rate": "delta ≤ 0",
            "latency_ms_p95_delta": "delta ≤ 0",
            "cost_per_case_delta": "delta ≤ 0",
        }
        for metric, gate_rule in expected_gate_rules.items():
            assert f"| `{metric}` | `0` | `{gate_rule}` | `pass` |" in report_text
    assert "Conclusion: **FAIL**" in Path(environment["GITHUB_STEP_SUMMARY"]).read_text(
        encoding="utf-8"
    )


def test_multiple_validator_receipt_regressions_are_reported_deterministically(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    baseline["case_results"][0]["validator_results"].append(
        {
            "validator_id": "test.adapter",
            "passed": True,
            "category": "none",
        }
    )
    _write_json(workspace / "baseline.json", baseline)
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["validator_results"][0].update(
        {"passed": False, "category": "wrong_category"}
    )
    candidate["case_results"][0]["validator_results"].append(
        {
            "validator_id": "test.adapter",
            "passed": False,
            "category": "adapter_error",
        }
    )
    _write_json(workspace / "candidate.json", candidate)

    assert github_action_compare.main(environment) == github_action_compare.BLOCKED
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert "| `validator_receipt_regression` | `fail` | 2 |" in report
    adapter_row = "| `case-1` | `test.adapter` | `adapter_error` |"
    correctness_row = "| `case-1` | `test.correctness` | `wrong_category` |"
    assert adapter_row in report
    assert correctness_row in report
    assert report.index(adapter_row) < report.index(correctness_row)


def test_baseline_known_validator_failure_is_not_a_new_regression(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        run["case_results"][0]["validator_results"][0].update(
            {"passed": False, "category": "evidence_mismatch"}
        )
        _write_json(workspace / filename, run)

    assert github_action_compare.main(environment) == github_action_compare.PASS
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"]))["conclusion"] == "pass"
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert "`evidence_mismatch`" in report
    assert "## Validator Receipt Regressions" not in report


def test_candidate_validator_recovery_is_not_a_regression(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    baseline["case_results"][0]["validator_results"][0].update(
        {"passed": False, "category": "wrong_category"}
    )
    _write_json(workspace / "baseline.json", baseline)

    assert github_action_compare.main(environment) == github_action_compare.PASS
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"]))["conclusion"] == "pass"
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert "## Validator Receipt Regressions" not in report


def test_duplicate_validator_ids_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    existing = dict(candidate["case_results"][0]["validator_results"][0])
    candidate["case_results"][0]["validator_results"].append(existing)
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("validator_id", ""),
        ("validator_id", 7),
        ("passed", "false"),
        ("passed", 1),
        ("category", ""),
        ("category", None),
        ("message", 7),
        ("message", None),
        ("case_id", "other-case"),
        ("case_id", None),
    ],
)
def test_validator_result_structure_is_strict(
    action_environment: tuple[Path, dict[str, str]], field: str, value: object
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["validator_results"][0][field] = value
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("passed", "category"),
    [(True, "unsafe_auto_approval"), (False, "none")],
)
def test_validator_pass_category_semantics_are_consistent(
    action_environment: tuple[Path, dict[str, str]], passed: bool, category: str
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    receipt = candidate["case_results"][0]["validator_results"][0]
    receipt.update({"passed": passed, "category": category})
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("field", "unsafe_value"),
    [
        ("dataset_hash", "sha256:test|forged"),
        ("candidate_version", "candidate`forged"),
        ("validator_version", "validator|forged"),
        ("threshold_config_version", "thresholds`forged"),
    ],
)
def test_report_metadata_rejects_markdown_structural_delimiters(
    action_environment: tuple[Path, dict[str, str]], field: str, unsafe_value: str
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        _update_json(workspace / filename, **{field: unsafe_value})
    if field == "threshold_config_version":
        _update_json(workspace / "thresholds.json", version=unsafe_value)

    _assert_action_error_removes_stale(workspace, environment)


def test_run_id_cannot_inject_a_forged_report_heading(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    forged = "candidate\n\n# Eval Report\n\n## Decision: PASS"
    _update_json(workspace / "candidate.json", run_id=forged, candidate_version="candidate")

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("field", "unsafe_value"),
    [
        ("case_id", "case|forged"),
        ("validator_id", "validator`forged"),
        ("category", "unsafe|forged"),
    ],
)
def test_case_receipt_cells_reject_markdown_structural_delimiters(
    action_environment: tuple[Path, dict[str, str]], field: str, unsafe_value: str
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        case = run["case_results"][0]
        receipt = case["validator_results"][0]
        receipt.update({"passed": False, "category": "unsafe_auto_approval"})
        if field == "case_id":
            case["case_id"] = unsafe_value
        else:
            receipt[field] = unsafe_value
        _write_json(workspace / filename, run)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("message", ["<b>FORGED PASS</b>", "`FORGED PASS`", "safe | FORGED"])
def test_validator_message_cannot_inject_markdown_or_html(
    action_environment: tuple[Path, dict[str, str]], message: str
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        receipt = run["case_results"][0]["validator_results"][0]
        receipt.update(
            {
                "passed": False,
                "category": "unsafe_auto_approval",
                "message": message,
            }
        )
        _write_json(workspace / filename, run)

    _assert_action_error_removes_stale(workspace, environment)


def test_validator_message_markdown_links_and_autolinks_render_as_inert_text(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    receipt = candidate["case_results"][0]["validator_results"][0]
    receipt.update(
        {
            "passed": False,
            "category": "adapter_error",
            "message": (
                r"[forged](https://evil.example) "
                r"\[escaped](https://evil.example/second) "
                "operator@evil.example"
            ),
        }
    )
    _write_json(workspace / "candidate.json", candidate)

    assert github_action_compare.main(environment) == github_action_compare.BLOCKED
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert "[forged](https://evil.example)" not in report
    assert "https://evil.example" not in report
    assert "operator@evil.example" not in report
    assert (
        "&#91;forged&#93;&#40;https&#58;&#47;&#47;evil&#46;example&#41; "
        "&#92;&#91;escaped&#93;&#40;https&#58;&#47;&#47;evil&#46;example&#47;second&#41; "
        "operator&#64;evil&#46;example"
    ) in report


def test_mismatched_run_types_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / "candidate.json", run_type="other-harness")

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    ["cost_total_usd", "cost_per_case_usd", "latency_ms_p50", "latency_ms_p95"],
)
def test_decision_aggregates_must_match_complete_case_results(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate[field] = float(candidate[field]) + 1.0
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


def test_high_magnitude_cost_cannot_hide_aggregate_difference(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    candidate_path = workspace / "candidate.json"
    candidate = _read_json(candidate_path)
    candidate["case_results"][0]["cost_usd"] = 1_000_000_000_000.5
    candidate["cost_total_usd"] = 1_000_000_000_000.0
    candidate["cost_per_case_usd"] = 1_000_000_000_000.0
    _write_json(candidate_path, candidate)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("metric", "case_field", "aggregate_fields", "threshold_field"),
    [
        (
            "cost_per_case_delta",
            "cost_usd",
            ("cost_total_usd", "cost_per_case_usd"),
            "max_cost_per_case_delta_usd",
        ),
        (
            "latency_ms_p95_delta",
            "latency_ms",
            ("latency_ms_p50", "latency_ms_p95"),
            "max_latency_p95_delta_ms",
        ),
    ],
)
def test_exact_high_magnitude_delta_blocks_in_action(
    action_environment: tuple[Path, dict[str, str]],
    metric: str,
    case_field: str,
    aggregate_fields: tuple[str, str],
    threshold_field: str,
) -> None:
    workspace, environment = action_environment
    for filename, value in (
        ("baseline.json", 1_000_000_000_000.0),
        ("candidate.json", 1_000_000_000_000.1),
    ):
        run = _read_json(workspace / filename)
        run["case_results"][0][case_field] = value
        for aggregate_field in aggregate_fields:
            run[aggregate_field] = value
        _write_json(workspace / filename, run)
    thresholds = _read_json(workspace / "thresholds.json")
    thresholds[threshold_field] = 0.09999
    _write_json(workspace / "thresholds.json", thresholds)

    assert github_action_compare.main(environment) == github_action_compare.BLOCKED
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert f"| `{metric}` | `0.1` | `delta ≤ 0.09999` | `fail` |" in report
    assert "## Validator Receipt Regressions" not in report


@pytest.mark.parametrize(
    ("metric", "category", "expected_delta", "threshold_field", "gate"),
    [
        (
            "accuracy_delta",
            None,
            "-1/3",
            "max_accuracy_drop",
            "delta ≥ -0.3333333333333333",
        ),
        (
            "invalid_output_rate",
            "invalid_structured_output",
            "1/3",
            "max_invalid_output_rate_increase",
            "delta ≤ 0.3333333333333333",
        ),
        (
            "unsafe_auto_approval_rate",
            "unsafe_auto_approval",
            "1/3",
            "max_unsafe_auto_approval_rate_increase",
            "delta ≤ 0.3333333333333333",
        ),
    ],
)
def test_exact_one_third_rate_boundary_blocks_in_action(
    action_environment: tuple[Path, dict[str, str]],
    metric: str,
    category: str | None,
    expected_delta: str,
    threshold_field: str,
    gate: str,
) -> None:
    workspace, environment = action_environment
    baseline = _expand_run_to_three_cases(_read_json(workspace / "baseline.json"))
    candidate = _expand_run_to_three_cases(_read_json(workspace / "candidate.json"))
    if metric == "accuracy_delta":
        baseline["case_results"][2]["output"]["correct"] = False
        candidate["case_results"][1]["output"]["correct"] = False
        candidate["case_results"][2]["output"]["correct"] = False
    else:
        baseline["case_results"][0]["validator_results"][0].update(
            {"passed": False, "category": "baseline_known_failure"}
        )
        candidate["case_results"][0]["validator_results"][0].update(
            {"passed": False, "category": category}
        )
    _write_json(workspace / "baseline.json", baseline)
    _write_json(workspace / "candidate.json", candidate)
    thresholds = _read_json(workspace / "thresholds.json")
    thresholds[threshold_field] = 0.3333333333333333
    _write_json(workspace / "thresholds.json", thresholds)

    assert github_action_compare.main(environment) == github_action_compare.BLOCKED
    report = (workspace / environment["EVAL_LAB_REPORT"]).read_text(encoding="utf-8")
    assert f"| `{metric}` | `{expected_delta}` | `{gate}` | `fail` |" in report
    assert "## Validator Receipt Regressions" not in report


def test_nonrepresentable_integer_cost_cannot_collapse_to_claimed_aggregate(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    baseline["case_results"][0]["cost_usd"] = 2**53
    baseline["cost_total_usd"] = 2**53
    baseline["cost_per_case_usd"] = 2**53
    _write_json(workspace / "baseline.json", baseline)
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["cost_usd"] = 2**53 + 1
    candidate["cost_total_usd"] = 2**53
    candidate["cost_per_case_usd"] = 2**53
    _write_json(workspace / "candidate.json", candidate)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "value",
    [MAX_DECISION_MAGNITUDE, float(MAX_DECISION_MAGNITUDE)],
    ids=["integer", "decimal-token"],
)
def test_supported_numeric_max_boundary_is_accepted(
    action_environment: tuple[Path, dict[str, str]], value: int | float
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        run["case_results"][0]["cost_usd"] = value
        run["cost_total_usd"] = value
        run["cost_per_case_usd"] = value
        _write_json(workspace / filename, run)

    assert github_action_compare.main(environment) == github_action_compare.PASS
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"]))["conclusion"] == "pass"


@pytest.mark.parametrize(
    "value",
    [2**53, 2**53 + 1, float(2**53)],
    ids=["integer-2pow53", "integer-2pow53-plus-1", "decimal-token-2pow53"],
)
def test_numeric_magnitudes_above_supported_max_are_rejected(
    action_environment: tuple[Path, dict[str, str]], value: int | float
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        run["case_results"][0]["cost_usd"] = value
        run["cost_total_usd"] = value
        run["cost_per_case_usd"] = value
        _write_json(workspace / filename, run)

    _assert_action_error_removes_stale(workspace, environment)


def test_noncanonical_decimal_cannot_collapse_to_same_binary64_value(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = _read_json(workspace / "baseline.json")
    baseline["case_results"][0]["cost_usd"] = 0.1
    baseline["cost_total_usd"] = 0.1
    baseline["cost_per_case_usd"] = 0.1
    _write_json(workspace / "baseline.json", baseline)
    candidate_path = workspace / "candidate.json"
    candidate = _read_json(candidate_path)
    candidate["case_results"][0]["cost_usd"] = "__NONCANONICAL_DECIMAL__"
    candidate["cost_total_usd"] = 0.1
    candidate["cost_per_case_usd"] = 0.1
    _write_json_with_literal(
        candidate_path,
        candidate,
        marker="__NONCANONICAL_DECIMAL__",
        literal="0.10000000000000001",
    )

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost_total_usd", True),
        ("cost_per_case_usd", "0"),
        ("cost_per_case_usd", -0.01),
        ("latency_ms_p50", -1),
        ("latency_ms_p95", False),
    ],
)
def test_invalid_aggregate_decision_metrics_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str, value: object
) -> None:
    workspace, environment = action_environment
    _update_json(workspace / "candidate.json", **{field: value})

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    ["cost_total_usd", "cost_per_case_usd", "latency_ms_p50", "latency_ms_p95"],
)
def test_overflowed_aggregate_decision_metrics_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    candidate_path = workspace / "candidate.json"
    candidate = _read_json(candidate_path)
    candidate[field] = "__OVERFLOW__"
    _write_json_with_literal(candidate_path, candidate, marker="__OVERFLOW__", literal="1e309")

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("field", ["cost_usd", "latency_ms"])
def test_non_finite_case_metrics_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    candidate_path = workspace / "candidate.json"
    candidate = _read_json(candidate_path)
    candidate["case_results"][0][field] = "__NONFINITE__"
    _write_json_with_literal(
        candidate_path,
        candidate,
        marker="__NONFINITE__",
        literal="NaN",
    )

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    [
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "max_latency_p95_delta_ms",
        "max_cost_per_case_delta_usd",
    ],
)
def test_overflowed_thresholds_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    thresholds = _read_json(thresholds_path)
    thresholds[field] = "__OVERFLOW__"
    _write_json_with_literal(thresholds_path, thresholds, marker="__OVERFLOW__", literal="1e309")

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("invalid_value", [True, "0.0", -0.1])
@pytest.mark.parametrize(
    "field",
    [
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "max_latency_p95_delta_ms",
        "max_cost_per_case_delta_usd",
    ],
)
def test_unsafe_threshold_types_and_negative_values_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str, invalid_value: object
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    thresholds = _read_json(thresholds_path)
    thresholds[field] = invalid_value
    _write_json(thresholds_path, thresholds)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    [
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
    ],
)
def test_rate_and_drop_thresholds_above_one_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    thresholds = _read_json(thresholds_path)
    thresholds[field] = 1.01
    _write_json(thresholds_path, thresholds)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    [
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "max_latency_p95_delta_ms",
        "max_cost_per_case_delta_usd",
    ],
)
def test_missing_threshold_fields_are_rejected(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    thresholds = _read_json(thresholds_path)
    thresholds.pop(field)
    _write_json(thresholds_path, thresholds)

    _assert_action_error_removes_stale(workspace, environment)


def test_unknown_and_duplicate_threshold_fields_are_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    thresholds = _read_json(thresholds_path)
    thresholds["unreviewed_gate_bypass"] = 1
    _write_json(thresholds_path, thresholds)
    _assert_action_error_removes_stale(workspace, environment)


def test_duplicate_threshold_key_is_rejected(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    source = thresholds_path.read_text(encoding="utf-8").rstrip()
    thresholds_path.write_text(
        source[:-1] + ', "max_accuracy_drop": 1}\n',
        encoding="utf-8",
    )

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("invalid_accuracy", [True, "0.8", -0.1, 1.1])
def test_legacy_accuracy_threshold_must_be_numeric_unit_interval(
    action_environment: tuple[Path, dict[str, str]], invalid_accuracy: object
) -> None:
    workspace, environment = action_environment
    _write_gdev_thresholds(workspace / "thresholds.json")
    thresholds = _read_json(workspace / "thresholds.json")
    thresholds["classification_accuracy_min"] = invalid_accuracy
    _write_json(workspace / "thresholds.json", thresholds)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize(
    "field",
    [
        "classification_accuracy_min",
        "max_invalid_structured_output_rate",
        "max_unsafe_auto_approval_rate",
        "max_latency_p95_ms",
        "max_cost_per_case_usd",
    ],
)
def test_legacy_thresholds_must_all_be_finite(
    action_environment: tuple[Path, dict[str, str]], field: str
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    _write_gdev_thresholds(thresholds_path)
    thresholds = _read_json(thresholds_path)
    thresholds[field] = "__OVERFLOW__"
    _write_json_with_literal(thresholds_path, thresholds, marker="__OVERFLOW__", literal="1e309")

    _assert_action_error_removes_stale(workspace, environment)


def test_legacy_thresholds_reject_missing_and_unknown_fields(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    thresholds_path = workspace / "thresholds.json"
    _write_gdev_thresholds(thresholds_path)
    thresholds = _read_json(thresholds_path)
    thresholds.pop("max_cost_per_case_usd")
    thresholds["unreviewed_threshold"] = 0
    _write_json(thresholds_path, thresholds)

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("correct", [True, False])
def test_action_decision_and_no_regression_report_match_compare_cli(
    action_environment: tuple[Path, dict[str, str]],
    correct: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, environment = action_environment
    _write_run(workspace / "candidate.json", run_id="candidate", correct=correct)

    action_status = github_action_compare.main(environment)
    cli_report = workspace / "reports/cli-report.md"
    monkeypatch.chdir(workspace)
    cli_status = run_compare_command(
        baseline_path="baseline.json",
        candidate_path="candidate.json",
        threshold_config_path="thresholds.json",
        report_path=cli_report,
    )

    assert action_status == cli_status
    action_report = (workspace / environment["EVAL_LAB_REPORT"]).read_bytes()
    cli_report_bytes = cli_report.read_bytes()
    assert action_report == cli_report_bytes
    assert b"Validator Receipt Regressions" not in action_report
    assert hashlib.sha256(action_report).hexdigest() == hashlib.sha256(cli_report_bytes).hexdigest()


@pytest.mark.parametrize("output", ["plain text", ["list", 1], None])
def test_non_object_json_outputs_preserve_action_cli_parity(
    action_environment: tuple[Path, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    output: object,
) -> None:
    workspace, environment = action_environment
    for filename in ("baseline.json", "candidate.json"):
        run = _read_json(workspace / filename)
        run["case_results"][0]["output"] = output
        _write_json(workspace / filename, run)

    action_status = github_action_compare.main(environment)
    cli_report = workspace / "reports/non-object-cli-report.md"
    monkeypatch.chdir(workspace)
    cli_status = run_compare_command(
        baseline_path="baseline.json",
        candidate_path="candidate.json",
        threshold_config_path="thresholds.json",
        report_path=cli_report,
    )

    assert action_status == cli_status == github_action_compare.PASS
    assert (workspace / environment["EVAL_LAB_REPORT"]).read_bytes() == cli_report.read_bytes()


def test_valid_legacy_thresholds_match_compare_cli(
    action_environment: tuple[Path, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, environment = action_environment
    _write_gdev_thresholds(workspace / "thresholds.json")

    action_status = github_action_compare.main(environment)
    cli_report = workspace / "reports/legacy-cli-report.md"
    monkeypatch.chdir(workspace)
    cli_status = run_compare_command(
        baseline_path="baseline.json",
        candidate_path="candidate.json",
        threshold_config_path="thresholds.json",
        report_path=cli_report,
    )

    assert action_status == cli_status == github_action_compare.PASS
    assert (workspace / environment["EVAL_LAB_REPORT"]).read_bytes() == cli_report.read_bytes()


def test_tiny_legacy_accuracy_minimum_blocks_with_exact_action_cli_gate(
    action_environment: tuple[Path, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, environment = action_environment
    candidate = _read_json(workspace / "candidate.json")
    candidate["case_results"][0]["output"]["correct"] = False
    _write_json(workspace / "candidate.json", candidate)
    _write_json(
        workspace / "thresholds.json",
        {
            "classification_accuracy_min": 1e-30,
            "max_cost_per_case_usd": 0.0,
            "max_invalid_structured_output_rate": 0.0,
            "max_latency_p95_ms": 0.0,
            "max_unsafe_auto_approval_rate": 0.0,
            "version": "test-v1",
        },
    )

    action_status = github_action_compare.main(environment)
    action_report = workspace / environment["EVAL_LAB_REPORT"]
    action_text = action_report.read_text(encoding="utf-8")

    assert action_status == github_action_compare.BLOCKED
    assert "## Validator Receipt Regressions" not in action_text
    assert (
        "| `accuracy_delta` | `-1` | `delta ≥ -0.999999999999999999999999999999` | `fail` |"
    ) in action_text

    cli_report = workspace / "reports/tiny-legacy-cli-report.md"
    monkeypatch.chdir(workspace)
    cli_status = run_compare_command(
        baseline_path="baseline.json",
        candidate_path="candidate.json",
        threshold_config_path="thresholds.json",
        report_path=cli_report,
    )

    assert cli_status == github_action_compare.BLOCKED
    assert action_report.read_bytes() == cli_report.read_bytes()


def test_compare_error_removes_stale_target_before_any_uploader_can_publish_it(
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
    assert not report.exists()
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
    outside_report = workspace.parent / "outside-report.md"
    if input_name == "EVAL_LAB_REPORT":
        outside_report.write_text("unsafe path stays untouched\n", encoding="utf-8")
    environment[input_name] = unsafe_value

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.ACTION_ERROR
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"]))["conclusion"] == "error"
    if input_name == "EVAL_LAB_REPORT":
        assert outside_report.read_text(encoding="utf-8") == "unsafe path stays untouched\n"
    else:
        assert not outside_report.exists()


@pytest.mark.parametrize(
    ("input_name", "invalid_value"),
    [
        ("EVAL_LAB_BASELINE", "missing-run.json"),
        ("EVAL_LAB_BASELINE", "../outside.json"),
        ("EVAL_LAB_CANDIDATE", ""),
        ("EVAL_LAB_CANDIDATE", "candidate.json\nignored"),
        ("EVAL_LAB_THRESHOLD_CONFIG", "missing-thresholds.json"),
    ],
)
def test_safe_stale_report_is_removed_when_any_input_path_is_invalid(
    action_environment: tuple[Path, dict[str, str]],
    input_name: str,
    invalid_value: str,
) -> None:
    workspace, environment = action_environment
    (workspace.parent / "outside.json").write_text("{}\n", encoding="utf-8")
    environment[input_name] = invalid_value

    _assert_action_error_removes_stale(workspace, environment)


def test_input_symlink_loop_is_an_error_and_removes_safe_stale_report(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    (workspace / "loop-a").symlink_to("loop-b")
    (workspace / "loop-b").symlink_to("loop-a")
    environment["EVAL_LAB_BASELINE"] = "loop-a"

    _assert_action_error_removes_stale(workspace, environment)


@pytest.mark.parametrize("unsafe_suffix", ["\n\n# FORGED PASS", "`forged", "| forged"])
def test_resolved_symlink_target_path_is_safe_for_markdown_report(
    action_environment: tuple[Path, dict[str, str]], unsafe_suffix: str
) -> None:
    workspace, environment = action_environment
    target = workspace / f"baseline{unsafe_suffix}.json"
    _write_run(target, run_id="baseline-target", correct=True)
    (workspace / "linked-baseline.json").symlink_to(target.name)
    environment["EVAL_LAB_BASELINE"] = "linked-baseline.json"

    _assert_action_error_removes_stale(workspace, environment)


def test_invalid_input_user_expansion_removes_safe_stale_report(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    environment["EVAL_LAB_BASELINE"] = "~codex-action-user-does-not-exist-7f3a/run.json"

    _assert_action_error_removes_stale(workspace, environment)


def test_invalid_report_user_expansion_does_not_touch_literal_path(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    literal = workspace / "~codex-action-user-does-not-exist-7f3a" / "report.md"
    literal.parent.mkdir()
    literal.write_text("literal path stays untouched\n", encoding="utf-8")
    environment["EVAL_LAB_REPORT"] = "~codex-action-user-does-not-exist-7f3a/report.md"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert literal.read_text(encoding="utf-8") == "literal path stays untouched\n"


def test_report_symlink_loop_is_rejected_without_touching_it(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    report = workspace / "report-loop-a"
    report.symlink_to("report-loop-b")
    (workspace / "report-loop-b").symlink_to("report-loop-a")
    environment["EVAL_LAB_REPORT"] = report.name

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert report.is_symlink()
    assert (workspace / "report-loop-b").is_symlink()


def test_report_alias_is_never_removed_when_another_input_is_invalid(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = workspace / "baseline.json"
    original = baseline.read_bytes()
    environment["EVAL_LAB_REPORT"] = "baseline.json"
    environment["EVAL_LAB_CANDIDATE"] = "missing-candidate.json"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert baseline.read_bytes() == original
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"])) == {
        "report": "",
        "conclusion": "error",
    }


def test_hardlink_report_alias_is_never_removed(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    baseline = workspace / "baseline.json"
    report = workspace / "hardlink-report.json"
    report.hardlink_to(baseline)
    original = baseline.read_bytes()
    environment["EVAL_LAB_REPORT"] = report.name
    environment["EVAL_LAB_CANDIDATE"] = "missing-candidate.json"

    assert github_action_compare.main(environment) == github_action_compare.ACTION_ERROR
    assert baseline.read_bytes() == original
    assert report.read_bytes() == original


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


def test_summary_html_escapes_report_path(
    action_environment: tuple[Path, dict[str, str]],
) -> None:
    workspace, environment = action_environment
    environment["EVAL_LAB_REPORT"] = "reports/<b>decision</b>.md"

    assert github_action_compare.main(environment) == github_action_compare.PASS

    summary = Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
    assert "reports/<b>decision</b>.md" not in summary
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


def _assert_action_error_removes_stale(workspace: Path, environment: dict[str, str]) -> None:
    report = workspace / environment["EVAL_LAB_REPORT"]
    report.parent.mkdir(parents=True, exist_ok=True)
    stale = "STALE DECISION: PASS\n"
    report.write_text(stale, encoding="utf-8")

    exit_code = github_action_compare.main(environment)

    assert exit_code == github_action_compare.ACTION_ERROR
    assert not report.exists()
    assert _read_outputs(Path(environment["GITHUB_OUTPUT"])) == {
        "report": "",
        "conclusion": "error",
    }
    summary = Path(environment["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
    assert "Conclusion: **ERROR**" in summary
    assert "Conclusion: **PASS**" not in summary
    assert "STALE DECISION" not in summary
    assert not list(report.parent.glob(".release-gate.md.*.tmp"))


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _update_json(path: Path, **updates: object) -> None:
    value = _read_json(path)
    value.update(updates)
    _write_json(path, value)


def _write_json_with_literal(path: Path, value: dict, *, marker: str, literal: str) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    encoded_marker = json.dumps(marker)
    assert payload.count(encoded_marker) == 1
    path.write_text(payload.replace(encoded_marker, literal), encoding="utf-8")


def _write_thresholds(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "max_accuracy_drop": 0.0,
                "max_invalid_output_rate_increase": 0.0,
                "max_unsafe_auto_approval_rate_increase": 0.0,
                "max_latency_p95_delta_ms": 0.0,
                "max_cost_per_case_delta_usd": 0.0,
                "version": "test-v1",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_gdev_thresholds(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "classification_accuracy_min": 0.8,
                "max_cost_per_case_usd": 0.01,
                "max_invalid_structured_output_rate": 0.0,
                "max_latency_p95_ms": 1_500,
                "max_unsafe_auto_approval_rate": 0.0,
                "version": "test-v1",
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
                        "validator_results": [
                            {
                                "validator_id": "test.correctness",
                                "passed": True,
                                "category": "none",
                            }
                        ],
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


def _expand_run_to_three_cases(run: dict) -> dict:
    first = run["case_results"][0]
    for index in (2, 3):
        case = json.loads(json.dumps(first))
        case["case_id"] = f"case-{index}"
        run["case_results"].append(case)
    run["cost_total_usd"] = sum(case["cost_usd"] for case in run["case_results"])
    run["cost_per_case_usd"] = run["cost_total_usd"] / len(run["case_results"])
    latencies = sorted(case["latency_ms"] for case in run["case_results"])
    run["latency_ms_p50"] = latencies[1]
    run["latency_ms_p95"] = latencies[-1]
    return run
