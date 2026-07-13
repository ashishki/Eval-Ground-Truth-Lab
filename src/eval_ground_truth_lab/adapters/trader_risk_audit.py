from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from eval_ground_truth_lab.adapters.base import AdapterError, AdapterResult, UnsafeAdapterInputError

TRADER_RISK_AUDIT_ADAPTER_VERSION = "eval-lab-trader-risk-audit-adapter-v1"
TRADER_RISK_AUDIT_CONTRACT_VERSION = "trader-risk-audit-evidence-v1"
TRADER_RISK_AUDIT_PROVENANCE_SCHEMA_VERSION = "eval-lab-trader-risk-audit-source-provenance-v1"
TRADER_RISK_AUDIT_PACKAGE = "trader-risk-audit"
SYNTHETIC_PRIVACY_CLASSIFICATION = "fully-synthetic-sanitized-export"

_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_GIT_OBJECT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_CASE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_ARTIFACT_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_REFERENCE_PATTERNS = {
    "row": re.compile(r"row_[0-9a-f]{24}\Z"),
    "rule": re.compile(r"rule_[0-9a-f]{24}\Z"),
    "violation": re.compile(r"violation_[0-9a-f]{24}\Z"),
}
_REQUIRED_ARTIFACTS = frozenset(
    {
        "attribution_summary",
        "normalized_trades",
        "policy_file",
        "report_markdown",
        "source_export",
        "violations",
    }
)
_CHECK_FIELDS = frozenset(
    {
        "all_violation_source_rows_resolve",
        "all_violations_have_source_rows",
        "manifest_artifacts_verified",
        "manifest_content_hash_verified",
        "pnl_reconciled",
    }
)
_METRIC_FIELDS = frozenset(
    {
        "normalized_trade_count",
        "pnl_reconciliation_delta",
        "resolved_trace_rate",
        "traceability_rate",
        "violation_count",
    }
)
_EVIDENCE_FIELDS = frozenset(
    {
        "artifact_digests",
        "candidate",
        "case_id",
        "checks",
        "contract_version",
        "evaluation_boundary",
        "evidence_content_hash",
        "manifest_content_hash",
        "metrics",
        "status",
        "trace_preview",
    }
)
_EXPECTED_EVALUATION_BOUNDARY = {
    "applies_ground_truth": False,
    "applies_thresholds": False,
    "bundles_eval_ground_truth_lab": False,
    "description": (
        "Verified audit observations for consumption by a separately configured evaluation harness."
    ),
    "trace_reference_scheme": "sha256-v1",
}


class TraderRiskAuditEvidenceError(AdapterError):
    """Raised when a Trader Risk Audit export or its source pin is invalid."""


@dataclass(frozen=True)
class TraderRiskAuditProvenance:
    adapter_version: str
    privacy_classification: str
    package_version: str
    contract_version: str
    source_git_commit: str
    source_git_tree: str
    source_git_blob_sha1: str
    source_bundle_sha256: str
    source_repository_state: str
    source_path: str
    evidence_sha256: str
    evidence_content_hash: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "adapter_version": self.adapter_version,
            "contract_version": self.contract_version,
            "evidence_content_hash": self.evidence_content_hash,
            "evidence_sha256": self.evidence_sha256,
            "package": TRADER_RISK_AUDIT_PACKAGE,
            "package_version": self.package_version,
            "privacy_classification": self.privacy_classification,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_git_blob_sha1": self.source_git_blob_sha1,
            "source_git_commit": self.source_git_commit,
            "source_git_tree": self.source_git_tree,
            "source_path": self.source_path,
            "source_repository_state": self.source_repository_state,
        }


class TraderRiskAuditEvidenceAdapter:
    """Load one pinned sanitized Trader Risk Audit evidence export.

    The adapter does not run the financial audit, read raw trades, or infer
    ground truth. It verifies the upstream export contract and source fixture
    pins before Eval Lab validators compare observations with a versioned case.
    """

    def __init__(self, *, evidence_path: str | Path, provenance_path: str | Path) -> None:
        self.evidence_path = Path(evidence_path)
        self.provenance_path = Path(provenance_path)
        evidence_bytes, raw_evidence = _read_json_object(self.evidence_path, "evidence export")
        _, raw_provenance = _read_json_object(self.provenance_path, "source provenance")
        self.provenance = _validate_provenance(raw_provenance, evidence_bytes=evidence_bytes)
        self.evidence = _validate_evidence(raw_evidence, provenance=self.provenance)

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not _CASE_ID_PATTERN.fullmatch(case_id):
            raise UnsafeAdapterInputError("Trader Risk Audit case id is missing or unsafe")
        case_input = case.get("input")
        if not isinstance(case_input, Mapping) or set(case_input) != {"evidence_case_id"}:
            raise UnsafeAdapterInputError(
                "Trader Risk Audit case input must contain only evidence_case_id"
            )
        if case_input.get("evidence_case_id") != case_id:
            raise UnsafeAdapterInputError(
                "Trader Risk Audit evidence_case_id must match the dataset case id"
            )
        if self.evidence["case_id"] != case_id:
            raise TraderRiskAuditEvidenceError(
                "Trader Risk Audit export case_id does not match the dataset case id"
            )

        output = {
            "adapter_version": self.provenance.adapter_version,
            "contract_version": self.provenance.contract_version,
            "evidence": self.evidence,
            "evidence_sha256": self.provenance.evidence_sha256,
            "privacy_classification": self.provenance.privacy_classification,
            "source": {
                "bundle_sha256": self.provenance.source_bundle_sha256,
                "git_blob_sha1": self.provenance.source_git_blob_sha1,
                "git_commit": self.provenance.source_git_commit,
                "git_tree": self.provenance.source_git_tree,
                "package": TRADER_RISK_AUDIT_PACKAGE,
                "package_version": self.provenance.package_version,
                "repository_state": self.provenance.source_repository_state,
            },
        }
        return AdapterResult(
            output=output,
            exit_code=0,
            latency_ms=0.0,
            trace_id=f"trader-evidence-{self.provenance.evidence_content_hash[:24]}",
            operation_name="candidate.trader_risk_audit.evidence_replay",
        )


def _validate_provenance(
    raw: Mapping[str, Any], *, evidence_bytes: bytes
) -> TraderRiskAuditProvenance:
    _require_exact_fields(
        raw,
        {
            "adapter_version",
            "evidence",
            "privacy_classification",
            "schema_version",
            "source",
        },
        "source provenance",
    )
    if raw.get("schema_version") != TRADER_RISK_AUDIT_PROVENANCE_SCHEMA_VERSION:
        raise TraderRiskAuditEvidenceError("Unsupported Trader Risk Audit provenance schema")
    if raw.get("adapter_version") != TRADER_RISK_AUDIT_ADAPTER_VERSION:
        raise TraderRiskAuditEvidenceError("Unsupported Trader Risk Audit adapter version")
    if raw.get("privacy_classification") != SYNTHETIC_PRIVACY_CLASSIFICATION:
        raise TraderRiskAuditEvidenceError(
            "Trader Risk Audit replay accepts only the declared fully synthetic fixture"
        )

    source = _mapping(raw.get("source"), "source provenance.source")
    _require_exact_fields(
        source,
        {
            "bundle_sha256",
            "contract_version",
            "git_blob_sha1",
            "git_commit",
            "git_tree",
            "package",
            "package_version",
            "repository_state",
            "source_path",
        },
        "source provenance.source",
    )
    if source.get("package") != TRADER_RISK_AUDIT_PACKAGE:
        raise TraderRiskAuditEvidenceError("Source package must be trader-risk-audit")
    contract_version = _required_string(source.get("contract_version"), "contract_version")
    if contract_version != TRADER_RISK_AUDIT_CONTRACT_VERSION:
        raise TraderRiskAuditEvidenceError("Unsupported Trader Risk Audit evidence contract")
    package_version = _required_string(source.get("package_version"), "package_version")
    source_git_commit = _required_git_object(source.get("git_commit"), "git_commit")
    source_git_tree = _required_git_object(source.get("git_tree"), "git_tree")
    source_git_blob_sha1 = _required_git_object(source.get("git_blob_sha1"), "git_blob_sha1")
    source_bundle_sha256 = _required_digest(source.get("bundle_sha256"), "bundle_sha256")
    source_repository_state = _required_string(source.get("repository_state"), "repository_state")
    source_path = _safe_source_path(source.get("source_path"))

    evidence = _mapping(raw.get("evidence"), "source provenance.evidence")
    _require_exact_fields(evidence, {"content_hash", "sha256"}, "source provenance.evidence")
    evidence_sha256 = _required_digest(evidence.get("sha256"), "evidence.sha256")
    evidence_content_hash = _required_digest(evidence.get("content_hash"), "evidence.content_hash")
    if hashlib.sha256(evidence_bytes).hexdigest() != evidence_sha256:
        raise TraderRiskAuditEvidenceError("Evidence bytes do not match the provenance SHA-256")
    if _git_blob_sha1(evidence_bytes) != source_git_blob_sha1:
        raise TraderRiskAuditEvidenceError("Evidence bytes do not match the pinned Git blob")

    return TraderRiskAuditProvenance(
        adapter_version=TRADER_RISK_AUDIT_ADAPTER_VERSION,
        privacy_classification=SYNTHETIC_PRIVACY_CLASSIFICATION,
        package_version=package_version,
        contract_version=contract_version,
        source_git_commit=source_git_commit,
        source_git_tree=source_git_tree,
        source_git_blob_sha1=source_git_blob_sha1,
        source_bundle_sha256=source_bundle_sha256,
        source_repository_state=source_repository_state,
        source_path=source_path,
        evidence_sha256=evidence_sha256,
        evidence_content_hash=evidence_content_hash,
    )


def _validate_evidence(
    raw: Mapping[str, Any], *, provenance: TraderRiskAuditProvenance
) -> dict[str, Any]:
    _require_exact_fields(raw, _EVIDENCE_FIELDS, "evidence export")
    contract_version = _required_string(raw.get("contract_version"), "contract_version")
    if contract_version != provenance.contract_version:
        raise TraderRiskAuditEvidenceError("Evidence contract does not match source provenance")
    case_id = _required_string(raw.get("case_id"), "case_id")
    if not _CASE_ID_PATTERN.fullmatch(case_id):
        raise TraderRiskAuditEvidenceError("Evidence case_id is unsafe")
    _required_digest(raw.get("manifest_content_hash"), "manifest_content_hash")
    evidence_content_hash = _required_digest(
        raw.get("evidence_content_hash"), "evidence_content_hash"
    )
    if evidence_content_hash != provenance.evidence_content_hash:
        raise TraderRiskAuditEvidenceError("Evidence content hash does not match source provenance")
    canonical_payload = dict(raw)
    canonical_payload.pop("evidence_content_hash")
    computed_content_hash = hashlib.sha256(_canonical_json_bytes(canonical_payload)).hexdigest()
    if computed_content_hash != evidence_content_hash:
        raise TraderRiskAuditEvidenceError("Evidence content hash is invalid")

    candidate = _mapping(raw.get("candidate"), "evidence candidate")
    _require_exact_fields(candidate, {"package", "version"}, "evidence candidate")
    if candidate.get("package") != TRADER_RISK_AUDIT_PACKAGE:
        raise TraderRiskAuditEvidenceError("Evidence candidate package is invalid")
    if candidate.get("version") != provenance.package_version:
        raise TraderRiskAuditEvidenceError("Evidence package version does not match provenance")

    boundary = _mapping(raw.get("evaluation_boundary"), "evaluation_boundary")
    if dict(boundary) != _EXPECTED_EVALUATION_BOUNDARY:
        raise TraderRiskAuditEvidenceError("Evidence evaluation boundary is invalid")

    checks = _mapping(raw.get("checks"), "checks")
    _require_exact_fields(checks, _CHECK_FIELDS, "checks")
    if any(not isinstance(value, bool) for value in checks.values()):
        raise TraderRiskAuditEvidenceError("Every evidence check must be boolean")

    metrics = _mapping(raw.get("metrics"), "metrics")
    _require_exact_fields(metrics, _METRIC_FIELDS, "metrics")
    normalized_trade_count = _non_negative_int(
        metrics.get("normalized_trade_count"), "normalized_trade_count"
    )
    violation_count = _non_negative_int(metrics.get("violation_count"), "violation_count")
    _decimal_string(metrics.get("pnl_reconciliation_delta"), "pnl_reconciliation_delta")
    _rate(metrics.get("resolved_trace_rate"), "resolved_trace_rate")
    _rate(metrics.get("traceability_rate"), "traceability_rate")
    if normalized_trade_count == 0 and violation_count > 0:
        raise TraderRiskAuditEvidenceError("Violations cannot exist without normalized trades")

    status = raw.get("status")
    if status not in {"evidence_ready", "invalid_evidence"}:
        raise TraderRiskAuditEvidenceError("Evidence status is invalid")
    expected_status = "evidence_ready" if all(checks.values()) else "invalid_evidence"
    if status != expected_status:
        raise TraderRiskAuditEvidenceError("Evidence status is inconsistent with checks")

    _validate_artifact_digests(raw.get("artifact_digests"))
    _validate_trace_preview(raw.get("trace_preview"), violation_count=violation_count)
    # Return a plain JSON-compatible copy so callers cannot mutate the parsed mapping.
    return json.loads(json.dumps(raw))


def _validate_artifact_digests(value: Any) -> None:
    if not isinstance(value, list):
        raise TraderRiskAuditEvidenceError("artifact_digests must be a list")
    names: list[str] = []
    for index, item in enumerate(value):
        artifact = _mapping(item, f"artifact_digests[{index}]")
        _require_exact_fields(artifact, {"name", "sha256"}, f"artifact_digests[{index}]")
        name = _required_string(artifact.get("name"), f"artifact_digests[{index}].name")
        if not _ARTIFACT_NAME_PATTERN.fullmatch(name):
            raise TraderRiskAuditEvidenceError("Evidence artifact name is invalid")
        _required_digest(artifact.get("sha256"), f"artifact_digests[{index}].sha256")
        names.append(name)
    if names != sorted(names) or len(names) != len(set(names)):
        raise TraderRiskAuditEvidenceError("Evidence artifacts must be uniquely name-sorted")
    missing = sorted(_REQUIRED_ARTIFACTS - set(names))
    if missing:
        raise TraderRiskAuditEvidenceError(
            "Evidence export is missing required artifact digests: " + ", ".join(missing)
        )


def _validate_trace_preview(value: Any, *, violation_count: int) -> None:
    if not isinstance(value, list) or len(value) != min(violation_count, 5):
        raise TraderRiskAuditEvidenceError(
            "trace_preview length must equal min(violation_count, 5)"
        )
    for index, item in enumerate(value):
        trace = _mapping(item, f"trace_preview[{index}]")
        _require_exact_fields(
            trace,
            {"rule_ref", "source_row_refs", "violation_ref"},
            f"trace_preview[{index}]",
        )
        _required_reference(trace.get("rule_ref"), "rule")
        _required_reference(trace.get("violation_ref"), "violation")
        source_rows = trace.get("source_row_refs")
        if not isinstance(source_rows, list) or not source_rows:
            raise TraderRiskAuditEvidenceError("Trace preview source_row_refs must be non-empty")
        for row_ref in source_rows:
            _required_reference(row_ref, "row")


def _read_json_object(path: Path, label: str) -> tuple[bytes, Mapping[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise TraderRiskAuditEvidenceError(f"{label} must be a regular file")
    try:
        raw_bytes = path.read_bytes()
        raw = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise TraderRiskAuditEvidenceError(f"Cannot read {label}") from exc
    if not isinstance(raw, Mapping):
        raise TraderRiskAuditEvidenceError(f"{label} must be a JSON object")
    return raw_bytes, raw


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TraderRiskAuditEvidenceError(f"{field} must be an object")
    return value


def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str] | frozenset[str], field: str
) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if unknown:
            details.append("unknown=" + ",".join(unknown))
        raise TraderRiskAuditEvidenceError(f"{field} fields are invalid ({'; '.join(details)})")


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise TraderRiskAuditEvidenceError(f"{field} must be a non-empty string")
    return value


def _required_digest(value: Any, field: str) -> str:
    digest = _required_string(value, field)
    if not _DIGEST_PATTERN.fullmatch(digest):
        raise TraderRiskAuditEvidenceError(f"{field} must be a lowercase SHA-256 digest")
    return digest


def _required_git_object(value: Any, field: str) -> str:
    object_id = _required_string(value, field)
    if not _GIT_OBJECT_PATTERN.fullmatch(object_id):
        raise TraderRiskAuditEvidenceError(f"{field} must be a full lowercase Git object id")
    return object_id


def _required_reference(value: Any, namespace: str) -> str:
    reference = _required_string(value, f"{namespace}_ref")
    if not _REFERENCE_PATTERNS[namespace].fullmatch(reference):
        raise TraderRiskAuditEvidenceError(f"Invalid {namespace} trace reference")
    return reference


def _safe_source_path(value: Any) -> str:
    text = _required_string(value, "source_path")
    path = PurePosixPath(text)
    if path.is_absolute() or "." in path.parts or ".." in path.parts or "\\" in text:
        raise TraderRiskAuditEvidenceError("source_path must be a safe relative POSIX path")
    return text


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TraderRiskAuditEvidenceError(f"{field} must be a non-negative integer")
    return value


def _decimal_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise TraderRiskAuditEvidenceError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise TraderRiskAuditEvidenceError(f"{field} must be decimal-compatible") from exc
    if not parsed.is_finite():
        raise TraderRiskAuditEvidenceError(f"{field} must be finite")
    return value


def _rate(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TraderRiskAuditEvidenceError(f"{field} must be numeric")
    rate = float(value)
    if not math.isfinite(rate) or not 0.0 <= rate <= 1.0:
        raise TraderRiskAuditEvidenceError(f"{field} must be a finite rate from 0 to 1")
    return rate


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TraderRiskAuditEvidenceError("Evidence must be canonical JSON data") from exc


def _git_blob_sha1(value: bytes) -> str:
    return hashlib.sha1(f"blob {len(value)}\0".encode() + value, usedforsecurity=False).hexdigest()
