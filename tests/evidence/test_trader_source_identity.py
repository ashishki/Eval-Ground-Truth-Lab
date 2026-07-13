from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab.trader_source_identity import (
    TraderSourceIdentityProofError,
    verify_trader_source_identity_proof,
)

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_ROOT = ROOT / "src/eval_ground_truth_lab/resources/trader_risk_audit"
EVIDENCE = RESOURCE_ROOT / "eval-evidence.json"
PROOF = RESOURCE_ROOT / "synthetic_quickstart_v1.git-proof.json"


def test_packaged_source_proof_binds_commit_tree_path_and_blob() -> None:
    identity = verify_trader_source_identity_proof(
        proof_bytes=PROOF.read_bytes(),
        evidence_bytes=EVIDENCE.read_bytes(),
    )

    assert identity.to_mapping() == {
        "proof_sha256": "0eee8d88dbc8b1ece4b4992aa3103718583b9c46124c5fbb4cdce84aced0ec21",
        "source_bundle_sha256": (
            "2c5b36afa9b2a9847de1c97789c52c57600e1d38cfd4947458906ee3bb3992ca"
        ),
        "source_git_blob_sha1": "9a64dc98e8edbe1ec39756611a6cb3b73b4994b9",
        "source_git_commit": "bf755a24450ff7c17328fa6d447f36bea8ea0fe5",
        "source_git_tree": "1a2c4ff91a7504642a1bae05a9487fa2e898e0b6",
        "source_path": "examples/synthetic_quickstart/evidence_preview/eval-evidence.json",
    }


@pytest.mark.parametrize("binding", ["commit", "tree", "path", "blob"])
def test_source_proof_rejects_each_altered_identity_binding(binding: str) -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    if binding == "commit":
        proof["commit"]["oid"] = "0" * 40
    elif binding == "tree":
        proof["trees"][0]["oid"] = "0" * 40
    elif binding == "path":
        proof["source_path"] = "examples/synthetic_quickstart/other.json"
    else:
        proof["blob_oid"] = "0" * 40

    with pytest.raises(TraderSourceIdentityProofError):
        verify_trader_source_identity_proof(
            proof_bytes=(json.dumps(proof, sort_keys=True) + "\n").encode(),
            evidence_bytes=EVIDENCE.read_bytes(),
        )
