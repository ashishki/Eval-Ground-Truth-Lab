from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab.cli import COMPARE_INPUT_ERROR, run_compare_command
from eval_ground_truth_lab.compare import (
    MAX_DECISION_NUMBER,
    ComparisonInputError,
    compare_runs,
    read_run_artifact,
    read_threshold_config,
)


def test_native_and_legacy_threshold_schemas_preserve_comparison_semantics(
    tmp_path: Path,
) -> None:
    native = _write_json(tmp_path / "native.json", _thresholds())
    legacy = _write_json(
        tmp_path / "legacy.json",
        {
            "classification_accuracy_min": 0.8,
            "max_cost_per_case_usd": 0.05,
            "max_invalid_structured_output_rate": 0.1,
            "max_latency_p95_ms": 250,
            "max_unsafe_auto_approval_rate": 0.0,
            "version": "policy-v1",
        },
    )

    native_config = read_threshold_config(native)
    legacy_config = read_threshold_config(legacy)

    assert native_config.version == legacy_config.version == "policy-v1"
    assert native_config.max_accuracy_drop == 0.0
    assert legacy_config.max_accuracy_drop == pytest.approx(0.2)
    assert legacy_config.max_invalid_output_rate_increase == 0.1
    assert legacy_config.max_latency_p95_delta_ms == 250
    assert legacy_config.max_cost_per_case_delta_usd == 0.05


def test_legacy_accuracy_minimum_retains_exact_decimal_complement(tmp_path: Path) -> None:
    legacy = _write_json(
        tmp_path / "legacy.json",
        {
            "classification_accuracy_min": 0.7,
            "max_cost_per_case_usd": 0.0,
            "max_invalid_structured_output_rate": 0.0,
            "max_latency_p95_ms": 0.0,
            "max_unsafe_auto_approval_rate": 0.0,
            "version": "policy-v1",
        },
    )

    config = read_threshold_config(legacy)

    assert config.max_accuracy_drop == 0.3
    assert config.exact_value("max_accuracy_drop") == "0.3"


def test_legacy_tiny_accuracy_minimum_cannot_round_complement_to_one(tmp_path: Path) -> None:
    policy = {
        "classification_accuracy_min": 1e-30,
        "max_cost_per_case_usd": 0.0,
        "max_invalid_structured_output_rate": 0.0,
        "max_latency_p95_ms": 0.0,
        "max_unsafe_auto_approval_rate": 0.0,
        "version": "policy-v1",
    }
    baseline_raw = _run_mapping(run_id="baseline")
    candidate_raw = _run_mapping(run_id="candidate")
    candidate_raw["case_results"][0]["output"]["correct"] = False
    thresholds = read_threshold_config(_write_json(tmp_path / "legacy.json", policy))

    comparison = compare_runs(
        baseline=read_run_artifact(_write_json(tmp_path / "baseline.json", baseline_raw)),
        candidate=read_run_artifact(_write_json(tmp_path / "candidate.json", candidate_raw)),
        thresholds=thresholds,
    )

    assert thresholds.max_accuracy_drop == 1.0
    assert thresholds.exact_value("max_accuracy_drop") == ("0.999999999999999999999999999999")
    assert comparison.exact_deltas["accuracy_delta"] == "-1"
    assert comparison.threshold_status["accuracy_delta"] == "fail"


def test_native_tiny_threshold_retains_its_exact_decimal_value(tmp_path: Path) -> None:
    policy = _thresholds()
    policy["max_accuracy_drop"] = 1e-30

    thresholds = read_threshold_config(_write_json(tmp_path / "native.json", policy))

    assert thresholds.max_accuracy_drop == 1e-30
    assert thresholds.exact_value("max_accuracy_drop") == ("0.000000000000000000000000000001")


def test_validator_only_outputs_remain_valid_and_keep_legacy_false_accuracy_semantics(
    tmp_path: Path,
) -> None:
    baseline_raw = _run_mapping(run_id="baseline")
    candidate_raw = _run_mapping(run_id="candidate")
    baseline_raw["case_results"][0]["output"] = {"answer": "baseline"}
    candidate_raw["case_results"][0]["output"] = {"answer": "candidate"}
    baseline = read_run_artifact(_write_json(tmp_path / "baseline.json", baseline_raw))
    candidate = read_run_artifact(_write_json(tmp_path / "candidate.json", candidate_raw))
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", _thresholds()))

    comparison = compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)

    assert comparison.accuracy_delta == 0.0
    assert comparison.has_blocking_failure is False


@pytest.mark.parametrize("output", ["plain text", ["list", 1], None])
def test_non_object_json_outputs_preserve_legacy_not_correct_semantics(
    tmp_path: Path,
    output: object,
) -> None:
    baseline_raw = _run_mapping(run_id="baseline")
    candidate_raw = _run_mapping(run_id="candidate")
    baseline_raw["case_results"][0]["output"] = output
    candidate_raw["case_results"][0]["output"] = output
    baseline = read_run_artifact(_write_json(tmp_path / "baseline.json", baseline_raw))
    candidate = read_run_artifact(_write_json(tmp_path / "candidate.json", candidate_raw))
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", _thresholds()))

    comparison = compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)

    assert comparison.accuracy_delta == 0.0
    assert comparison.exact_deltas["accuracy_delta"] == "0"
    assert comparison.has_blocking_failure is False


def test_validator_outcome_and_category_changes_are_blocking_not_contract_errors(
    tmp_path: Path,
) -> None:
    baseline_raw = _run_mapping(run_id="baseline")
    candidate_raw = _run_mapping(run_id="candidate")
    candidate_raw["case_results"][0]["validator_results"][0].update(
        {
            "passed": False,
            "category": "invalid_structured_output",
            "message": "candidate emitted invalid output",
        }
    )
    baseline = read_run_artifact(_write_json(tmp_path / "baseline.json", baseline_raw))
    candidate = read_run_artifact(_write_json(tmp_path / "candidate.json", candidate_raw))
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", _thresholds()))

    comparison = compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)

    assert comparison.invalid_output_rate_delta == 1.0
    assert comparison.threshold_status["invalid_output_rate"] == "fail"
    assert comparison.has_blocking_failure is True


@pytest.mark.parametrize("status", ["running", "interrupted", "unknown"])
def test_non_completed_runs_are_rejected(tmp_path: Path, status: str) -> None:
    raw = _run_mapping()
    raw["status"] = status

    with pytest.raises(ComparisonInputError, match="status must be exactly 'completed'"):
        read_run_artifact(_write_json(tmp_path / "run.json", raw))


def test_empty_and_one_sided_truncated_case_sets_are_rejected(tmp_path: Path) -> None:
    empty = _run_mapping()
    empty["case_results"] = []
    empty.update(
        cost_total_usd=0.0,
        cost_per_case_usd=0.0,
        latency_ms_p50=0.0,
        latency_ms_p95=0.0,
    )
    with pytest.raises(ComparisonInputError, match="at least one completed case"):
        read_run_artifact(_write_json(tmp_path / "empty.json", empty))

    baseline_raw = _run_mapping(run_id="baseline")
    second = json.loads(json.dumps(baseline_raw["case_results"][0]))
    second["case_id"] = "case-2"
    second["validator_results"][0]["case_id"] = "case-2"
    baseline_raw["case_results"].append(second)
    _recalculate_metrics(baseline_raw)
    baseline = read_run_artifact(_write_json(tmp_path / "baseline.json", baseline_raw))
    candidate = read_run_artifact(
        _write_json(tmp_path / "candidate.json", _run_mapping(run_id="candidate"))
    )
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", _thresholds()))
    with pytest.raises(ComparisonInputError, match="same case IDs"):
        compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_validator_id", "missing required fields"),
        ("duplicate_validator_id", "duplicate validator ID"),
        ("empty_receipts", "at least one receipt"),
        ("invalid_passed", "passed must be a boolean"),
        ("inconsistent_category", "exactly when passed is true"),
        ("wrong_nested_case", "must match its outer case"),
        ("invalid_evidence", "evidence must be a JSON object"),
    ],
)
def test_sparse_duplicate_and_invalid_validator_receipts_fail_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    raw = _run_mapping()
    receipts = raw["case_results"][0]["validator_results"]
    receipt = receipts[0]
    if mutation == "missing_validator_id":
        receipt.pop("validator_id")
    elif mutation == "duplicate_validator_id":
        receipts.append(dict(receipt))
    elif mutation == "empty_receipts":
        receipts.clear()
    elif mutation == "invalid_passed":
        receipt["passed"] = "true"
    elif mutation == "inconsistent_category":
        receipt["category"] = "unsafe_auto_approval"
    elif mutation == "wrong_nested_case":
        receipt["case_id"] = "other-case"
    elif mutation == "invalid_evidence":
        receipt["evidence"] = []

    with pytest.raises(ComparisonInputError, match=message):
        read_run_artifact(_write_json(tmp_path / "run.json", raw))


def test_duplicate_json_keys_are_rejected_recursively(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "run.json", _run_mapping())
    source = path.read_text(encoding="utf-8")
    marker = '"validator_id": "test.output_contract"'
    assert source.count(marker) == 1
    path.write_text(source.replace(marker, f"{marker},\n        {marker}"), encoding="utf-8")

    with pytest.raises(ComparisonInputError, match="duplicate key 'validator_id'"):
        read_run_artifact(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("cost_total_usd", -1, "non-negative"),
        ("cost_per_case_usd", True, "JSON number"),
        ("latency_ms_p50", "10", "JSON number"),
        ("latency_ms_p95", 11, "complete case-result aggregate"),
    ],
)
def test_invalid_or_inconsistent_aggregate_metrics_are_rejected(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    raw = _run_mapping()
    raw[field] = value

    with pytest.raises(ComparisonInputError, match=message):
        read_run_artifact(_write_json(tmp_path / "run.json", raw))


def test_nonstandard_and_overflowed_numeric_constants_are_rejected(tmp_path: Path) -> None:
    for literal in ("NaN", "Infinity", "1e309"):
        path = _write_json(tmp_path / f"run-{literal}.json", _run_mapping())
        source = path.read_text(encoding="utf-8")
        path.write_text(
            source.replace('"cost_usd": 0.0', f'"cost_usd": {literal}'),
            encoding="utf-8",
        )
        with pytest.raises(ComparisonInputError, match="non-standard|finite|supported maximum"):
            read_run_artifact(path)


def test_integer_rounding_attack_and_decimal_collision_are_rejected_before_coercion(
    tmp_path: Path,
) -> None:
    integer_path = _write_json(tmp_path / "integer.json", _run_mapping())
    integer_source = integer_path.read_text(encoding="utf-8")
    integer_path.write_text(
        integer_source.replace('"cost_usd": 0.0', f'"cost_usd": {2**53 + 1}')
        .replace('"cost_total_usd": 0.0', f'"cost_total_usd": {2**53}')
        .replace('"cost_per_case_usd": 0.0', f'"cost_per_case_usd": {2**53}'),
        encoding="utf-8",
    )
    with pytest.raises(ComparisonInputError, match="supported maximum"):
        read_run_artifact(integer_path)

    decimal_path = _write_json(tmp_path / "decimal.json", _run_mapping())
    decimal_source = decimal_path.read_text(encoding="utf-8")
    decimal_path.write_text(
        decimal_source.replace('"cost_usd": 0.0', '"cost_usd": 0.10000000000000001')
        .replace('"cost_total_usd": 0.0', '"cost_total_usd": 0.1')
        .replace('"cost_per_case_usd": 0.0', '"cost_per_case_usd": 0.1'),
        encoding="utf-8",
    )
    with pytest.raises(ComparisonInputError, match="lossless shortest-round-trip"):
        read_run_artifact(decimal_path)


def test_supported_numeric_boundary_is_accepted_losslessly(tmp_path: Path) -> None:
    raw = _run_mapping()
    raw["case_results"][0]["cost_usd"] = MAX_DECISION_NUMBER
    raw["cost_total_usd"] = MAX_DECISION_NUMBER
    raw["cost_per_case_usd"] = MAX_DECISION_NUMBER

    run = read_run_artifact(_write_json(tmp_path / "run.json", raw))

    assert run.cost_total_usd == float(MAX_DECISION_NUMBER)
    assert run.case_results[0].cost_usd == float(MAX_DECISION_NUMBER)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_accuracy_drop", -0.1, "non-negative"),
        ("max_invalid_output_rate_increase", 1.01, "between 0 and 1"),
        ("max_latency_p95_delta_ms", True, "JSON number"),
        ("max_cost_per_case_delta_usd", "0", "JSON number"),
    ],
)
def test_invalid_thresholds_are_rejected(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    raw = _thresholds()
    raw[field] = value

    with pytest.raises(ComparisonInputError, match=message):
        read_threshold_config(_write_json(tmp_path / "thresholds.json", raw))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("run_type", "other", "same run type"),
        ("validator_version", "other", "same validator version"),
        ("threshold_config_version", "other", "same threshold config version"),
    ],
)
def test_mismatched_run_policy_is_rejected(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    baseline = read_run_artifact(
        _write_json(tmp_path / "baseline.json", _run_mapping(run_id="baseline"))
    )
    candidate_raw = _run_mapping(run_id="candidate")
    candidate_raw[field] = value
    candidate = read_run_artifact(_write_json(tmp_path / "candidate.json", candidate_raw))
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", _thresholds()))

    with pytest.raises(ComparisonInputError, match=message):
        compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)


def test_threshold_file_version_must_match_both_runs(tmp_path: Path) -> None:
    baseline = read_run_artifact(
        _write_json(tmp_path / "baseline.json", _run_mapping(run_id="baseline"))
    )
    candidate = read_run_artifact(
        _write_json(tmp_path / "candidate.json", _run_mapping(run_id="candidate"))
    )
    policy = _thresholds()
    policy["version"] = "other-policy"
    thresholds = read_threshold_config(_write_json(tmp_path / "thresholds.json", policy))

    with pytest.raises(ComparisonInputError, match="version must match both"):
        compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)


def test_cli_invalid_input_returns_two_removes_stale_report_and_is_not_a_threshold_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text("not-json\n", encoding="utf-8")
    candidate = _write_json(tmp_path / "candidate.json", _run_mapping(run_id="candidate"))
    thresholds = _write_json(tmp_path / "thresholds.json", _thresholds())
    report = tmp_path / "report.md"
    report.write_text("STALE PASS\n", encoding="utf-8")

    status = run_compare_command(
        baseline_path=baseline,
        candidate_path=candidate,
        threshold_config_path=thresholds,
        report_path=report,
    )

    captured = capsys.readouterr()
    assert status == COMPARE_INPUT_ERROR == 2
    assert not report.exists()
    assert captured.out == ""
    assert "Eval comparison error:" in captured.err
    assert "threshold fail" not in captured.err.lower()


def test_cli_invalid_input_does_not_create_a_new_report_parent(tmp_path: Path) -> None:
    report = tmp_path / "not-created" / "report.md"

    status = run_compare_command(
        baseline_path=tmp_path / "missing-baseline.json",
        candidate_path=tmp_path / "missing-candidate.json",
        threshold_config_path=tmp_path / "missing-thresholds.json",
        report_path=report,
    )

    assert status == COMPARE_INPUT_ERROR
    assert not report.parent.exists()


def test_cli_report_alias_and_symlink_boundaries_never_modify_inputs(tmp_path: Path) -> None:
    baseline = _write_json(tmp_path / "baseline.json", _run_mapping(run_id="baseline"))
    candidate = _write_json(tmp_path / "candidate.json", _run_mapping(run_id="candidate"))
    thresholds = _write_json(tmp_path / "thresholds.json", _thresholds())
    baseline_bytes = baseline.read_bytes()

    assert (
        run_compare_command(
            baseline_path=baseline,
            candidate_path=candidate,
            threshold_config_path=thresholds,
            report_path=baseline,
        )
        == COMPARE_INPUT_ERROR
    )
    assert baseline.read_bytes() == baseline_bytes

    target = tmp_path / "target.md"
    target.write_text("DO NOT TOUCH\n", encoding="utf-8")
    linked_report = tmp_path / "linked-report.md"
    linked_report.symlink_to(target)
    assert (
        run_compare_command(
            baseline_path=baseline,
            candidate_path=candidate,
            threshold_config_path=thresholds,
            report_path=linked_report,
        )
        == COMPARE_INPUT_ERROR
    )
    assert linked_report.is_symlink()
    assert target.read_text(encoding="utf-8") == "DO NOT TOUCH\n"


def test_cli_raw_artifact_paths_cannot_forge_markdown_structure(tmp_path: Path) -> None:
    injected = tmp_path / "baseline|forged`\n## FORGED PASS.json"
    baseline = _write_json(injected, _run_mapping(run_id="baseline"))
    candidate = _write_json(tmp_path / "candidate.json", _run_mapping(run_id="candidate"))
    thresholds = _write_json(tmp_path / "thresholds.json", _thresholds())
    report = tmp_path / "report.md"

    assert (
        run_compare_command(
            baseline_path=baseline,
            candidate_path=candidate,
            threshold_config_path=thresholds,
            report_path=report,
        )
        == 0
    )
    rendered = report.read_text(encoding="utf-8")
    assert "\n## FORGED PASS" not in rendered
    assert r"baseline&#124;forged&#96;\n## FORGED PASS.json" in rendered


@pytest.mark.parametrize(
    ("metric", "aggregate_fields"),
    [
        ("cost_per_case_delta", ("cost_usd", "cost_total_usd", "cost_per_case_usd")),
        ("latency_ms_p95_delta", ("latency_ms", "latency_ms_p50", "latency_ms_p95")),
    ],
)
def test_cli_exact_high_magnitude_delta_cannot_cancel_into_pass(
    tmp_path: Path,
    metric: str,
    aggregate_fields: tuple[str, str, str],
) -> None:
    baseline_raw = _run_mapping(run_id="baseline")
    candidate_raw = _run_mapping(run_id="candidate")
    case_field, aggregate_a, aggregate_b = aggregate_fields
    baseline_raw["case_results"][0][case_field] = 1_000_000_000_000.0
    candidate_raw["case_results"][0][case_field] = 1_000_000_000_000.1
    baseline_raw[aggregate_a] = 1_000_000_000_000.0
    baseline_raw[aggregate_b] = 1_000_000_000_000.0
    candidate_raw[aggregate_a] = 1_000_000_000_000.1
    candidate_raw[aggregate_b] = 1_000_000_000_000.1
    thresholds_raw = _thresholds()
    threshold_field = (
        "max_cost_per_case_delta_usd"
        if metric == "cost_per_case_delta"
        else "max_latency_p95_delta_ms"
    )
    thresholds_raw[threshold_field] = 0.09999
    baseline_path = _write_json(tmp_path / "baseline.json", baseline_raw)
    candidate_path = _write_json(tmp_path / "candidate.json", candidate_raw)
    thresholds_path = _write_json(tmp_path / "thresholds.json", thresholds_raw)
    baseline = read_run_artifact(baseline_path)
    candidate = read_run_artifact(candidate_path)
    thresholds = read_threshold_config(thresholds_path)

    comparison = compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)

    assert comparison.exact_deltas[metric] == "0.1"
    assert comparison.exact_thresholds[metric] == "0.09999"
    assert comparison.threshold_status[metric] == "fail"
    assert comparison.validator_receipt_regressions == ()
    assert {
        name: status for name, status in comparison.threshold_status.items() if name != metric
    } == {name: "pass" for name in comparison.threshold_status if name != metric}
    report = tmp_path / "report.md"
    assert (
        run_compare_command(
            baseline_path=baseline_path,
            candidate_path=candidate_path,
            threshold_config_path=thresholds_path,
            report_path=report,
        )
        == 1
    )
    assert f"| `{metric}` | `0.1` | `delta ≤ 0.09999` | `fail` |" in report.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("metric", "category", "expected_delta", "gate"),
    [
        ("accuracy_delta", None, "-1/3", "delta ≥ -0.3333333333333333"),
        (
            "invalid_output_rate",
            "invalid_structured_output",
            "1/3",
            "delta ≤ 0.3333333333333333",
        ),
        (
            "unsafe_auto_approval_rate",
            "unsafe_auto_approval",
            "1/3",
            "delta ≤ 0.3333333333333333",
        ),
    ],
)
def test_cli_exact_one_third_rate_boundary_cannot_round_into_pass(
    tmp_path: Path,
    metric: str,
    category: str | None,
    expected_delta: str,
    gate: str,
) -> None:
    baseline_raw = _three_case_mapping(run_id="baseline")
    candidate_raw = _three_case_mapping(run_id="candidate")
    thresholds_raw = _thresholds()
    if metric == "accuracy_delta":
        baseline_raw["case_results"][2]["output"]["correct"] = False
        candidate_raw["case_results"][1]["output"]["correct"] = False
        candidate_raw["case_results"][2]["output"]["correct"] = False
        thresholds_raw["max_accuracy_drop"] = 0.3333333333333333
    else:
        baseline_receipt = baseline_raw["case_results"][0]["validator_results"][0]
        baseline_receipt.update({"passed": False, "category": "baseline_known_failure"})
        receipt = candidate_raw["case_results"][0]["validator_results"][0]
        receipt.update({"passed": False, "category": category})
        thresholds_raw[
            "max_invalid_output_rate_increase"
            if metric == "invalid_output_rate"
            else "max_unsafe_auto_approval_rate_increase"
        ] = 0.3333333333333333
    baseline_path = _write_json(tmp_path / "baseline.json", baseline_raw)
    candidate_path = _write_json(tmp_path / "candidate.json", candidate_raw)
    thresholds_path = _write_json(tmp_path / "thresholds.json", thresholds_raw)
    comparison = compare_runs(
        baseline=read_run_artifact(baseline_path),
        candidate=read_run_artifact(candidate_path),
        thresholds=read_threshold_config(thresholds_path),
    )

    assert comparison.exact_deltas[metric] == expected_delta
    assert comparison.threshold_status[metric] == "fail"
    assert comparison.validator_receipt_regressions == ()
    assert {
        name: status for name, status in comparison.threshold_status.items() if name != metric
    } == {name: "pass" for name in comparison.threshold_status if name != metric}
    report = tmp_path / "report.md"
    assert (
        run_compare_command(
            baseline_path=baseline_path,
            candidate_path=candidate_path,
            threshold_config_path=thresholds_path,
            report_path=report,
        )
        == 1
    )
    assert f"| `{metric}` | `{expected_delta}` | `{gate}` | `fail` |" in report.read_text(
        encoding="utf-8"
    )


def _run_mapping(*, run_id: str = "run") -> dict:
    return {
        "candidate_version": f"{run_id}-candidate",
        "case_results": [
            {
                "case_id": "case-1",
                "cost_usd": 0.0,
                "latency_ms": 10.0,
                "output": {"correct": True},
                "validator_results": [
                    {
                        "case_id": "case-1",
                        "category": "none",
                        "evidence": {},
                        "message": "validator passed",
                        "passed": True,
                        "validator_id": "test.output_contract",
                    }
                ],
            }
        ],
        "completed_at": "2026-07-14T00:00:01+00:00",
        "cost_per_case_usd": 0.0,
        "cost_total_usd": 0.0,
        "dataset_hash": "sha256:test-dataset",
        "interrupted_at": None,
        "latency_ms_p50": 10.0,
        "latency_ms_p95": 10.0,
        "max_candidate_retries": 0,
        "run_id": run_id,
        "run_type": "test",
        "started_at": "2026-07-14T00:00:00+00:00",
        "status": "completed",
        "threshold_config_version": "policy-v1",
        "validator_version": "validator-v1",
    }


def _three_case_mapping(*, run_id: str) -> dict:
    raw = _run_mapping(run_id=run_id)
    first = raw["case_results"][0]
    for index in (2, 3):
        case = json.loads(json.dumps(first))
        case["case_id"] = f"case-{index}"
        case["validator_results"][0]["case_id"] = f"case-{index}"
        raw["case_results"].append(case)
    _recalculate_metrics(raw)
    return raw


def _thresholds() -> dict:
    return {
        "max_accuracy_drop": 0.0,
        "max_cost_per_case_delta_usd": 0.0,
        "max_invalid_output_rate_increase": 0.0,
        "max_latency_p95_delta_ms": 0.0,
        "max_unsafe_auto_approval_rate_increase": 0.0,
        "version": "policy-v1",
    }


def _recalculate_metrics(raw: dict) -> None:
    cases = raw["case_results"]
    costs = [case["cost_usd"] for case in cases]
    latencies = sorted(case["latency_ms"] for case in cases)
    raw["cost_total_usd"] = sum(costs)
    raw["cost_per_case_usd"] = sum(costs) / len(costs)
    raw["latency_ms_p50"] = latencies[(len(latencies) - 1) // 2]
    raw["latency_ms_p95"] = latencies[-1]


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
