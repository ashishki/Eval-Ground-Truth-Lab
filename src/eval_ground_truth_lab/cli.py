from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_ground_truth_lab.adapters import GdevAgentConfig, GdevAgentHttpAdapter
from eval_ground_truth_lab.compare import ComparisonReport, ThresholdConfig, compare_runs
from eval_ground_truth_lab.cost import check_budget, load_budget_policy, rollup_telemetry
from eval_ground_truth_lab.datasets import Dataset, load_dataset
from eval_ground_truth_lab.reports import render_markdown_report
from eval_ground_truth_lab.runs import CaseResult, RunRecord, RunStore
from eval_ground_truth_lab.validators import GdevValidatorThresholds, validate_gdev_case


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
    gdev_parser.add_argument("--report", required=True)
    gdev_parser.add_argument(
        "--threshold-config",
        default="datasets/gdev_agent/thresholds.json",
    )

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
            threshold_config_path=args.threshold_config,
        )
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
    threshold_config_path: str | Path = "datasets/gdev_agent/thresholds.json",
    adapter: GdevAgentHttpAdapter | None = None,
) -> int:
    dataset = load_dataset(dataset_path)
    validator_thresholds = _load_gdev_validator_thresholds(Path(threshold_config_path))
    selected_adapter = adapter or _build_gdev_adapter(base_url)
    store = RunStore(run_dir)
    run = store.create_run(
        run_id=run_id,
        run_type="candidate",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version=candidate_version,
        validator_version="gdev-validators-v1",
        threshold_config_version=_threshold_config_version(Path(threshold_config_path)),
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
    )
    return 1 if has_failure else 0


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
        },
    )
    report_path.write_text(report, encoding="utf-8")


def _build_gdev_adapter(base_url: str) -> GdevAgentHttpAdapter:
    return GdevAgentHttpAdapter(GdevAgentConfig.from_environment(base_url=base_url))


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


if __name__ == "__main__":
    raise SystemExit(main())
