from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from eval_ground_truth_lab.validators.result import ValidationResult

TRADER_RISK_AUDIT_VALIDATOR_VERSION = "trader-risk-audit-exact-replay-validators-v1"

_TOP_LEVEL_FIELDS = {
    "adapter_version",
    "contract_version",
    "evidence",
    "evidence_sha256",
    "privacy_classification",
    "provenance_sha256",
    "source",
}
_SOURCE_FIELDS = {
    "bundle_sha256",
    "git_blob_sha1",
    "git_commit",
    "git_tree",
    "package",
    "package_version",
    "repository_state",
    "source_path",
}
_EXPECTED_FIELDS = {
    "adapter_version",
    "contract_version",
    "evidence",
    "evidence_sha256",
    "privacy_classification",
    "provenance_sha256",
    "source",
}
_EXPECTED_EVIDENCE_FIELDS = {
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
_CANDIDATE_FIELDS = {"package", "version"}
_CHECK_FIELDS = {
    "all_violation_source_rows_resolve",
    "all_violations_have_source_rows",
    "manifest_artifacts_verified",
    "manifest_content_hash_verified",
    "pnl_reconciled",
}
_METRIC_FIELDS = {
    "normalized_trade_count",
    "pnl_reconciliation_delta",
    "resolved_trace_rate",
    "traceability_rate",
    "violation_count",
}
_BOUNDARY_FIELDS = {
    "applies_ground_truth",
    "applies_thresholds",
    "bundles_eval_ground_truth_lab",
    "description",
    "trace_reference_scheme",
}
_ARTIFACT_FIELDS = {"name", "sha256"}
_TRACE_FIELDS = {"rule_ref", "source_row_refs", "violation_ref"}


def validate_trader_risk_audit_case(
    *, case_id: str, expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> tuple[ValidationResult, ...]:
    """Compare a verified Trader export with one versioned synthetic expectation."""

    structure_issues = _structure_issues(expected=expected, actual=actual)
    if structure_issues:
        return (
            ValidationResult(
                case_id=case_id,
                validator_id="trader_risk_audit.structured_output",
                passed=False,
                category="invalid_structured_output",
                message="Trader Risk Audit replay shape is invalid: " + "; ".join(structure_issues),
                evidence={"issue_count": len(structure_issues)},
            ),
        )

    expected_source = _mapping(expected["source"])
    actual_source = _mapping(actual["source"])
    expected_evidence = _mapping(expected["evidence"])
    actual_evidence = _mapping(actual["evidence"])
    expected_candidate = _mapping(expected_evidence["candidate"])
    actual_candidate = _mapping(actual_evidence["candidate"])
    actual_checks = _mapping(actual_evidence["checks"])
    actual_metrics = _mapping(actual_evidence["metrics"])

    results = [
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.adapter_contract",
            category="adapter_contract_mismatch",
            label="adapter and export contract versions",
            expected_value={
                "adapter_version": expected["adapter_version"],
                "contract_version": expected["contract_version"],
                "privacy_classification": expected["privacy_classification"],
            },
            actual_value={
                "adapter_version": actual["adapter_version"],
                "contract_version": actual["contract_version"],
                "privacy_classification": actual["privacy_classification"],
            },
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.source_provenance",
            category="provenance_mismatch",
            label="pinned Trader Risk Audit source provenance",
            expected_value=dict(expected_source),
            actual_value=dict(actual_source),
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.evidence_identity",
            category="evidence_mismatch",
            label="sanitized evidence identity",
            expected_value={
                "evidence_content_hash": expected_evidence["evidence_content_hash"],
                "evidence_sha256": expected["evidence_sha256"],
                "manifest_content_hash": expected_evidence["manifest_content_hash"],
                "provenance_sha256": expected["provenance_sha256"],
            },
            actual_value={
                "evidence_content_hash": actual_evidence["evidence_content_hash"],
                "evidence_sha256": actual["evidence_sha256"],
                "manifest_content_hash": actual_evidence["manifest_content_hash"],
                "provenance_sha256": actual["provenance_sha256"],
            },
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.candidate_version",
            category="candidate_version_mismatch",
            label="Trader Risk Audit candidate version",
            expected_value=dict(expected_candidate),
            actual_value=dict(actual_candidate),
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.case_contract",
            category="evidence_mismatch",
            label="evidence case and contract identity",
            expected_value={
                "case_id": expected_evidence["case_id"],
                "contract_version": expected_evidence["contract_version"],
            },
            actual_value={
                "case_id": actual_evidence["case_id"],
                "contract_version": actual_evidence["contract_version"],
            },
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.evaluation_boundary",
            category="evidence_boundary_mismatch",
            label="evaluation boundary",
            expected_value=expected_evidence["evaluation_boundary"],
            actual_value=actual_evidence["evaluation_boundary"],
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.artifact_digests",
            category="evidence_mismatch",
            label="artifact digest receipts",
            expected_value=expected_evidence["artifact_digests"],
            actual_value=actual_evidence["artifact_digests"],
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.trace_preview",
            category="evidence_mismatch",
            label="opaque trace preview",
            expected_value=expected_evidence["trace_preview"],
            actual_value=actual_evidence["trace_preview"],
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.export_checks",
            category="evidence_check_failure",
            label="upstream manifest, trace, and P&L checks",
            expected_value=expected_evidence["checks"],
            actual_value=dict(actual_checks),
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.synthetic_metrics",
            category="observation_mismatch",
            label="synthetic fixture observations",
            expected_value=expected_evidence["metrics"],
            actual_value=dict(actual_metrics),
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.evidence_status",
            category="evidence_not_ready",
            label="evidence readiness status",
            expected_value=expected_evidence["status"],
            actual_value=actual_evidence["status"],
        ),
    ]
    return tuple(results)


def _structure_issues(*, expected: Mapping[str, Any], actual: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    _check_fields(expected, _EXPECTED_FIELDS, "expected", issues)
    _check_fields(actual, _TOP_LEVEL_FIELDS, "actual", issues)
    expected_source = expected.get("source")
    actual_source = actual.get("source")
    expected_evidence = expected.get("evidence")
    actual_evidence = actual.get("evidence")
    if isinstance(expected_source, Mapping):
        _check_fields(expected_source, _SOURCE_FIELDS, "expected.source", issues)
    else:
        issues.append("expected.source is not an object")
    if isinstance(actual_source, Mapping):
        _check_fields(actual_source, _SOURCE_FIELDS, "actual.source", issues)
    else:
        issues.append("actual.source is not an object")
    if isinstance(expected_evidence, Mapping):
        _check_fields(
            expected_evidence,
            _EXPECTED_EVIDENCE_FIELDS,
            "expected.evidence",
            issues,
        )
    else:
        issues.append("expected.evidence is not an object")
    if isinstance(actual_evidence, Mapping):
        _check_fields(actual_evidence, _EXPECTED_EVIDENCE_FIELDS, "actual.evidence", issues)
    else:
        issues.append("actual.evidence is not an object")
    for label, evidence in (
        ("expected.evidence", expected_evidence),
        ("actual.evidence", actual_evidence),
    ):
        if isinstance(evidence, Mapping):
            _check_nested_evidence(evidence, label, issues)
    return issues


def _check_nested_evidence(evidence: Mapping[str, Any], label: str, issues: list[str]) -> None:
    for field, expected_fields in (
        ("candidate", _CANDIDATE_FIELDS),
        ("checks", _CHECK_FIELDS),
        ("evaluation_boundary", _BOUNDARY_FIELDS),
        ("metrics", _METRIC_FIELDS),
    ):
        value = evidence.get(field)
        if isinstance(value, Mapping):
            _check_fields(value, expected_fields, f"{label}.{field}", issues)
        else:
            issues.append(f"{label}.{field} is not an object")
    _check_mapping_list(
        evidence.get("artifact_digests"),
        expected_fields=_ARTIFACT_FIELDS,
        label=f"{label}.artifact_digests",
        issues=issues,
    )
    _check_mapping_list(
        evidence.get("trace_preview"),
        expected_fields=_TRACE_FIELDS,
        label=f"{label}.trace_preview",
        issues=issues,
        require_source_rows=True,
    )


def _check_mapping_list(
    value: Any,
    *,
    expected_fields: set[str],
    label: str,
    issues: list[str],
    require_source_rows: bool = False,
) -> None:
    if not isinstance(value, list):
        issues.append(f"{label} is not a list")
        return
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, Mapping):
            issues.append(f"{item_label} is not an object")
            continue
        _check_fields(item, expected_fields, item_label, issues)
        if require_source_rows and not isinstance(item.get("source_row_refs"), list):
            issues.append(f"{item_label}.source_row_refs is not a list")


def _check_fields(
    value: Mapping[str, Any], expected: set[str], label: str, issues: list[str]
) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        issues.append(f"{label} missing " + ",".join(missing))
    if unknown:
        issues.append(f"{label} unknown " + ",".join(unknown))


def _exact_result(
    *,
    case_id: str,
    validator_id: str,
    category: str,
    label: str,
    expected_value: Any,
    actual_value: Any,
) -> ValidationResult:
    passed = actual_value == expected_value
    return ValidationResult(
        case_id=case_id,
        validator_id=validator_id,
        passed=passed,
        category="none" if passed else category,
        message=f"{label} {'matches' if passed else 'does not match'} the pinned expectation",
        evidence={
            "actual": actual_value,
            "expected": expected_value,
        },
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):  # Guarded by _structure_issues.
        raise TypeError("Expected a mapping")
    return value
