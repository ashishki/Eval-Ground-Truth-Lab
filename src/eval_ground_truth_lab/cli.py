from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_ground_truth_lab import __version__
from eval_ground_truth_lab import challenge as challenge_module
from eval_ground_truth_lab.adapters import (
    GdevAgentConfig,
    GdevAgentHttpAdapter,
    GdevRequestNamespace,
)
from eval_ground_truth_lab.adapters import gdev_agent as gdev_adapter_module
from eval_ground_truth_lab.challenge import (
    CandidateAdapter,
    ChallengeThresholds,
    FaultInjectingAdapter,
    build_challenge_result,
    render_challenge_markdown,
)
from eval_ground_truth_lab.compare import ComparisonReport, ThresholdConfig, compare_runs
from eval_ground_truth_lab.cost import check_budget, load_budget_policy, rollup_telemetry
from eval_ground_truth_lab.datasets import Dataset, load_dataset
from eval_ground_truth_lab.evidence import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    sha256_file,
    verify_evidence_manifest,
    write_evidence_manifest,
)
from eval_ground_truth_lab.reports import render_markdown_report
from eval_ground_truth_lab.runs import CaseResult, RunRecord, RunStore
from eval_ground_truth_lab.trader_replay import run_trader_risk_audit_replay
from eval_ground_truth_lab.validators import GdevValidatorThresholds, validate_gdev_case
from eval_ground_truth_lab.validators import gdev_agent as gdev_validator_module


def comparison_exit_code(report: ComparisonReport) -> int:
    return 1 if report.has_blocking_failure else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval-ground-truth-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    smoke_parser = subparsers.add_parser("seeded-smoke")
    smoke_parser.add_argument("--dataset", required=True)
    smoke_parser.add_argument("--report", required=True)
    smoke_parser.add_argument(
        "--threshold-config",
        default="datasets/smoke/thresholds.json",
    )

    inspect_parser = subparsers.add_parser("dataset-inspect")
    inspect_parser.add_argument("--dataset", required=True)

    gdev_parser = subparsers.add_parser("run-gdev-agent")
    gdev_parser.add_argument("--dataset", required=True)
    gdev_parser.add_argument("--base-url", required=True)
    gdev_parser.add_argument("--run-id")
    gdev_parser.add_argument("--run-dir", default="runs")
    gdev_parser.add_argument("--candidate-version", default="gdev-agent-demo")
    gdev_parser.add_argument("--component-revision", required=True)
    gdev_parser.add_argument("--report", required=True)
    gdev_parser.add_argument(
        "--threshold-config",
        default="datasets/gdev_agent/thresholds.json",
    )

    challenge_parser = subparsers.add_parser("run-gdev-agent-challenge")
    challenge_parser.add_argument(
        "--dataset",
        default="datasets/gdev_agent/challenge_v1.jsonl",
    )
    challenge_parser.add_argument("--base-url", required=True)
    challenge_parser.add_argument("--run-id")
    challenge_parser.add_argument("--run-dir", default="runs")
    challenge_parser.add_argument("--candidate-version", required=True)
    challenge_parser.add_argument("--component-revision", required=True)
    challenge_parser.add_argument(
        "--component-worktree-state",
        choices=("clean", "dirty", "fixture"),
        required=True,
    )
    challenge_parser.add_argument("--component-image-digest")
    challenge_parser.add_argument("--environment-label", required=True)
    challenge_parser.add_argument("--evidence-dir", required=True)
    challenge_parser.add_argument(
        "--threshold-config",
        default="datasets/gdev_agent/challenge_thresholds.json",
    )

    trader_parser = subparsers.add_parser("run-trader-risk-audit-replay")
    trader_parser.add_argument(
        "--dataset",
        default="datasets/trader_risk_audit/synthetic_quickstart_v1.jsonl",
    )
    trader_parser.add_argument(
        "--evidence",
        default=("datasets/trader_risk_audit/fixtures/synthetic_quickstart_v1/eval-evidence.json"),
    )
    trader_parser.add_argument(
        "--provenance",
        default="datasets/trader_risk_audit/synthetic_quickstart_v1.provenance.json",
    )
    trader_parser.add_argument("--evidence-dir", required=True)
    trader_parser.add_argument("--run-dir", required=True)
    trader_parser.add_argument("--run-id")

    verify_parser = subparsers.add_parser("verify-evidence")
    verify_parser.add_argument("--manifest", required=True)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)
    compare_parser.add_argument("--threshold-config", required=True)
    compare_parser.add_argument("--report", required=True)

    cost_rollup_parser = subparsers.add_parser("cost-rollup")
    cost_rollup_parser.add_argument("--telemetry", required=True)
    cost_rollup_parser.add_argument("--out", required=True)

    budget_check_parser = subparsers.add_parser("budget-check")
    budget_check_parser.add_argument("--rollup", required=True)
    budget_check_parser.add_argument("--policy", required=True)

    args = parser.parse_args(argv)
    if args.command == "seeded-smoke":
        return run_seeded_smoke_eval(
            dataset_path=args.dataset,
            report_path=args.report,
            threshold_config_path=args.threshold_config,
        )
    if args.command == "dataset-inspect":
        print(json.dumps(inspect_dataset(args.dataset), sort_keys=True))
        return 0
    if args.command == "run-gdev-agent":
        return run_gdev_agent_eval(
            dataset_path=args.dataset,
            base_url=args.base_url,
            report_path=args.report,
            run_id=args.run_id,
            run_dir=args.run_dir,
            candidate_version=args.candidate_version,
            component_revision=args.component_revision,
            threshold_config_path=args.threshold_config,
        )
    if args.command == "run-gdev-agent-challenge":
        return run_gdev_agent_challenge(
            dataset_path=args.dataset,
            base_url=args.base_url,
            evidence_dir=args.evidence_dir,
            component_revision=args.component_revision,
            component_worktree_state=args.component_worktree_state,
            environment_label=args.environment_label,
            candidate_version=args.candidate_version,
            component_image_digest=args.component_image_digest,
            run_id=args.run_id,
            run_dir=args.run_dir,
            threshold_config_path=args.threshold_config,
        )
    if args.command == "run-trader-risk-audit-replay":
        return run_trader_risk_audit_replay(
            dataset_path=args.dataset,
            evidence_path=args.evidence,
            provenance_path=args.provenance,
            evidence_dir=args.evidence_dir,
            run_dir=args.run_dir,
            run_id=args.run_id,
        )
    if args.command == "verify-evidence":
        result = verify_evidence_manifest(args.manifest)
        print(json.dumps(result.to_mapping(), sort_keys=True))
        return 0
    if args.command == "compare":
        return run_compare_command(
            baseline_path=args.baseline,
            candidate_path=args.candidate,
            threshold_config_path=args.threshold_config,
            report_path=args.report,
        )
    if args.command == "cost-rollup":
        return run_cost_rollup_command(telemetry_path=args.telemetry, out_path=args.out)
    if args.command == "budget-check":
        return run_budget_check_command(rollup_path=args.rollup, policy_path=args.policy)
    raise ValueError(f"Unsupported command {args.command}")


def inspect_dataset(dataset_path: str | Path) -> dict[str, int | str]:
    dataset = load_dataset(dataset_path)
    return {
        "case_count": dataset.metadata.case_count,
        "dataset_hash": dataset.metadata.dataset_hash,
        "dataset_id": dataset.metadata.dataset_id,
        "schema_version": dataset.metadata.schema_version,
    }


def run_seeded_smoke_eval(
    *,
    dataset_path: str | Path,
    report_path: str | Path,
    threshold_config_path: str | Path = "datasets/smoke/thresholds.json",
) -> int:
    dataset = load_dataset(dataset_path)
    threshold_config = _load_threshold_config(Path(threshold_config_path))
    baseline, candidate = _build_seeded_runs(dataset)
    comparison = compare_runs(
        baseline=baseline,
        candidate=candidate,
        thresholds=threshold_config,
    )

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path = report_path.with_name(f"{report_path.stem}-baseline-run.json")
    candidate_path = report_path.with_name(f"{report_path.stem}-candidate-run.json")
    _write_run_artifact(baseline_path, baseline)
    _write_run_artifact(candidate_path, candidate)

    report = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "dataset hash": dataset.metadata.dataset_hash,
            "baseline run": str(baseline_path),
            "candidate run": str(candidate_path),
            "threshold config": str(threshold_config_path),
            "failure taxonomy evidence": "src/eval_ground_truth_lab/reports/taxonomy.py",
        },
    )
    report_path.write_text(report, encoding="utf-8")
    return comparison_exit_code(comparison)


def run_gdev_agent_eval(
    *,
    dataset_path: str | Path,
    base_url: str,
    report_path: str | Path,
    run_id: str | None = None,
    run_dir: str | Path = "runs",
    candidate_version: str = "gdev-agent-demo",
    component_revision: str,
    threshold_config_path: str | Path = "datasets/gdev_agent/thresholds.json",
    adapter: CandidateAdapter | None = None,
) -> int:
    _validate_component_revision(component_revision)
    dataset = load_dataset(dataset_path)
    validator_thresholds = _load_gdev_validator_thresholds(Path(threshold_config_path))
    delegate = adapter or _build_gdev_adapter(base_url)
    store = RunStore(run_dir)
    run = store.create_run(
        run_id=run_id,
        run_type="candidate",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version=candidate_version,
        validator_version="gdev-validators-v1",
        threshold_config_version=_threshold_config_version(Path(threshold_config_path)),
    )
    request_namespace = GdevRequestNamespace(
        run_id=run.run_id,
        candidate_version=candidate_version,
        component_revision=component_revision,
        dataset_hash=dataset.metadata.dataset_hash,
    )
    selected_adapter, adapter_mode = _bind_request_namespace(delegate, request_namespace)
    request_namespace_evidence = _request_namespace_evidence(
        request_namespace,
        adapter_mode=adapter_mode,
    )

    has_failure = False
    for case in dataset.cases:
        adapter_result = selected_adapter.invoke(case.to_canonical_mapping())
        actual = _mapping_or_empty(adapter_result.output)
        expected = _mapping_or_empty(case.expected)
        validator_results = validate_gdev_case(
            case_id=case.id,
            expected=expected,
            actual=actual,
            thresholds=validator_thresholds,
        )
        has_failure = has_failure or any(not result.passed for result in validator_results)
        output = dict(actual)
        output["correct"] = _derived_gdev_correctness(validator_results)
        store.add_case_result(
            run.run_id,
            CaseResult(
                case_id=case.id,
                output=output,
                validator_results=tuple(asdict(result) for result in validator_results),
                cost_usd=float(actual.get("cost_usd") or 0.0),
                latency_ms=float(actual.get("latency_ms") or adapter_result.latency_ms),
            ),
        )

    completed = store.complete_run(run.run_id)
    _write_gdev_run_report(
        report_path=Path(report_path),
        run=completed,
        dataset=dataset,
        threshold_config_path=Path(threshold_config_path),
        run_artifact_path=Path(run_dir) / f"{completed.run_id}.json",
        request_namespace=request_namespace_evidence,
    )
    return 1 if has_failure else 0


def run_gdev_agent_challenge(
    *,
    dataset_path: str | Path,
    base_url: str,
    evidence_dir: str | Path,
    component_revision: str,
    component_worktree_state: str,
    environment_label: str,
    candidate_version: str,
    component_image_digest: str | None = None,
    run_id: str | None = None,
    run_dir: str | Path = "runs",
    threshold_config_path: str | Path = "datasets/gdev_agent/challenge_thresholds.json",
    adapter: CandidateAdapter | None = None,
) -> int:
    is_fixture = _validate_challenge_provenance(
        component_revision=component_revision,
        component_worktree_state=component_worktree_state,
        component_image_digest=component_image_digest,
        environment_label=environment_label,
        candidate_version=candidate_version,
    )
    pack_root = Path(evidence_dir)
    if pack_root.exists() and any(pack_root.iterdir()):
        raise ValueError(f"Evidence directory must be empty: {pack_root}")
    pack_root.mkdir(parents=True, exist_ok=True)

    dataset_source = Path(dataset_path)
    threshold_source = Path(threshold_config_path)
    dataset = load_dataset(dataset_source)
    thresholds = _load_challenge_thresholds(threshold_source)
    validator_thresholds = _load_gdev_validator_thresholds(threshold_source)
    delegate = adapter or _build_gdev_adapter(base_url)
    store = RunStore(run_dir)
    run = store.create_run(
        run_id=run_id,
        run_type="gdev_agent_challenge",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version=candidate_version,
        validator_version="gdev-challenge-validators-v1",
        threshold_config_version=thresholds.version,
    )
    request_namespace = GdevRequestNamespace(
        run_id=run.run_id,
        candidate_version=candidate_version,
        component_revision=component_revision,
        dataset_hash=dataset.metadata.dataset_hash,
    )
    namespaced_delegate, adapter_mode = _bind_request_namespace(delegate, request_namespace)
    request_namespace_evidence = _request_namespace_evidence(
        request_namespace,
        adapter_mode=adapter_mode,
    )
    selected_adapter = FaultInjectingAdapter(
        namespaced_delegate,
        fault_cost_usd=thresholds.max_cost_per_case_usd + 1.0,
        fault_latency_ms=thresholds.max_latency_p95_ms + 1_000.0,
    )

    try:
        for case in dataset.cases:
            adapter_result = selected_adapter.invoke(case.to_canonical_mapping())
            actual = _mapping_or_empty(adapter_result.output)
            expected = _mapping_or_empty(case.expected)
            validator_results = validate_gdev_case(
                case_id=case.id,
                expected=expected,
                actual=actual,
                thresholds=validator_thresholds,
            )
            output = dict(actual)
            output["correct"] = _derived_gdev_correctness(validator_results)
            store.add_case_result(
                run.run_id,
                CaseResult(
                    case_id=case.id,
                    output=output,
                    validator_results=tuple(asdict(result) for result in validator_results),
                    cost_usd=float(actual.get("cost_usd") or 0.0),
                    latency_ms=float(actual.get("latency_ms") or adapter_result.latency_ms),
                ),
            )
    except BaseException:
        store.interrupt_run(run.run_id)
        raise

    completed = store.complete_run(run.run_id)
    implementation_sha256 = {
        "challenge": sha256_file(Path(challenge_module.__file__)),
        "cli": sha256_file(Path(__file__)),
        "gdev_adapter": sha256_file(Path(gdev_adapter_module.__file__)),
        "gdev_validators": sha256_file(Path(gdev_validator_module.__file__)),
    }
    runtime_environment = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pyyaml": importlib.metadata.version("PyYAML"),
    }
    result = build_challenge_result(
        dataset=dataset,
        run=completed,
        thresholds=thresholds,
        provenance={
            "component_image_digest": component_image_digest,
            "component_revision": component_revision,
            "component_worktree_state": component_worktree_state,
            "environment_label": environment_label,
            "execution_mode": "candidate_http_plus_deterministic_provider_faults",
            "fixture": is_fixture,
            "harness_version": f"eval-ground-truth-lab-{__version__}",
            "implementation_sha256": implementation_sha256,
            "request_namespace": request_namespace_evidence,
            "runtime": runtime_environment,
        },
        dataset_raw_sha256=sha256_file(dataset_source),
        threshold_config_sha256=sha256_file(threshold_source),
    )

    result_path = pack_root / "challenge-run.json"
    report_path = pack_root / "challenge-report.md"
    run_artifact_dir = pack_root / "run"
    run_artifact_dir.mkdir()
    run_source = Path(run_dir) / f"{completed.run_id}.json"
    seal_source = Path(run_dir) / f"{completed.run_id}.sha256"
    run_artifact_path = run_artifact_dir / run_source.name
    seal_artifact_path = run_artifact_dir / seal_source.name
    atomic_write_json(result_path, result)
    atomic_write_text(report_path, render_challenge_markdown(result))
    atomic_write_bytes(run_artifact_path, run_source.read_bytes())
    atomic_write_bytes(seal_artifact_path, seal_source.read_bytes())
    declared = [
        result_path.relative_to(pack_root),
        report_path.relative_to(pack_root),
        run_artifact_path.relative_to(pack_root),
        seal_artifact_path.relative_to(pack_root),
    ]
    manifest_path = write_evidence_manifest(
        pack_root,
        declared,
        metadata={
            "candidate_version": candidate_version,
            "component_image_digest": component_image_digest,
            "component_revision": component_revision,
            "component_worktree_state": component_worktree_state,
            "dataset_hash": dataset.metadata.dataset_hash,
            "dataset_raw_sha256": sha256_file(dataset_source),
            "environment_label": environment_label,
            "fixture": is_fixture,
            "gate_passed": result["gate"]["passed"],
            "implementation_sha256": implementation_sha256,
            "request_namespace": request_namespace_evidence,
            "run_id": completed.run_id,
            "runtime": runtime_environment,
            "threshold_config_sha256": sha256_file(threshold_source),
        },
    )
    verification = verify_evidence_manifest(manifest_path)
    print(
        json.dumps(
            {
                "content_address": verification.content_address,
                "gate_passed": result["gate"]["passed"],
                "manifest": str(manifest_path),
                "request_namespace": request_namespace.identifier,
                "run_id": completed.run_id,
            },
            sort_keys=True,
        )
    )
    return 0 if result["gate"]["passed"] else 1


def run_compare_command(
    *,
    baseline_path: str | Path,
    candidate_path: str | Path,
    threshold_config_path: str | Path,
    report_path: str | Path,
) -> int:
    baseline = _read_run_artifact(Path(baseline_path))
    candidate = _read_run_artifact(Path(candidate_path))
    thresholds = _load_threshold_config(Path(threshold_config_path))
    comparison = compare_runs(baseline=baseline, candidate=candidate, thresholds=thresholds)

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = render_markdown_report(
        baseline=baseline,
        candidate=candidate,
        comparison=comparison,
        raw_artifact_links={
            "baseline run": str(baseline_path),
            "candidate run": str(candidate_path),
            "threshold config": str(threshold_config_path),
        },
    )
    report_path.write_text(report, encoding="utf-8")
    return comparison_exit_code(comparison)


def run_cost_rollup_command(*, telemetry_path: str | Path, out_path: str | Path) -> int:
    rollup = rollup_telemetry(telemetry_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rollup, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def run_budget_check_command(*, rollup_path: str | Path, policy_path: str | Path) -> int:
    with Path(rollup_path).open(encoding="utf-8") as rollup_file:
        rollup = json.load(rollup_file)
    if not isinstance(rollup, dict):
        raise ValueError("Rollup must be a JSON object")
    result = check_budget(rollup, load_budget_policy(policy_path))
    print(json.dumps(result.to_mapping(), sort_keys=True))
    return 0 if result.passed else 1


def _build_seeded_runs(dataset: Dataset) -> tuple[RunRecord, RunRecord]:
    baseline_results: list[CaseResult] = []
    candidate_results: list[CaseResult] = []
    for case in dataset.cases:
        baseline_results.append(
            CaseResult(
                case_id=case.id,
                output={"correct": True},
                cost_usd=0.01,
                latency_ms=100.0,
            )
        )
        candidate_results.append(_candidate_case_result(case.id, case.metadata))

    started_at = "2026-06-11T00:00:00+00:00"
    completed_at = "2026-06-11T00:01:00+00:00"
    baseline = _run_record(
        run_id="seeded-smoke-baseline",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version="synthetic-baseline-v1",
        started_at=started_at,
        completed_at=completed_at,
        case_results=tuple(baseline_results),
    )
    candidate = _run_record(
        run_id="seeded-smoke-unsafe-regression",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version="synthetic-seeded-regression-v1",
        started_at=started_at,
        completed_at=completed_at,
        case_results=tuple(candidate_results),
    )
    return baseline, candidate


def _candidate_case_result(case_id: str, metadata: dict[str, Any]) -> CaseResult:
    regression_class = metadata.get("blocking_regression_class")
    if regression_class == "unsafe_auto_approval":
        return CaseResult(
            case_id=case_id,
            output={"correct": True, "action": "approve"},
            validator_results=(
                {
                    "validator_id": "safety.unsafe_auto_approval",
                    "passed": False,
                    "category": "unsafe_auto_approval",
                    "message": "approved high-risk action without evidence",
                },
            ),
            cost_usd=0.01,
            latency_ms=100.0,
        )
    if regression_class == "invalid_structured_output":
        return CaseResult(
            case_id=case_id,
            output={"correct": True, "rationale": "missing action"},
            validator_results=(
                {
                    "validator_id": "structured_output.required_fields",
                    "passed": False,
                    "category": "invalid_structured_output",
                    "message": "missing required field action",
                },
            ),
            cost_usd=0.01,
            latency_ms=100.0,
        )
    if regression_class == "excessive_cost_increase":
        return CaseResult(
            case_id=case_id,
            output={"correct": True},
            cost_usd=0.10,
            latency_ms=100.0,
        )
    if regression_class == "material_accuracy_drop":
        return CaseResult(
            case_id=case_id,
            output={"correct": False, "category": "billing"},
            cost_usd=0.01,
            latency_ms=100.0,
        )
    return CaseResult(
        case_id=case_id,
        output={"correct": True},
        cost_usd=0.01,
        latency_ms=100.0,
    )


def _run_record(
    *,
    run_id: str,
    dataset_hash: str,
    candidate_version: str,
    started_at: str,
    completed_at: str,
    case_results: tuple[CaseResult, ...],
) -> RunRecord:
    case_count = len(case_results)
    total_cost = sum(case.cost_usd for case in case_results)
    latencies = sorted(case.latency_ms for case in case_results)
    latency_p95 = latencies[-1] if latencies else 0.0
    return RunRecord(
        run_id=run_id,
        run_type="seeded_smoke",
        dataset_hash=dataset_hash,
        candidate_version=candidate_version,
        validator_version="validators-v1",
        threshold_config_version="smoke-v1",
        status="completed",
        started_at=started_at,
        completed_at=completed_at,
        cost_total_usd=total_cost,
        cost_per_case_usd=total_cost / case_count if case_count else 0.0,
        latency_ms_p50=latencies[case_count // 2] if case_count else 0.0,
        latency_ms_p95=latency_p95,
        case_results=case_results,
    )


def _load_threshold_config(path: Path) -> ThresholdConfig:
    with path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    if "max_accuracy_drop" not in raw:
        return _load_gdev_comparison_threshold_config(raw)
    return ThresholdConfig(
        max_accuracy_drop=float(raw["max_accuracy_drop"]),
        max_invalid_output_rate_increase=float(raw["max_invalid_output_rate_increase"]),
        max_unsafe_auto_approval_rate_increase=float(raw["max_unsafe_auto_approval_rate_increase"]),
        max_latency_p95_delta_ms=float(raw["max_latency_p95_delta_ms"]),
        max_cost_per_case_delta_usd=float(raw["max_cost_per_case_delta_usd"]),
    )


def _load_gdev_comparison_threshold_config(raw: Mapping[str, Any]) -> ThresholdConfig:
    accuracy_min = float(raw.get("classification_accuracy_min", 1.0))
    return ThresholdConfig(
        max_accuracy_drop=max(0.0, 1.0 - accuracy_min),
        max_invalid_output_rate_increase=float(raw.get("max_invalid_structured_output_rate", 0.0)),
        max_unsafe_auto_approval_rate_increase=float(raw.get("max_unsafe_auto_approval_rate", 0.0)),
        max_latency_p95_delta_ms=float(raw.get("max_latency_p95_ms", 0.0)),
        max_cost_per_case_delta_usd=float(raw.get("max_cost_per_case_usd", 0.0)),
    )


def _load_gdev_validator_thresholds(path: Path) -> GdevValidatorThresholds:
    with path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    return GdevValidatorThresholds(
        confidence_floor=float(raw.get("confidence_floor", 0.0)),
        cost_ceiling_usd=_optional_float(raw.get("max_cost_per_case_usd")),
        latency_ceiling_ms=_optional_float(raw.get("max_latency_p95_ms")),
    )


def _load_challenge_thresholds(path: Path) -> ChallengeThresholds:
    with path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    if not isinstance(raw, Mapping):
        raise ValueError("Challenge threshold config must be a JSON object")
    return ChallengeThresholds.from_mapping(raw)


def _write_run_artifact(path: Path, record: RunRecord) -> None:
    path.write_text(
        json.dumps(record.to_mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_gdev_run_report(
    *,
    report_path: Path,
    run: RunRecord,
    dataset: Dataset,
    threshold_config_path: Path,
    run_artifact_path: Path,
    request_namespace: Mapping[str, Any],
) -> None:
    comparison = ComparisonReport(
        baseline_run_id=run.run_id,
        candidate_run_id=run.run_id,
        dataset_hash=dataset.metadata.dataset_hash,
        accuracy_delta=0.0,
        invalid_output_rate_delta=0.0,
        unsafe_auto_approval_rate_delta=0.0,
        latency_ms_p95_delta=0.0,
        cost_per_case_delta=0.0,
        threshold_status={
            "accuracy_delta": "pass",
            "invalid_output_rate": "pass",
            "unsafe_auto_approval_rate": "pass",
            "latency_ms_p95_delta": "pass",
            "cost_per_case_delta": "pass",
        },
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = render_markdown_report(
        baseline=run,
        candidate=run,
        comparison=comparison,
        raw_artifact_links={
            "dataset hash": dataset.metadata.dataset_hash,
            "run artifact": str(run_artifact_path),
            "threshold config": str(threshold_config_path),
            "failure taxonomy": "docs/FAILURE_TAXONOMY.md",
            "component revision": str(request_namespace["context"]["component_revision"]),
            "request namespace": str(request_namespace["identifier"]),
            "request namespace applied": str(request_namespace["applied"]),
            "request namespace adapter mode": str(request_namespace["adapter_mode"]),
        },
    )
    report_path.write_text(report, encoding="utf-8")


def _build_gdev_adapter(base_url: str) -> GdevAgentHttpAdapter:
    return GdevAgentHttpAdapter(GdevAgentConfig.from_environment(base_url=base_url))


def _bind_request_namespace(
    adapter: CandidateAdapter,
    request_namespace: GdevRequestNamespace,
) -> tuple[CandidateAdapter, str]:
    if isinstance(adapter, GdevAgentHttpAdapter):
        return adapter.with_request_namespace(request_namespace), "gdev_http_namespaced"
    return adapter, "custom_adapter_passthrough"


def _request_namespace_evidence(
    request_namespace: GdevRequestNamespace,
    *,
    adapter_mode: str,
) -> dict[str, Any]:
    applied = adapter_mode == "gdev_http_namespaced"
    return {
        **request_namespace.to_mapping(),
        "adapter_mode": adapter_mode,
        "applied": applied,
        "applied_fields": ["message_id", "request_id"] if applied else [],
    }


def _read_run_artifact(path: Path) -> RunRecord:
    with path.open(encoding="utf-8") as run_file:
        return RunRecord.from_mapping(json.load(run_file))


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _derived_gdev_correctness(validator_results: tuple[Any, ...]) -> bool:
    threshold_validators = {
        "gdev.confidence_floor",
        "gdev.cost_ceiling",
        "gdev.latency_ceiling",
    }
    return all(
        result.passed
        for result in validator_results
        if result.validator_id not in threshold_validators
    )


def _threshold_config_version(path: Path) -> str:
    if not path.exists():
        return path.stem
    with path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    return str(raw.get("version") or path.stem)


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    return float(value)


def _validate_challenge_provenance(
    *,
    component_revision: str,
    component_worktree_state: str,
    component_image_digest: str | None,
    environment_label: str,
    candidate_version: str,
) -> bool:
    for field, value in (
        ("candidate_version", candidate_version),
        ("component_revision", component_revision),
        ("environment_label", environment_label),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
    is_fixture = component_revision.startswith("fixture:")
    if is_fixture:
        if "fixture" not in environment_label.lower():
            raise ValueError("Fixture revisions require an environment label containing 'fixture'")
        if component_worktree_state != "fixture":
            raise ValueError("Fixture revisions require component_worktree_state='fixture'")
    elif not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", component_revision):
        raise ValueError(
            "component_revision must be a full 40- or 64-character git commit SHA "
            "or start with 'fixture:'"
        )
    elif component_worktree_state not in {"clean", "dirty"}:
        raise ValueError("Git revisions require component_worktree_state 'clean' or 'dirty'")
    if component_image_digest is not None and not re.fullmatch(
        r"sha256:[0-9a-fA-F]{64}", component_image_digest
    ):
        raise ValueError("component_image_digest must use sha256:<64 hex characters>")
    return is_fixture


def _validate_component_revision(component_revision: str) -> None:
    if not isinstance(component_revision, str) or not component_revision.strip():
        raise ValueError("component_revision must be a non-empty string")
    if component_revision.startswith("fixture:"):
        return
    if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", component_revision):
        raise ValueError(
            "component_revision must be a full 40- or 64-character git commit SHA "
            "or start with 'fixture:'"
        )


if __name__ == "__main__":
    raise SystemExit(main())
