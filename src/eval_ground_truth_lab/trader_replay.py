from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from eval_ground_truth_lab import __version__
from eval_ground_truth_lab import evidence as evidence_module
from eval_ground_truth_lab.adapters import trader_risk_audit as adapter_module
from eval_ground_truth_lab.adapters.trader_risk_audit import (
    SYNTHETIC_PRIVACY_CLASSIFICATION,
    TRADER_RISK_AUDIT_ADAPTER_VERSION,
    TRADER_RISK_AUDIT_PACKAGE,
    TraderRiskAuditEvidenceAdapter,
    read_regular_file_bytes,
)
from eval_ground_truth_lab.datasets import Dataset, load_dataset_bytes
from eval_ground_truth_lab.datasets import registry as dataset_module
from eval_ground_truth_lab.evidence import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    verify_evidence_manifest,
    write_evidence_manifest,
)
from eval_ground_truth_lab.implementation_provenance import build_implementation_provenance
from eval_ground_truth_lab.runs import CaseResult, RunRecord, RunStore
from eval_ground_truth_lab.runs import store as run_store_module
from eval_ground_truth_lab.trader_source_identity import (
    TraderSourceIdentityProofError,
    VerifiedTraderSourceIdentity,
    verify_trader_source_identity_proof,
)
from eval_ground_truth_lab.validators import trader_risk_audit as validator_module
from eval_ground_truth_lab.validators.trader_risk_audit import (
    TRADER_RISK_AUDIT_VALIDATOR_VERSION,
    trader_risk_audit_expected_structure_issues,
    validate_trader_risk_audit_case,
)

TRADER_RISK_AUDIT_REPLAY_SCHEMA_VERSION = "eval-lab-trader-risk-audit-replay-v1"
_DEFAULT_DATASET_NAME = "synthetic_quickstart_v1.jsonl"
_DEFAULT_EVIDENCE_NAME = "eval-evidence.json"
_DEFAULT_PROVENANCE_NAME = "synthetic_quickstart_v1.provenance.json"
_DEFAULT_SOURCE_IDENTITY_PROOF_NAME = "synthetic_quickstart_v1.git-proof.json"
_TRUSTED_CASE_ID = "synthetic-quickstart-v1"
_TRUSTED_CASE_INPUT = {"evidence_case_id": _TRUSTED_CASE_ID}
_TRUSTED_CASE_METADATA = {
    "external_annotations": 0,
    "fixture_kind": "fully_synthetic",
    "intended_use": "contract_compatibility_replay",
    "source_data": "invented",
}
_TRUSTED_DATASET_PRIVACY = "fully-synthetic-packaged-expectation-dataset"
_UNTRUSTED_DATASET_PRIVACY = "caller-supplied-dataset-not-privacy-reviewed"
_UNTRUSTED_EVIDENCE_PRIVACY = "caller-supplied-evidence-not-privacy-reviewed"


class TraderRiskAuditReplayConfigurationError(ValueError):
    """Raised before a replay starts when its fixed v1 coverage is invalid."""


@dataclass(frozen=True)
class _TraderReplayInputSnapshot:
    dataset_bytes: bytes
    dataset_source_name: str
    evidence_bytes: bytes
    provenance_bytes: bytes
    source_identity_proof_bytes: bytes
    trusted_source_identity: VerifiedTraderSourceIdentity
    trusted_dataset_bytes_match: bool
    trusted_evidence_bytes_match: bool
    trusted_provenance_bytes_match: bool


@dataclass(frozen=True)
class _TraderDatasetTrust:
    fixture: bool
    privacy_classification: str
    replay_type: str
    source: str

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _TraderSourceTrust:
    evidence_source: str
    privacy_classification: str
    privacy_reviewed: bool
    provenance_source: str
    reviewed: bool
    source_identity_proof_sha256: str
    source_identity_verified: bool
    status: str

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def run_trader_risk_audit_replay(
    *,
    dataset_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    provenance_path: str | Path | None = None,
    evidence_dir: str | Path,
    run_dir: str | Path,
    run_id: str | None = None,
    adapter: TraderRiskAuditEvidenceAdapter | None = None,
) -> int:
    """Run a Trader evidence snapshot through Eval Lab's exact validators."""

    pack_root = Path(evidence_dir)
    run_root = Path(run_dir)
    _require_separate_run_directory(pack_root=pack_root, run_root=run_root)
    _require_available_pack_directory(pack_root)

    # Read every caller-controlled input exactly once. Parsing, validation,
    # hashing, adapter execution, and evidence packaging all use these same
    # immutable byte snapshots, so a later path mutation cannot change what is
    # sealed into the pack.
    snapshot = _load_input_snapshot(
        dataset_path=dataset_path,
        evidence_path=evidence_path,
        provenance_path=provenance_path,
    )
    dataset = load_dataset_bytes(
        snapshot.dataset_bytes,
        source_path=snapshot.dataset_source_name,
    )
    _require_v1_dataset_coverage(dataset)
    dataset_trust = _validate_and_classify_dataset(dataset=dataset, snapshot=snapshot)
    selected_adapter = adapter or TraderRiskAuditEvidenceAdapter.from_bytes(
        evidence_bytes=snapshot.evidence_bytes,
        provenance_bytes=snapshot.provenance_bytes,
    )
    _require_adapter_snapshot_match(adapter=selected_adapter, snapshot=snapshot)
    source_trust = _classify_source_trust(adapter=selected_adapter, snapshot=snapshot)
    source_provenance = _source_provenance_mapping(
        adapter=selected_adapter,
        source_trust=source_trust,
    )
    _prepare_empty_pack_directory(pack_root)
    store = RunStore(run_root)
    run = store.create_run(
        run_id=run_id,
        run_type="trader_risk_audit_evidence_replay",
        dataset_hash=dataset.metadata.dataset_hash,
        candidate_version=_candidate_version(selected_adapter, source_trust=source_trust),
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
            actual = _apply_effective_source_trust(
                output=adapter_result.output,
                source_trust=source_trust,
            )
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

    terminal_snapshot = store.complete_run_snapshot(run.run_id)
    completed = terminal_snapshot.record
    run_binding = _run_binding(
        completed,
        record_bytes=terminal_snapshot.record_bytes,
        seal_bytes=terminal_snapshot.seal_bytes,
    )
    implementation = build_implementation_provenance(
        component_paths={
            "adapter": Path(adapter_module.__file__),
            "dataset_parser": Path(dataset_module.__file__),
            "evidence_manifest": Path(evidence_module.__file__),
            "run_store": Path(run_store_module.__file__),
            "runner": Path(__file__),
            "validators": Path(validator_module.__file__),
        },
        package_root=Path(__file__).parent,
    )
    runtime = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pyyaml": importlib.metadata.version("PyYAML"),
    }
    result = _build_replay_result(
        dataset=dataset,
        run=completed,
        source_provenance=source_provenance,
        dataset_raw_sha256=_sha256_bytes(snapshot.dataset_bytes),
        implementation=implementation,
        runtime=runtime,
        dataset_trust=dataset_trust,
        source_trust=source_trust,
        run_binding=run_binding,
    )
    _require_terminal_result_binding(
        completed=completed,
        terminal_record=terminal_snapshot.record,
        result=result,
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
    source_identity_proof_artifact = input_dir / "source-identity-proof.json"
    run_artifact = run_artifact_dir / f"{completed.run_id}.json"
    seal_artifact = run_artifact_dir / f"{completed.run_id}.sha256"

    atomic_write_json(result_path, result)
    atomic_write_text(report_path, render_trader_risk_audit_replay_markdown(result))
    atomic_write_bytes(dataset_artifact, snapshot.dataset_bytes)
    atomic_write_bytes(evidence_artifact, snapshot.evidence_bytes)
    atomic_write_bytes(provenance_artifact, snapshot.provenance_bytes)
    atomic_write_bytes(source_identity_proof_artifact, snapshot.source_identity_proof_bytes)
    atomic_write_bytes(run_artifact, terminal_snapshot.record_bytes)
    atomic_write_bytes(seal_artifact, terminal_snapshot.seal_bytes)
    declared = [
        result_path.relative_to(pack_root),
        report_path.relative_to(pack_root),
        dataset_artifact.relative_to(pack_root),
        evidence_artifact.relative_to(pack_root),
        provenance_artifact.relative_to(pack_root),
        source_identity_proof_artifact.relative_to(pack_root),
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
            "dataset_raw_sha256": _sha256_bytes(snapshot.dataset_bytes),
            "evidence_content_hash": selected_adapter.provenance.evidence_content_hash,
            "evidence_sha256": selected_adapter.provenance.evidence_sha256,
            "dataset_trust": dataset_trust.to_mapping(),
            "fixture": _replay_fixture(dataset_trust=dataset_trust, source_trust=source_trust),
            "gate_passed": not has_failure,
            "harness_version": f"eval-ground-truth-lab-{__version__}",
            "implementation": implementation,
            "implementation_sha256": implementation["components_sha256"],
            "privacy_classification": _replay_privacy_classification(
                dataset_trust=dataset_trust,
                source_trust=source_trust,
            ),
            "provenance_sha256": selected_adapter.provenance_sha256,
            "run_id": completed.run_id,
            "runtime": runtime,
            "run": run_binding,
            "source_provenance": source_provenance,
            "source_trust": source_trust.to_mapping(),
            "validator_version": TRADER_RISK_AUDIT_VALIDATOR_VERSION,
        },
    )
    verification = verify_evidence_manifest(manifest_path)
    _require_packaged_terminal_binding(
        manifest_path=manifest_path,
        result_path=result_path,
        run_path=run_artifact,
        seal_path=seal_artifact,
        run_binding=run_binding,
        record_bytes=terminal_snapshot.record_bytes,
        seal_bytes=terminal_snapshot.seal_bytes,
    )
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
    result_provenance = _mapping(result.get("provenance"), "provenance")
    dataset_trust = _mapping(result_provenance.get("dataset_trust"), "dataset_trust")
    source_trust = _mapping(result_provenance.get("source_trust"), "source_trust")
    source_identity = _mapping(provenance.get("source_identity"), "source_identity")
    run = _mapping(result.get("run"), "run")
    cases = result.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases must be a list")
    if dataset_trust.get("fixture") is True:
        dataset_statement = (
            "This is a deterministic compatibility replay of one fully synthetic expectation "
            "dataset distributed with Eval Lab."
        )
    else:
        dataset_statement = (
            "This replay uses a caller-supplied expectation dataset that passed the v1 schema "
            "allowlist but was not byte-identical to the packaged privacy-reviewed fixture."
        )
    if source_trust.get("reviewed") is True:
        title = "# Trader Risk Audit sanitized evidence replay"
        source_statement = (
            "The source evidence is the byte-identical packaged export. Its Git identity is "
            "bound by the packaged commit-to-tree-to-path-to-blob proof. It is not a "
            "financial-performance evaluation, live-data audit, external-user case study, "
            "investment recommendation, or production claim."
        )
        source_heading = "## Source pins"
        source_lines = [
            f"- Trader package: `{provenance.get('package')}` / "
            f"`{provenance.get('package_version')}`",
            f"- Export contract: `{provenance.get('contract_version')}`",
            f"- Source commit: `{source_identity.get('git_commit')}`",
            f"- Source tree: `{source_identity.get('git_tree')}`",
            f"- Source path: `{source_identity.get('path')}`",
            f"- Source blob: `{source_identity.get('git_blob_sha1')}`",
            f"- Source bundle SHA-256: `{source_identity.get('bundle_sha256')}`",
            f"- Evidence SHA-256: `{provenance.get('evidence_sha256')}`",
            f"- Evidence content hash: `{provenance.get('evidence_content_hash')}`",
            f"- Privacy classification: `{provenance.get('privacy_classification')}`",
        ]
        if dataset_trust.get("fixture") is True:
            trust_boundary = (
                "PASS means the pinned sanitized export matches this self-authored synthetic "
                "dataset and its exact contract expectations."
            )
        else:
            trust_boundary = (
                "PASS means only that the pinned sanitized export matches this caller-supplied "
                "schema-valid expectation dataset; Eval Lab makes no fixture or privacy claim "
                "for that dataset."
            )
    else:
        title = "# Trader Risk Audit caller evidence replay"
        source_statement = (
            "The evidence and provenance were supplied or modified by the caller. They passed "
            "format and internal hash checks only; Eval Lab did not review their privacy status "
            "or authenticate their source."
        )
        source_heading = "## Caller declarations (not trusted)"
        source_lines = [
            f"- Declared package: `{provenance.get('package')}` / "
            f"`{provenance.get('package_version')}`",
            f"- Declared contract: `{provenance.get('contract_version')}`",
            f"- Declared commit: `{source_identity.get('git_commit')}`",
            f"- Declared tree: `{source_identity.get('git_tree')}`",
            f"- Declared path: `{source_identity.get('path')}`",
            f"- Declared blob: `{source_identity.get('git_blob_sha1')}`",
            f"- Input SHA-256: `{provenance.get('evidence_sha256')}`",
            f"- Effective privacy status: `{provenance.get('privacy_classification')}`",
        ]
        trust_boundary = (
            "PASS means only that the caller evidence matches the selected schema-valid "
            "expectations; Eval Lab makes no source-authenticity or privacy claim for it."
        )
    lines = [
        title,
        "",
        f"Gate: **{'PASS' if gate.get('passed') else 'FAIL'}**",
        "",
        dataset_statement,
        source_statement,
        "",
        source_heading,
        "",
        *source_lines,
        "",
        "## Eval run",
        "",
        f"- Run ID: `{run.get('run_id')}`",
        f"- Candidate version: `{run.get('candidate_version')}`",
        f"- Dataset: `{dataset.get('dataset_id')}` / `{dataset.get('dataset_hash')}`",
        f"- Dataset cases: `{dataset.get('case_count')}`",
        f"- Dataset fixture: `{dataset_trust.get('fixture')}`",
        f"- Dataset privacy classification: `{dataset_trust.get('privacy_classification')}`",
        f"- Validator: `{run.get('validator_version')}`",
        f"- Run status: `{run.get('status')}`",
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
            trust_boundary + " It does not validate suitable "
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
    implementation: Mapping[str, Any],
    runtime: Mapping[str, str],
    dataset_trust: _TraderDatasetTrust,
    source_trust: _TraderSourceTrust,
    run_binding: Mapping[str, str],
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
            "dataset_trust": dataset_trust.to_mapping(),
            "fixture": _replay_fixture(dataset_trust=dataset_trust, source_trust=source_trust),
            "harness_version": f"eval-ground-truth-lab-{__version__}",
            "implementation": dict(implementation),
            "implementation_sha256": dict(implementation["components_sha256"]),
            "privacy_classification": _replay_privacy_classification(
                dataset_trust=dataset_trust,
                source_trust=source_trust,
            ),
            "runtime": dict(runtime),
            "source_trust": source_trust.to_mapping(),
        },
        "run": {
            **dict(run_binding),
            "completed_at": run.completed_at,
            "started_at": run.started_at,
        },
        "schema_version": TRADER_RISK_AUDIT_REPLAY_SCHEMA_VERSION,
        "scope": {
            "applies_financial_advice": False,
            "evaluates_raw_trades": False,
            "external_user_case_study": False,
            "production_evidence": False,
            "replay_type": _replay_type(dataset_trust=dataset_trust, source_trust=source_trust),
        },
        "source_provenance": dict(source_provenance),
    }


def _require_available_pack_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Evidence path is not a directory: {path}")
        if any(path.iterdir()):
            raise ValueError(f"Evidence directory must be empty: {path}")


def _prepare_empty_pack_directory(path: Path) -> None:
    _require_available_pack_directory(path)
    path.mkdir(parents=True, exist_ok=True)


def _load_input_snapshot(
    *,
    dataset_path: str | Path | None,
    evidence_path: str | Path | None,
    provenance_path: str | Path | None,
) -> _TraderReplayInputSnapshot:
    trusted_dataset_bytes = _load_resource_bytes(_DEFAULT_DATASET_NAME)
    trusted_evidence_bytes = _load_resource_bytes(_DEFAULT_EVIDENCE_NAME)
    trusted_provenance_bytes = _load_resource_bytes(_DEFAULT_PROVENANCE_NAME)
    source_identity_proof_bytes = _load_resource_bytes(_DEFAULT_SOURCE_IDENTITY_PROOF_NAME)
    try:
        trusted_source_identity = verify_trader_source_identity_proof(
            proof_bytes=source_identity_proof_bytes,
            evidence_bytes=trusted_evidence_bytes,
        )
    except TraderSourceIdentityProofError as exc:
        raise TraderRiskAuditReplayConfigurationError(
            "Packaged Trader source identity proof is invalid"
        ) from exc
    if dataset_path is None:
        dataset_bytes = trusted_dataset_bytes
        dataset_source_name = _DEFAULT_DATASET_NAME
    else:
        dataset_bytes, dataset_source_name = _load_input_bytes(
            path=dataset_path,
            resource_name=_DEFAULT_DATASET_NAME,
            label="Trader Risk Audit replay dataset",
        )
    if evidence_path is None:
        evidence_bytes = trusted_evidence_bytes
    else:
        evidence_bytes = read_regular_file_bytes(
            evidence_path,
            "Trader Risk Audit evidence export",
        )
    if provenance_path is None:
        provenance_bytes = trusted_provenance_bytes
    else:
        provenance_bytes = read_regular_file_bytes(
            provenance_path,
            "Trader Risk Audit source provenance",
        )
    return _TraderReplayInputSnapshot(
        dataset_bytes=dataset_bytes,
        dataset_source_name=dataset_source_name,
        evidence_bytes=evidence_bytes,
        provenance_bytes=provenance_bytes,
        source_identity_proof_bytes=source_identity_proof_bytes,
        trusted_source_identity=trusted_source_identity,
        trusted_dataset_bytes_match=(
            dataset_source_name == _DEFAULT_DATASET_NAME and dataset_bytes == trusted_dataset_bytes
        ),
        trusted_evidence_bytes_match=evidence_bytes == trusted_evidence_bytes,
        trusted_provenance_bytes_match=provenance_bytes == trusted_provenance_bytes,
    )


def _load_input_bytes(
    *,
    path: str | Path | None,
    resource_name: str,
    label: str,
) -> tuple[bytes, str]:
    if path is not None:
        source = Path(path)
        return read_regular_file_bytes(source, label), source.name
    return _load_resource_bytes(resource_name), resource_name


def _load_resource_bytes(resource_name: str) -> bytes:
    resource = (
        resources.files("eval_ground_truth_lab")
        .joinpath("resources")
        .joinpath("trader_risk_audit")
        .joinpath(resource_name)
    )
    if not resource.is_file():
        raise TraderRiskAuditReplayConfigurationError(
            f"Packaged Trader Risk Audit replay resource is missing: {resource_name}"
        )
    return resource.read_bytes()


def _require_v1_dataset_coverage(dataset: Dataset) -> None:
    if dataset.metadata.case_count != 1:
        raise TraderRiskAuditReplayConfigurationError(
            "Trader Risk Audit replay v1 requires exactly one dataset case; "
            f"received {dataset.metadata.case_count}"
        )


def _validate_and_classify_dataset(
    *,
    dataset: Dataset,
    snapshot: _TraderReplayInputSnapshot,
) -> _TraderDatasetTrust:
    case = dataset.cases[0]
    if case.id != _TRUSTED_CASE_ID:
        raise TraderRiskAuditReplayConfigurationError(
            f"Trader Risk Audit replay v1 accepts only case id {_TRUSTED_CASE_ID!r}"
        )
    if not isinstance(case.input, Mapping) or dict(case.input) != _TRUSTED_CASE_INPUT:
        raise TraderRiskAuditReplayConfigurationError(
            "Trader Risk Audit replay input must contain only the pinned evidence_case_id"
        )
    if case.metadata != _TRUSTED_CASE_METADATA:
        raise TraderRiskAuditReplayConfigurationError(
            "Trader Risk Audit replay metadata must exactly match the trusted synthetic schema"
        )
    if not isinstance(case.expected, Mapping):
        raise TraderRiskAuditReplayConfigurationError(
            "Trader Risk Audit replay expected payload must be an object"
        )
    structure_issues = trader_risk_audit_expected_structure_issues(case.expected)
    if structure_issues:
        raise TraderRiskAuditReplayConfigurationError(
            "Trader Risk Audit replay expected payload is not allowlisted: "
            + "; ".join(structure_issues)
        )

    if (
        snapshot.trusted_dataset_bytes_match
        and dataset.metadata.dataset_id == Path(_DEFAULT_DATASET_NAME).stem
    ):
        return _TraderDatasetTrust(
            fixture=True,
            privacy_classification=_TRUSTED_DATASET_PRIVACY,
            replay_type="pinned_synthetic_sanitized_export",
            source="packaged_byte-identical_fixture",
        )
    return _TraderDatasetTrust(
        fixture=False,
        privacy_classification=_UNTRUSTED_DATASET_PRIVACY,
        replay_type="caller_supplied_expectation_replay",
        source="caller_supplied_schema_validated_dataset",
    )


def _classify_source_trust(
    *,
    adapter: TraderRiskAuditEvidenceAdapter,
    snapshot: _TraderReplayInputSnapshot,
) -> _TraderSourceTrust:
    expected_identity = snapshot.trusted_source_identity
    provenance = adapter.provenance
    identity_matches_proof = (
        provenance.source_bundle_sha256 == expected_identity.source_bundle_sha256
        and provenance.source_git_blob_sha1 == expected_identity.source_git_blob_sha1
        and provenance.source_git_commit == expected_identity.source_git_commit
        and provenance.source_git_tree == expected_identity.source_git_tree
        and provenance.source_path == expected_identity.source_path
    )
    reviewed = (
        snapshot.trusted_evidence_bytes_match
        and snapshot.trusted_provenance_bytes_match
        and identity_matches_proof
    )
    if (
        snapshot.trusted_evidence_bytes_match
        and snapshot.trusted_provenance_bytes_match
        and not identity_matches_proof
    ):
        raise TraderRiskAuditReplayConfigurationError(
            "Packaged Trader provenance does not match its Git source identity proof"
        )
    if reviewed:
        return _TraderSourceTrust(
            evidence_source="packaged_byte_identical_evidence",
            privacy_classification=SYNTHETIC_PRIVACY_CLASSIFICATION,
            privacy_reviewed=True,
            provenance_source="packaged_byte_identical_provenance",
            reviewed=True,
            source_identity_proof_sha256=expected_identity.proof_sha256,
            source_identity_verified=True,
            status="packaged_reviewed_source",
        )
    return _TraderSourceTrust(
        evidence_source=(
            "packaged_byte_identical_evidence"
            if snapshot.trusted_evidence_bytes_match
            else "caller_supplied_or_modified_evidence"
        ),
        privacy_classification=_UNTRUSTED_EVIDENCE_PRIVACY,
        privacy_reviewed=False,
        provenance_source=(
            "packaged_byte_identical_provenance"
            if snapshot.trusted_provenance_bytes_match
            else "caller_supplied_or_modified_provenance"
        ),
        reviewed=False,
        source_identity_proof_sha256=expected_identity.proof_sha256,
        source_identity_verified=False,
        status="caller_source_unreviewed",
    )


def _source_provenance_mapping(
    *,
    adapter: TraderRiskAuditEvidenceAdapter,
    source_trust: _TraderSourceTrust,
) -> dict[str, Any]:
    provenance = adapter.provenance
    return {
        "adapter_version": provenance.adapter_version,
        "contract_version": provenance.contract_version,
        "declared_privacy_classification": provenance.privacy_classification,
        "evidence_content_hash": provenance.evidence_content_hash,
        "evidence_sha256": provenance.evidence_sha256,
        "package": TRADER_RISK_AUDIT_PACKAGE,
        "package_version": provenance.package_version,
        "privacy_classification": source_trust.privacy_classification,
        "provenance_sha256": adapter.provenance_sha256,
        "source_identity": {
            "bundle_sha256": provenance.source_bundle_sha256,
            "git_blob_sha1": provenance.source_git_blob_sha1,
            "git_commit": provenance.source_git_commit,
            "git_tree": provenance.source_git_tree,
            "path": provenance.source_path,
            "repository_state": provenance.source_repository_state,
            "status": (
                "packaged_git_object_chain_verified"
                if source_trust.source_identity_verified
                else "caller_declared_not_authenticated"
            ),
        },
        "trust": source_trust.to_mapping(),
    }


def _apply_effective_source_trust(
    *,
    output: Mapping[str, Any],
    source_trust: _TraderSourceTrust,
) -> dict[str, Any]:
    """Replace the adapter's fail-closed placeholder with replay-level trust.

    The structural adapter can validate caller declarations but cannot know
    whether its bytes are the packaged, privacy-reviewed resources. Only the
    replay layer has the byte-identity and Git-object proof needed to make that
    decision. RunStore therefore seals declarations and effective trust as
    separate fields; it never stores an unqualified caller privacy/source claim.
    """

    actual = dict(output)
    actual["effective_trust"] = {
        "privacy_classification": source_trust.privacy_classification,
        "privacy_reviewed": source_trust.privacy_reviewed,
        "source_identity_status": (
            "packaged_git_object_chain_verified"
            if source_trust.source_identity_verified
            else "caller_declared_not_authenticated"
        ),
        "source_reviewed": source_trust.reviewed,
        "status": source_trust.status,
    }
    return actual


def _candidate_version(
    adapter: TraderRiskAuditEvidenceAdapter,
    *,
    source_trust: _TraderSourceTrust,
) -> str:
    provenance = adapter.provenance
    if source_trust.reviewed:
        return f"trader-risk-audit-{provenance.package_version}@{provenance.source_git_commit[:12]}"
    return f"trader-risk-audit-caller-evidence@{provenance.evidence_sha256[:12]}"


def _replay_type(
    *,
    dataset_trust: _TraderDatasetTrust,
    source_trust: _TraderSourceTrust,
) -> str:
    if not source_trust.reviewed:
        return "caller_supplied_unreviewed_evidence_replay"
    return dataset_trust.replay_type


def _replay_fixture(
    *,
    dataset_trust: _TraderDatasetTrust,
    source_trust: _TraderSourceTrust,
) -> bool:
    return dataset_trust.fixture and source_trust.reviewed


def _replay_privacy_classification(
    *,
    dataset_trust: _TraderDatasetTrust,
    source_trust: _TraderSourceTrust,
) -> str:
    if not source_trust.reviewed:
        return source_trust.privacy_classification
    return dataset_trust.privacy_classification


def _run_identity(run: RunRecord) -> dict[str, str]:
    return {
        "candidate_version": run.candidate_version,
        "dataset_hash": run.dataset_hash,
        "run_id": run.run_id,
        "status": run.status,
        "validator_version": run.validator_version,
    }


def _run_binding(
    run: RunRecord,
    *,
    record_bytes: bytes,
    seal_bytes: bytes,
) -> dict[str, str]:
    return {
        **_run_identity(run),
        "record_sha256": _sha256_bytes(record_bytes),
        "seal_sha256": _sha256_bytes(seal_bytes),
    }


def _require_terminal_result_binding(
    *,
    completed: RunRecord,
    terminal_record: RunRecord,
    result: Mapping[str, Any],
) -> None:
    if completed != terminal_record or completed.status != "completed":
        raise RuntimeError("Terminal run snapshot does not contain the exact completed run")
    result_run = _mapping(result.get("run"), "result.run")
    expected_identity = _run_identity(completed)
    actual_identity = {field: result_run.get(field) for field in expected_identity}
    if actual_identity != expected_identity:
        raise RuntimeError("Replay result is not bound to the packaged terminal run")


def _require_packaged_terminal_binding(
    *,
    manifest_path: Path,
    result_path: Path,
    run_path: Path,
    seal_path: Path,
    run_binding: Mapping[str, str],
    record_bytes: bytes,
    seal_bytes: bytes,
) -> None:
    if run_path.read_bytes() != record_bytes or seal_path.read_bytes() != seal_bytes:
        raise RuntimeError("Packaged terminal run differs from the locked RunStore snapshot")
    manifest = json.loads(manifest_path.read_bytes())
    result = json.loads(result_path.read_bytes())
    if not isinstance(manifest, Mapping) or not isinstance(result, Mapping):
        raise RuntimeError("Trader replay pack binding artifacts must be JSON objects")
    metadata = _mapping(manifest.get("metadata"), "manifest.metadata")
    result_run = _mapping(result.get("run"), "result.run")
    if metadata.get("run") != run_binding:
        raise RuntimeError("Evidence manifest is not bound to the packaged terminal run")
    if {field: result_run.get(field) for field in run_binding} != dict(run_binding):
        raise RuntimeError("Replay result is not bound to the packaged terminal bytes")


def _require_adapter_snapshot_match(
    *,
    adapter: TraderRiskAuditEvidenceAdapter,
    snapshot: _TraderReplayInputSnapshot,
) -> None:
    if (
        adapter.evidence_bytes != snapshot.evidence_bytes
        or adapter.provenance_bytes != snapshot.provenance_bytes
    ):
        raise TraderRiskAuditReplayConfigurationError(
            "Provided adapter was not constructed from the replay input snapshots"
        )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_separate_run_directory(*, pack_root: Path, run_root: Path) -> None:
    resolved_pack = pack_root.resolve()
    resolved_run = run_root.resolve()
    if resolved_run == resolved_pack or resolved_pack in resolved_run.parents:
        raise ValueError("run_dir must not equal or be nested inside evidence_dir")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value
