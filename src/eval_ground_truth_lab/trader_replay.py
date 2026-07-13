from __future__ import annotations

import importlib.metadata
import json
import platform
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from eval_ground_truth_lab import __version__
from eval_ground_truth_lab.adapters import trader_risk_audit as adapter_module
from eval_ground_truth_lab.adapters.trader_risk_audit import (
    TRADER_RISK_AUDIT_ADAPTER_VERSION,
    TraderRiskAuditEvidenceAdapter,
)
from eval_ground_truth_lab.datasets import Dataset, load_dataset
from eval_ground_truth_lab.evidence import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    sha256_file,
    verify_evidence_manifest,
    write_evidence_manifest,
)
from eval_ground_truth_lab.runs import CaseResult, RunRecord, RunStore
from eval_ground_truth_lab.validators import trader_risk_audit as validator_module
from eval_ground_truth_lab.validators.trader_risk_audit import (
    TRADER_RISK_AUDIT_VALIDATOR_VERSION,
    validate_trader_risk_audit_case,
)

TRADER_RISK_AUDIT_REPLAY_SCHEMA_VERSION = "eval-lab-trader-risk-audit-replay-v1"


def run_trader_risk_audit_replay(
    *,
    dataset_path: str | Path,
    evidence_path: str | Path,
    provenance_path: str | Path,
    evidence_dir: str | Path,
    run_dir: str | Path,
    run_id: str | None = None,
    adapter: TraderRiskAuditEvidenceAdapter | None = None,
) -> int:
    """Run a pinned sanitized Trader export through Eval Lab's exact validators."""

    pack_root = Path(evidence_dir)
    run_root = Path(run_dir)
    _require_separate_run_directory(pack_root=pack_root, run_root=run_root)
    _require_empty_pack_directory(pack_root)

    dataset_source = Path(dataset_path)
    evidence_source = Path(evidence_path)
    provenance_source = Path(provenance_path)
    dataset = load_dataset(dataset_source)
    selected_adapter = adapter or TraderRiskAuditEvidenceAdapter(
        evidence_path=evidence_source,
        provenance_path=provenance_source,
    )
    source_provenance = selected_adapter.provenance.to_mapping()
    store = RunStore(run_root)
    run = store.create_run(
        run_id=run_id,
        run_type="trader_risk_audit_evidence_replay",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version=(
            f"trader-risk-audit-{selected_adapter.provenance.package_version}"
            f"@{selected_adapter.provenance.source_git_commit[:12]}"
        ),
        validator_version=TRADER_RISK_AUDIT_VALIDATOR_VERSION,
        threshold_config_version="exact-versioned-synthetic-expectation-v1",
    )

    has_failure = False
    try:
        for case in dataset.cases:
            adapter_result = selected_adapter.invoke(case.to_canonical_mapping())
            if not isinstance(adapter_result.output, Mapping):
                raise TypeError("Trader Risk Audit adapter output must be an object")
            if not isinstance(case.expected, Mapping):
                raise TypeError("Trader Risk Audit expected value must be an object")
            actual = dict(adapter_result.output)
            validator_results = validate_trader_risk_audit_case(
                case_id=case.id,
                expected=case.expected,
                actual=actual,
            )
            case_passed = all(result.passed for result in validator_results)
            has_failure = has_failure or not case_passed
            actual["correct"] = case_passed
            store.add_case_result(
                run.run_id,
                CaseResult(
                    case_id=case.id,
                    output=actual,
                    validator_results=tuple(asdict(result) for result in validator_results),
                    cost_usd=0.0,
                    latency_ms=adapter_result.latency_ms,
                ),
            )
    except BaseException:
        store.interrupt_run(run.run_id)
        raise

    completed = store.complete_run(run.run_id)
    implementation_sha256 = {
        "adapter": sha256_file(Path(adapter_module.__file__)),
        "runner": sha256_file(Path(__file__)),
        "validators": sha256_file(Path(validator_module.__file__)),
    }
    runtime = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pyyaml": importlib.metadata.version("PyYAML"),
    }
    result = _build_replay_result(
        dataset=dataset,
        run=completed,
        source_provenance=source_provenance,
        dataset_raw_sha256=sha256_file(dataset_source),
        implementation_sha256=implementation_sha256,
        runtime=runtime,
    )

    result_path = pack_root / "replay-result.json"
    report_path = pack_root / "replay-report.md"
    input_dir = pack_root / "inputs"
    run_artifact_dir = pack_root / "run"
    input_dir.mkdir(parents=True)
    run_artifact_dir.mkdir()
    dataset_artifact = input_dir / "dataset.jsonl"
    evidence_artifact = input_dir / "eval-evidence.json"
    provenance_artifact = input_dir / "source-provenance.json"
    run_source = run_root / f"{completed.run_id}.json"
    seal_source = run_root / f"{completed.run_id}.sha256"
    run_artifact = run_artifact_dir / run_source.name
    seal_artifact = run_artifact_dir / seal_source.name

    atomic_write_json(result_path, result)
    atomic_write_text(report_path, render_trader_risk_audit_replay_markdown(result))
    atomic_write_bytes(dataset_artifact, dataset_source.read_bytes())
    atomic_write_bytes(evidence_artifact, evidence_source.read_bytes())
    atomic_write_bytes(provenance_artifact, provenance_source.read_bytes())
    atomic_write_bytes(run_artifact, run_source.read_bytes())
    atomic_write_bytes(seal_artifact, seal_source.read_bytes())
    declared = [
        result_path.relative_to(pack_root),
        report_path.relative_to(pack_root),
        dataset_artifact.relative_to(pack_root),
        evidence_artifact.relative_to(pack_root),
        provenance_artifact.relative_to(pack_root),
        run_artifact.relative_to(pack_root),
        seal_artifact.relative_to(pack_root),
    ]
    manifest_path = write_evidence_manifest(
        pack_root,
        declared,
        metadata={
            "adapter_version": TRADER_RISK_AUDIT_ADAPTER_VERSION,
            "contract_version": selected_adapter.provenance.contract_version,
            "dataset_hash": dataset.metadata.dataset_hash,
            "dataset_raw_sha256": sha256_file(dataset_source),
            "evidence_content_hash": selected_adapter.provenance.evidence_content_hash,
            "evidence_sha256": selected_adapter.provenance.evidence_sha256,
            "fixture": True,
            "gate_passed": not has_failure,
            "harness_version": f"eval-ground-truth-lab-{__version__}",
            "implementation_sha256": implementation_sha256,
            "privacy_classification": selected_adapter.provenance.privacy_classification,
            "run_id": completed.run_id,
            "runtime": runtime,
            "source_bundle_sha256": selected_adapter.provenance.source_bundle_sha256,
            "source_git_commit": selected_adapter.provenance.source_git_commit,
            "source_git_tree": selected_adapter.provenance.source_git_tree,
            "validator_version": TRADER_RISK_AUDIT_VALIDATOR_VERSION,
        },
    )
    verification = verify_evidence_manifest(manifest_path)
    print(
        json.dumps(
            {
                "content_address": verification.content_address,
                "gate_passed": not has_failure,
                "manifest": str(manifest_path),
                "run_id": completed.run_id,
            },
            sort_keys=True,
        )
    )
    return 1 if has_failure else 0


def render_trader_risk_audit_replay_markdown(result: Mapping[str, Any]) -> str:
    gate = _mapping(result.get("gate"), "gate")
    dataset = _mapping(result.get("dataset"), "dataset")
    provenance = _mapping(result.get("source_provenance"), "source_provenance")
    run = _mapping(result.get("run"), "run")
    cases = result.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    lines = [
        "# Trader Risk Audit sanitized evidence replay",
        "",
        f"Gate: **{'PASS' if gate.get('passed') else 'FAIL'}**",
        "",
        "This is a deterministic compatibility replay of one fully synthetic, sanitized",
        "Trader Risk Audit export. It is not a financial-performance evaluation, live-data",
        "audit, external-user case study, investment recommendation, or production claim.",
        "",
        "## Source pins",
        "",
        f"- Trader package: `{provenance.get('package')}` / `{provenance.get('package_version')}`",
        f"- Export contract: `{provenance.get('contract_version')}`",
        f"- Source commit: `{provenance.get('source_git_commit')}`",
        f"- Source tree: `{provenance.get('source_git_tree')}`",
        f"- Source bundle SHA-256: `{provenance.get('source_bundle_sha256')}`",
        f"- Evidence SHA-256: `{provenance.get('evidence_sha256')}`",
        f"- Evidence content hash: `{provenance.get('evidence_content_hash')}`",
        f"- Privacy classification: `{provenance.get('privacy_classification')}`",
        "",
        "## Eval run",
        "",
        f"- Run ID: `{run.get('run_id')}`",
        f"- Candidate version: `{run.get('candidate_version')}`",
        f"- Dataset: `{dataset.get('dataset_id')}` / `{dataset.get('dataset_hash')}`",
        f"- Dataset cases: `{dataset.get('case_count')}`",
        f"- Validator: `{run.get('validator_version')}`",
        "",
        "## Case decisions",
        "",
        "| Case | Status | Failed validators |",
        "|---|---|---|",
    ]
    for raw_case in cases:
        case = _mapping(raw_case, "cases[]")
        failures = case.get("failed_validators")
        if not isinstance(failures, list):
            raise ValueError("failed_validators must be a list")
        lines.append(
            f"| `{case.get('case_id')}` | "
            f"`{'pass' if case.get('passed') else 'fail'}` | "
            f"`{', '.join(str(value) for value in failures) or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Decision boundary",
            "",
            "PASS means the pinned sanitized export matches this self-authored synthetic "
            "dataset and its exact contract expectations. It does not validate suitable "
            "risk thresholds, investment outcomes, raw-source correctness, publisher "
            "authenticity, external adoption, or general workflow quality.",
            "",
        ]
    )
    return "\n".join(lines)


def _build_replay_result(
    *,
    dataset: Dataset,
    run: RunRecord,
    source_provenance: Mapping[str, Any],
    dataset_raw_sha256: str,
    implementation_sha256: Mapping[str, str],
    runtime: Mapping[str, str],
) -> dict[str, Any]:
    cases = []
    failed_validator_count = 0
    for case_result in run.case_results:
        failures = [
            str(result.get("validator_id"))
            for result in case_result.validator_results
            if result.get("passed") is False
        ]
        failed_validator_count += len(failures)
        cases.append(
            {
                "case_id": case_result.case_id,
                "failed_validators": failures,
                "passed": not failures,
            }
        )
    return {
        "cases": cases,
        "dataset": {
            "case_count": dataset.metadata.case_count,
            "dataset_hash": dataset.metadata.dataset_hash,
            "dataset_id": dataset.metadata.dataset_id,
            "raw_sha256": dataset_raw_sha256,
            "schema_version": dataset.metadata.schema_version,
        },
        "gate": {
            "failed_validator_count": failed_validator_count,
            "passed": failed_validator_count == 0,
        },
        "provenance": {
            "fixture": True,
            "harness_version": f"eval-ground-truth-lab-{__version__}",
            "implementation_sha256": dict(implementation_sha256),
            "runtime": dict(runtime),
        },
        "run": {
            "candidate_version": run.candidate_version,
            "completed_at": run.completed_at,
            "run_id": run.run_id,
            "started_at": run.started_at,
            "validator_version": run.validator_version,
        },
        "schema_version": TRADER_RISK_AUDIT_REPLAY_SCHEMA_VERSION,
        "scope": {
            "applies_financial_advice": False,
            "evaluates_raw_trades": False,
            "external_user_case_study": False,
            "production_evidence": False,
            "replay_type": "pinned_synthetic_sanitized_export",
        },
        "source_provenance": dict(source_provenance),
    }


def _require_empty_pack_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Evidence path is not a directory: {path}")
        if any(path.iterdir()):
            raise ValueError(f"Evidence directory must be empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def _require_separate_run_directory(*, pack_root: Path, run_root: Path) -> None:
    resolved_pack = pack_root.resolve()
    resolved_run = run_root.resolve()
    if resolved_run == resolved_pack or resolved_pack in resolved_run.parents:
        raise ValueError("run_dir must not equal or be nested inside evidence_dir")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value
