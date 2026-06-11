from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from eval_ground_truth_lab.compare import ComparisonReport, ThresholdConfig, compare_runs
from eval_ground_truth_lab.datasets import Dataset, load_dataset
from eval_ground_truth_lab.reports import render_markdown_report
from eval_ground_truth_lab.runs import CaseResult, RunRecord


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

    args = parser.parse_args(argv)
    if args.command == "seeded-smoke":
        return run_seeded_smoke_eval(
            dataset_path=args.dataset,
            report_path=args.report,
            threshold_config_path=args.threshold_config,
        )
    raise ValueError(f"Unsupported command {args.command}")


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
    return ThresholdConfig(
        max_accuracy_drop=float(raw["max_accuracy_drop"]),
        max_invalid_output_rate_increase=float(raw["max_invalid_output_rate_increase"]),
        max_unsafe_auto_approval_rate_increase=float(raw["max_unsafe_auto_approval_rate_increase"]),
        max_latency_p95_delta_ms=float(raw["max_latency_p95_delta_ms"]),
        max_cost_per_case_delta_usd=float(raw["max_cost_per_case_delta_usd"]),
    )


def _write_run_artifact(path: Path, record: RunRecord) -> None:
    path.write_text(
        json.dumps(record.to_mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
