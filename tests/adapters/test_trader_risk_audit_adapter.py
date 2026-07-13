from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from eval_ground_truth_lab.adapters import (
    UNASSESSED_PRIVACY_CLASSIFICATION,
    TraderRiskAuditEvidenceAdapter,
    TraderRiskAuditEvidenceError,
    UnsafeAdapterInputError,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = ROOT / "datasets/trader_risk_audit"
EVIDENCE = DATASET_ROOT / "fixtures/synthetic_quickstart_v1/eval-evidence.json"
PROVENANCE = DATASET_ROOT / "synthetic_quickstart_v1.provenance.json"
CASE = {
    "id": "synthetic-quickstart-v1",
    "input": {"evidence_case_id": "synthetic-quickstart-v1"},
}


def test_adapter_separates_caller_declarations_from_unassessed_effective_trust() -> None:
    adapter = _adapter()

    first = adapter.invoke(CASE)
    second = adapter.invoke(deepcopy(CASE))

    assert first == second
    assert first.output is not second.output
    assert first.output["evidence"] is not second.output["evidence"]
    assert first.output["evidence"]["metrics"] is not second.output["evidence"]["metrics"]
    assert (
        first.output["evidence"]["artifact_digests"]
        is not second.output["evidence"]["artifact_digests"]
    )
    assert (
        first.output["evidence"]["trace_preview"] is not second.output["evidence"]["trace_preview"]
    )
    assert first.trace_id == "trader-evidence-d7e6fe92f50ba410a2c23882"
    assert first.operation_name == "candidate.trader_risk_audit.evidence_replay"
    assert first.output["adapter_version"] == "eval-lab-trader-risk-audit-adapter-v1"
    assert first.output["provenance_sha256"] == (
        "3cd4339892665f5ed0003856a4b251e7524733a4ce5c99fac834d84fcdf8e402"
    )
    assert first.output["declared_privacy_classification"] == ("fully-synthetic-sanitized-export")
    assert first.output["declared_source"] == {
        "bundle_sha256": ("2c5b36afa9b2a9847de1c97789c52c57600e1d38cfd4947458906ee3bb3992ca"),
        "git_blob_sha1": "9a64dc98e8edbe1ec39756611a6cb3b73b4994b9",
        "git_commit": "bf755a24450ff7c17328fa6d447f36bea8ea0fe5",
        "git_tree": "1a2c4ff91a7504642a1bae05a9487fa2e898e0b6",
        "package": "trader-risk-audit",
        "package_version": "0.2.0",
        "repository_state": "path-purged-publication-candidate",
        "source_path": "examples/synthetic_quickstart/evidence_preview/eval-evidence.json",
    }
    assert first.output["effective_trust"] == {
        "privacy_classification": UNASSESSED_PRIVACY_CLASSIFICATION,
        "privacy_reviewed": False,
        "source_identity_status": "not_assessed_by_structural_adapter",
        "source_reviewed": False,
        "status": "not_assessed_by_structural_adapter",
    }
    assert "privacy_classification" not in first.output
    assert "source" not in first.output

    first.output["evidence"]["metrics"]["violation_count"] = 999
    first.output["evidence"]["artifact_digests"][0]["name"] = "mutated"
    first.output["evidence"]["trace_preview"][0]["source_row_refs"].append("mutated")
    third = adapter.invoke(CASE)
    assert second.output["evidence"]["metrics"]["violation_count"] == 7
    assert third.output == second.output
    assert (
        third.output["evidence"]["trace_preview"][0]["source_row_refs"]
        is not second.output["evidence"]["trace_preview"][0]["source_row_refs"]
    )
    serialized = json.dumps(first.output, sort_keys=True)
    for forbidden in ("/home/", "account_id", "api_key", "private_key", "trades.csv"):
        assert forbidden not in serialized.lower()


def test_adapter_rejects_changed_evidence_even_with_updated_file_and_blob_pins(
    tmp_path: Path,
) -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    evidence["metrics"]["violation_count"] = 8
    evidence_path = tmp_path / "eval-evidence.json"
    evidence_bytes = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    evidence_path.write_bytes(evidence_bytes)

    provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    provenance["evidence"]["sha256"] = hashlib.sha256(evidence_bytes).hexdigest()
    provenance["source"]["git_blob_sha1"] = _git_blob_sha1(evidence_bytes)
    provenance_path = tmp_path / "provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(TraderRiskAuditEvidenceError, match="content hash is invalid"):
        TraderRiskAuditEvidenceAdapter(
            evidence_path=evidence_path,
            provenance_path=provenance_path,
        )


def test_adapter_rejects_evidence_bytes_that_do_not_match_provenance(tmp_path: Path) -> None:
    evidence_path = tmp_path / "eval-evidence.json"
    evidence_path.write_bytes(EVIDENCE.read_bytes() + b"\n")

    with pytest.raises(TraderRiskAuditEvidenceError, match="provenance SHA-256"):
        TraderRiskAuditEvidenceAdapter(
            evidence_path=evidence_path,
            provenance_path=PROVENANCE,
        )


@pytest.mark.parametrize(
    "case",
    [
        {"id": "synthetic-quickstart-v1", "input": {}},
        {
            "id": "synthetic-quickstart-v1",
            "input": {
                "evidence_case_id": "synthetic-quickstart-v1",
                "evidence_path": "/tmp/override.json",
            },
        },
        {
            "id": "synthetic-quickstart-v1",
            "input": {"evidence_case_id": "different-case"},
        },
    ],
)
def test_adapter_rejects_dataset_control_over_configured_evidence(case: dict[str, object]) -> None:
    with pytest.raises(UnsafeAdapterInputError):
        _adapter().invoke(case)


def _adapter() -> TraderRiskAuditEvidenceAdapter:
    return TraderRiskAuditEvidenceAdapter(
        evidence_path=EVIDENCE,
        provenance_path=PROVENANCE,
    )


def _git_blob_sha1(value: bytes) -> str:
    return hashlib.sha1(f"blob {len(value)}\0".encode() + value, usedforsecurity=False).hexdigest()
