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
}
_EXPECTED_FIELDS = {
    "adapter_version",
    "contract_version",
    "evidence",
    "evidence_sha256",
    "privacy_classification",
    "source",
}
_EXPECTED_EVIDENCE_FIELDS = {
    "candidate_version",
    "checks",
    "evidence_content_hash",
    "manifest_content_hash",
    "metrics",
    "status",
}


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
            },
            actual_value={
                "evidence_content_hash": actual_evidence["evidence_content_hash"],
                "evidence_sha256": actual["evidence_sha256"],
                "manifest_content_hash": actual_evidence["manifest_content_hash"],
            },
        ),
        _exact_result(
            case_id=case_id,
            validator_id="trader_risk_audit.candidate_version",
            category="candidate_version_mismatch",
            label="Trader Risk Audit candidate version",
            expected_value=expected_evidence["candidate_version"],
            actual_value=actual_candidate["version"],
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
        required_actual_evidence = {
            "candidate",
            "checks",
            "evidence_content_hash",
            "manifest_content_hash",
            "metrics",
            "status",
        }
        missing = sorted(required_actual_evidence - set(actual_evidence))
        if missing:
            issues.append("actual.evidence missing " + ",".join(missing))
        for field in ("candidate", "checks", "metrics"):
            if field in actual_evidence and not isinstance(actual_evidence[field], Mapping):
                issues.append(f"actual.evidence.{field} is not an object")
    else:
        issues.append("actual.evidence is not an object")
    return issues


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
