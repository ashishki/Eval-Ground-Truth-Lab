from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

IMPLEMENTATION_COMMIT = "31120c809cc4935c9f5ffbb2cb539a3018d38d92"
IMPLEMENTATION_TREE = "8cbbff195bbae0ee5309d94c38ad27e8215c755e"
EXECUTION_BINDING = "423d9bc2bf89438b147485f88b4b251b6c872d62b00fea998c97904828da15b3"
POLICY_VERSION = "v0.2.1-exact-comparison-policy"
EXPECTED_VERSION = "0.2.1"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the immutable Eval Lab v0.2.1 fail-closed evidence pack."
    )
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    source_root = args.source_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    _require_clean_exact_source(source_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"output directory must be empty: {output_root}")

    source_package = source_root / "src"
    sys.path.insert(0, str(source_package))
    from eval_ground_truth_lab import __version__
    from eval_ground_truth_lab import cli as cli_module
    from eval_ground_truth_lab import evidence as evidence_module
    from eval_ground_truth_lab import execution_binding as execution_binding_module
    from eval_ground_truth_lab import implementation_provenance as provenance_module
    from eval_ground_truth_lab.compare import comparison as comparison_module
    from eval_ground_truth_lab.compare import contracts as contracts_module
    from eval_ground_truth_lab.reports import markdown as markdown_module
    from eval_ground_truth_lab.runs import store as run_store_module

    if __version__ != EXPECTED_VERSION:
        raise RuntimeError(f"expected Eval Lab {EXPECTED_VERSION}, loaded {__version__}")
    if execution_binding_module.EXECUTION_BINDING_SHA256 != EXECUTION_BINDING:
        raise RuntimeError("loaded execution binding does not match the reviewed implementation")

    implementation = provenance_module.build_implementation_provenance(
        component_paths={
            "cli": cli_module.__file__,
            "comparison": comparison_module.__file__,
            "comparison_contracts": contracts_module.__file__,
            "evidence_manifest": evidence_module.__file__,
            "execution_binding": execution_binding_module.__file__,
            "implementation_provenance": provenance_module.__file__,
            "markdown_renderer": markdown_module.__file__,
            "run_store": run_store_module.__file__,
        },
        package_root=source_root / "src/eval_ground_truth_lab",
        require_execution_binding=True,
    )
    expected_source = {
        "commit": IMPLEMENTATION_COMMIT,
        "kind": "git_worktree",
        "measured_package_matches_head": True,
        "tree": IMPLEMENTATION_TREE,
    }
    if implementation["source"] != expected_source:
        raise RuntimeError(f"implementation source mismatch: {implementation['source']!r}")
    expected_binding = {
        "schema_version": "eval-lab-loaded-execution-binding-v1",
        "sha256": EXECUTION_BINDING,
    }
    if implementation["execution_binding"] != expected_binding:
        raise RuntimeError("implementation provenance has an unexpected execution binding")

    output_root.mkdir(parents=True, exist_ok=True)
    inputs = output_root / "inputs"
    reports = output_root / "reports"
    receipts = output_root / "receipts"
    inputs.mkdir()
    reports.mkdir()
    receipts.mkdir()

    one_case_dataset = hashlib.sha256(b"eval-lab-v0.2.1-fail-closed-one-case-v1").hexdigest()
    three_case_dataset = hashlib.sha256(b"eval-lab-v0.2.1-fail-closed-three-case-v1").hexdigest()
    common_baseline = _run_mapping(
        run_id="fail-closed-common-baseline",
        dataset_hash=one_case_dataset,
        cases=[_case("case-1", correct=True, cost=0.0)],
    )
    generic_candidate = _run_mapping(
        run_id="generic-validator-regression-candidate",
        dataset_hash=one_case_dataset,
        cases=[
            _case(
                "case-1",
                correct=True,
                cost=0.0,
                passed=False,
                category="arbitrary_validator_regression",
                message="candidate validator changed from pass to fail",
            )
        ],
    )
    high_magnitude_baseline = _run_mapping(
        run_id="high-magnitude-decimal-baseline",
        dataset_hash=one_case_dataset,
        cases=[_case("case-1", correct=True, cost=1_000_000_000_000.0)],
    )
    high_magnitude_candidate = _run_mapping(
        run_id="high-magnitude-decimal-candidate",
        dataset_hash=one_case_dataset,
        cases=[_case("case-1", correct=True, cost=1_000_000_000_000.1)],
    )
    three_case_baseline = _run_mapping(
        run_id="one-third-boundary-baseline",
        dataset_hash=three_case_dataset,
        cases=[
            _case("case-1", correct=True, cost=0.0),
            _case("case-2", correct=True, cost=0.0),
            _case("case-3", correct=False, cost=0.0),
        ],
    )
    one_third_candidate = _run_mapping(
        run_id="one-third-boundary-candidate",
        dataset_hash=three_case_dataset,
        cases=[
            _case("case-1", correct=True, cost=0.0),
            _case("case-2", correct=False, cost=0.0),
            _case("case-3", correct=False, cost=0.0),
        ],
    )

    _write_json(evidence_module, inputs / "common-passing-baseline.json", common_baseline)
    _write_json(
        evidence_module,
        inputs / "generic-validator-regression-candidate.json",
        generic_candidate,
    )
    _write_json(
        evidence_module,
        inputs / "high-magnitude-decimal-baseline.json",
        high_magnitude_baseline,
    )
    _write_json(
        evidence_module,
        inputs / "high-magnitude-decimal-candidate.json",
        high_magnitude_candidate,
    )
    _write_json(
        evidence_module,
        inputs / "one-third-boundary-baseline.json",
        three_case_baseline,
    )
    _write_json(
        evidence_module,
        inputs / "one-third-boundary-candidate.json",
        one_third_candidate,
    )
    _write_json(evidence_module, inputs / "zero-thresholds.json", _thresholds())
    _write_json(
        evidence_module,
        inputs / "high-magnitude-decimal-thresholds.json",
        _thresholds(max_cost_per_case_delta_usd=0.09999),
    )
    _write_json(
        evidence_module,
        inputs / "one-third-boundary-thresholds.json",
        _thresholds(max_accuracy_drop=0.3333333333333333),
    )
    invalid_candidate = json.dumps(generic_candidate, indent=2, sort_keys=True) + "\n"
    duplicate_marker = '"validator_id": "evidence.output_contract"'
    if invalid_candidate.count(duplicate_marker) != 1:
        raise RuntimeError("nested duplicate-key fixture marker is not unique")
    evidence_module.atomic_write_text(
        inputs / "invalid-duplicate-key-candidate.json",
        invalid_candidate.replace(
            duplicate_marker,
            f"{duplicate_marker},\n          {duplicate_marker}",
        ),
    )
    stale_seed = b"STALE PASS MUST NOT SURVIVE INVALID INPUT\n"
    evidence_module.atomic_write_bytes(inputs / "stale-report-seed.md", stale_seed)

    scenarios = [
        _scenario(
            name="valid_no_regression",
            baseline="inputs/common-passing-baseline.json",
            candidate="inputs/common-passing-baseline.json",
            thresholds="inputs/zero-thresholds.json",
            report="reports/valid-no-regression.md",
            expected_exit=0,
        ),
        _scenario(
            name="generic_validator_pass_to_fail",
            baseline="inputs/common-passing-baseline.json",
            candidate="inputs/generic-validator-regression-candidate.json",
            thresholds="inputs/zero-thresholds.json",
            report="reports/generic-validator-regression.md",
            expected_exit=1,
        ),
        _scenario(
            name="high_magnitude_decimal_cancellation",
            baseline="inputs/high-magnitude-decimal-baseline.json",
            candidate="inputs/high-magnitude-decimal-candidate.json",
            thresholds="inputs/high-magnitude-decimal-thresholds.json",
            report="reports/high-magnitude-decimal-cancellation.md",
            expected_exit=1,
        ),
        _scenario(
            name="exact_one_third_boundary",
            baseline="inputs/one-third-boundary-baseline.json",
            candidate="inputs/one-third-boundary-candidate.json",
            thresholds="inputs/one-third-boundary-thresholds.json",
            report="reports/exact-one-third-boundary.md",
            expected_exit=1,
        ),
        _scenario(
            name="invalid_input_stale_report_invalidation",
            baseline="inputs/common-passing-baseline.json",
            candidate="inputs/invalid-duplicate-key-candidate.json",
            thresholds="inputs/zero-thresholds.json",
            report="reports/invalid-input-must-not-exist.md",
            expected_exit=2,
            stale_seed="inputs/stale-report-seed.md",
        ),
    ]

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source_package)
    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        result = _execute_scenario(
            source_root=source_root,
            pack_root=output_root,
            scenario=scenario,
            environment=environment,
            contracts_module=contracts_module,
            comparison_module=comparison_module,
        )
        results.append(result)

    by_name = {result["name"]: result for result in results}
    _require_nonblocking_decision(by_name["valid_no_regression"])
    _require_decision(
        by_name["generic_validator_pass_to_fail"],
        exact_delta=("cost_per_case_delta", "0"),
        failing_metric=None,
        regression_count=1,
    )
    _require_decision(
        by_name["high_magnitude_decimal_cancellation"],
        exact_delta=("cost_per_case_delta", "0.1"),
        failing_metric="cost_per_case_delta",
        regression_count=0,
    )
    _require_decision(
        by_name["exact_one_third_boundary"],
        exact_delta=("accuracy_delta", "-1/3"),
        failing_metric="accuracy_delta",
        regression_count=0,
    )
    invalid_result = by_name["invalid_input_stale_report_invalidation"]
    if invalid_result["report_exists_after"] or not invalid_result["stale_report_removed"]:
        raise RuntimeError("invalid input did not remove the stale report")
    if "duplicate key 'validator_id'" not in invalid_result["stderr"]:
        raise RuntimeError("invalid-input receipt did not retain the duplicate-key reason")

    receipt = {
        "implementation": implementation,
        "release": {
            "classification": "internal_correctness_and_security_patch",
            "external_feedback_maintenance_evidence": False,
            "version": EXPECTED_VERSION,
        },
        "runtime": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "scenarios": results,
        "schema_version": "eval-lab-v0.2.1-fail-closed-evidence-receipt-v1",
    }
    receipt_path = receipts / "command-results.json"
    evidence_module.atomic_write_json(receipt_path, receipt)
    evidence_module.atomic_write_text(output_root / "README.md", _readme())

    declared = sorted(
        path.relative_to(output_root) for path in output_root.rglob("*") if path.is_file()
    )
    manifest = evidence_module.write_evidence_manifest(
        output_root,
        declared,
        metadata={
            "claim_boundary": {
                "external_feedback_maintenance_evidence": False,
                "external_user_evidence": False,
                "production_evidence": False,
                "synthetic_local_execution": True,
            },
            "implementation": implementation,
            "release_classification": "internal_correctness_and_security_patch",
            "release_version": EXPECTED_VERSION,
            "scenario_exit_codes": {result["name"]: result["exit_code"] for result in results},
        },
    )
    verification = evidence_module.verify_evidence_manifest(manifest)
    print(json.dumps(verification.to_mapping(), sort_keys=True))
    return 0


def _require_clean_exact_source(source_root: Path) -> None:
    commit = _git(source_root, "rev-parse", "HEAD")
    tree = _git(source_root, "rev-parse", "HEAD^{tree}")
    status = _git(source_root, "status", "--porcelain", "--untracked-files=all")
    if commit != IMPLEMENTATION_COMMIT:
        raise RuntimeError(f"source commit must be {IMPLEMENTATION_COMMIT}; received {commit}")
    if tree != IMPLEMENTATION_TREE:
        raise RuntimeError(f"source tree must be {IMPLEMENTATION_TREE}; received {tree}")
    if status:
        raise RuntimeError("source worktree must be clean")


def _git(source_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=source_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _case(
    case_id: str,
    *,
    correct: bool,
    cost: float,
    passed: bool = True,
    category: str = "none",
    message: str = "validator passed",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "cost_usd": cost,
        "latency_ms": 10.0,
        "output": {"correct": correct},
        "validator_results": [
            {
                "case_id": case_id,
                "category": category,
                "evidence": {"fixture": "fully_synthetic"},
                "message": message,
                "passed": passed,
                "validator_id": "evidence.output_contract",
            }
        ],
    }


def _run_mapping(
    *,
    run_id: str,
    dataset_hash: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    costs = [case["cost_usd"] for case in cases]
    latencies = sorted(case["latency_ms"] for case in cases)
    total = sum(costs)
    return {
        "candidate_version": f"eval-lab-{EXPECTED_VERSION}-synthetic-{run_id}",
        "case_results": cases,
        "completed_at": "2026-07-14T00:00:01+00:00",
        "cost_per_case_usd": total / len(cases),
        "cost_total_usd": total,
        "dataset_hash": dataset_hash,
        "interrupted_at": None,
        "latency_ms_p50": latencies[(len(latencies) - 1) // 2],
        "latency_ms_p95": latencies[-1],
        "max_candidate_retries": 0,
        "run_id": run_id,
        "run_type": "comparison-evidence",
        "started_at": "2026-07-14T00:00:00+00:00",
        "status": "completed",
        "threshold_config_version": POLICY_VERSION,
        "validator_version": "fail-closed-evidence-validators-v1",
    }


def _thresholds(**overrides: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "max_accuracy_drop": 0.0,
        "max_cost_per_case_delta_usd": 0.0,
        "max_invalid_output_rate_increase": 0.0,
        "max_latency_p95_delta_ms": 0.0,
        "max_unsafe_auto_approval_rate_increase": 0.0,
        "version": POLICY_VERSION,
    }
    result.update(overrides)
    return result


def _write_json(evidence_module: Any, path: Path, value: dict[str, Any]) -> None:
    evidence_module.atomic_write_json(path, value)


def _scenario(
    *,
    name: str,
    baseline: str,
    candidate: str,
    thresholds: str,
    report: str,
    expected_exit: int,
    stale_seed: str | None = None,
) -> dict[str, Any]:
    return {
        "baseline": baseline,
        "candidate": candidate,
        "expected_exit": expected_exit,
        "name": name,
        "report": report,
        "stale_seed": stale_seed,
        "thresholds": thresholds,
    }


def _execute_scenario(
    *,
    source_root: Path,
    pack_root: Path,
    scenario: dict[str, Any],
    environment: dict[str, str],
    contracts_module: Any,
    comparison_module: Any,
) -> dict[str, Any]:
    report_path = pack_root / scenario["report"]
    stale_seed = scenario["stale_seed"]
    stale_seed_sha256: str | None = None
    if stale_seed is not None:
        stale_bytes = (pack_root / stale_seed).read_bytes()
        report_path.write_bytes(stale_bytes)
        stale_seed_sha256 = hashlib.sha256(stale_bytes).hexdigest()

    portable_command = [
        "python",
        "-m",
        "eval_ground_truth_lab.cli",
        "compare",
        "--baseline",
        scenario["baseline"],
        "--candidate",
        scenario["candidate"],
        "--threshold-config",
        scenario["thresholds"],
        "--report",
        scenario["report"],
    ]
    executed_command = [sys.executable, *portable_command[1:]]
    completed = subprocess.run(
        executed_command,
        cwd=pack_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != scenario["expected_exit"]:
        raise RuntimeError(
            f"{scenario['name']} exited {completed.returncode}; "
            f"expected {scenario['expected_exit']}: {completed.stderr}"
        )

    decision: dict[str, Any] | None = None
    if completed.returncode in {0, 1}:
        baseline = contracts_module.read_run_artifact(pack_root / scenario["baseline"])
        candidate = contracts_module.read_run_artifact(pack_root / scenario["candidate"])
        thresholds = contracts_module.read_threshold_config(pack_root / scenario["thresholds"])
        comparison = comparison_module.compare_runs(
            baseline=baseline,
            candidate=candidate,
            thresholds=thresholds,
        )
        decision = {
            "blocking": comparison.has_blocking_failure,
            "exact_deltas": comparison.exact_deltas,
            "exact_thresholds": comparison.exact_thresholds,
            "threshold_status": comparison.threshold_status,
            "validator_receipt_regressions": [
                {
                    "candidate_category": regression.candidate_category,
                    "case_id": regression.case_id,
                    "validator_id": regression.validator_id,
                }
                for regression in comparison.validator_receipt_regressions
            ],
        }

    report_exists = report_path.is_file()
    return {
        "command": portable_command,
        "decision": decision,
        "exit_code": completed.returncode,
        "expected_exit_code": scenario["expected_exit"],
        "name": scenario["name"],
        "report_exists_after": report_exists,
        "report_sha256": (
            hashlib.sha256(report_path.read_bytes()).hexdigest() if report_exists else None
        ),
        "stale_report_removed": stale_seed is not None and not report_path.exists(),
        "stale_report_seed_sha256": stale_seed_sha256,
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
        "source_commit": IMPLEMENTATION_COMMIT,
        "source_tree": IMPLEMENTATION_TREE,
    }


def _require_decision(
    result: dict[str, Any],
    *,
    exact_delta: tuple[str, str],
    failing_metric: str | None,
    regression_count: int,
) -> None:
    decision = result["decision"]
    if not isinstance(decision, dict) or decision["blocking"] is not True:
        raise RuntimeError(f"{result['name']} did not produce a blocking decision")
    metric, expected_delta = exact_delta
    if decision["exact_deltas"][metric] != expected_delta:
        raise RuntimeError(f"{result['name']} exact delta does not match")
    regressions = decision["validator_receipt_regressions"]
    if len(regressions) != regression_count:
        raise RuntimeError(f"{result['name']} validator regression count does not match")
    failing = {name for name, status in decision["threshold_status"].items() if status == "fail"}
    expected_failing = set() if failing_metric is None else {failing_metric}
    if failing != expected_failing:
        raise RuntimeError(f"{result['name']} threshold failures do not match")


def _require_nonblocking_decision(result: dict[str, Any]) -> None:
    decision = result["decision"]
    if not isinstance(decision, dict) or decision["blocking"] is not False:
        raise RuntimeError(f"{result['name']} did not produce a non-blocking decision")
    if set(decision["exact_deltas"].values()) != {"0"}:
        raise RuntimeError(f"{result['name']} did not retain exact zero deltas")
    if set(decision["threshold_status"].values()) != {"pass"}:
        raise RuntimeError(f"{result['name']} did not pass all metric thresholds")
    if decision["validator_receipt_regressions"]:
        raise RuntimeError(f"{result['name']} unexpectedly recorded a validator regression")


def _readme() -> str:
    return f"""# Eval Lab v0.2.1 fail-closed comparison evidence

This content-addressed pack records five synthetic, local executions of the
shared comparison contract from implementation commit `{IMPLEMENTATION_COMMIT}`
and tree `{IMPLEMENTATION_TREE}`. The loaded execution binding is
`{EXECUTION_BINDING}`.

The scenarios demonstrate the complete comparison CLI exit contract:

1. a valid no-regression comparison passes every metric and exits `0`;
2. an arbitrary-category validator receipt changing from pass to fail blocks
   even when all five metric thresholds pass;
3. an exact `0.1` high-magnitude cost delta blocks against `0.09999` instead of
   cancelling through binary-float subtraction;
4. an exact `-1/3` accuracy delta blocks against the finite decimal threshold
   `0.3333333333333333`;
5. recursively invalid JSON exits `2` and removes a pre-existing stale report.

The three valid regressions exit `1`, so the pack covers statuses `0`, `1`, and
`2` without treating invalid input as an ordinary policy decision.

`receipts/command-results.json` records normalized commands, exit codes, exact
decisions, report hashes, stale-target invalidation, package provenance, and the
execution binding. The reports link only pack-relative raw inputs. Verify the
pack with `eval-ground-truth-lab verify-evidence --manifest sha256-*.manifest.json`.

## Reproduce

From the evidence commit that contains the generator, create a clean detached
worktree for the recorded implementation and choose a new empty output path:

```bash
SOURCE=/tmp/eval-lab-v021-source
OUTPUT=/tmp/eval-lab-v021-evidence
git worktree add --detach "$SOURCE" {IMPLEMENTATION_COMMIT}
test ! -e "$OUTPUT"
python3 tools/generate_v021_release_evidence.py --source-root "$SOURCE" --output-root "$OUTPUT"
diff -qr docs/evidence/releases/v0.2.1 "$OUTPUT"
```

On the receipt's recorded Python/platform runtime, generation is byte-stable:
`diff -qr` is silent and exits `0`, including the manifest filename and content
address. A different runtime or platform is recorded explicitly and therefore
can produce a different receipt and content address.

## Claim boundary

v0.2.1 is an internal correctness and security patch. This pack is not evidence
of external-feedback-driven maintenance, external users, adoption, design
partners, production execution, or production quality. All run inputs are
self-authored synthetic fixtures executed locally; no financial or business
outcome is evaluated.
"""


if __name__ == "__main__":
    raise SystemExit(main())
