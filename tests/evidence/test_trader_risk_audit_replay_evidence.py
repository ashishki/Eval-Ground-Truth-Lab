from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval_ground_truth_lab import evidence as evidence_module
from eval_ground_truth_lab import trader_replay as replay_module
from eval_ground_truth_lab.adapters import trader_risk_audit as adapter_module
from eval_ground_truth_lab.datasets import registry as dataset_module
from eval_ground_truth_lab.evidence import verify_evidence_manifest
from eval_ground_truth_lab.implementation_provenance import build_implementation_provenance
from eval_ground_truth_lab.runs import store as run_store_module
from eval_ground_truth_lab.validators import trader_risk_audit as validator_module

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs/evidence/integrations/trader-risk-audit-synthetic-v1"
MANIFEST = PACK / (
    "sha256-05b2f18a78f5961f60d232d9626a471805123f78e4e46120db9c40111e2bd627.manifest.json"
)


def test_committed_trader_replay_pack_is_verified_and_pinned_to_current_code() -> None:
    verification = verify_evidence_manifest(MANIFEST)
    manifest = _json(MANIFEST)
    result = _json(PACK / "replay-result.json")

    assert verification.artifact_count == 8
    assert verification.content_address == (
        "sha256:05b2f18a78f5961f60d232d9626a471805123f78e4e46120db9c40111e2bd627"
    )
    assert result["gate"] == {"failed_validator_count": 0, "passed": True}
    assert result["dataset"]["dataset_hash"] == (
        "df201d0787c6ea31868f7f6465a2fb9895b6f14b78cb01e13e0f9ff244e5b67a"
    )
    measured = build_implementation_provenance(
        component_paths={
            "adapter": Path(adapter_module.__file__),
            "dataset_parser": Path(dataset_module.__file__),
            "evidence_manifest": Path(evidence_module.__file__),
            "run_store": Path(run_store_module.__file__),
            "runner": Path(replay_module.__file__),
            "validators": Path(validator_module.__file__),
        },
        package_root=Path(replay_module.__file__).parent,
    )
    implementation = result["provenance"]["implementation"]
    assert implementation["components_sha256"] == measured["components_sha256"]
    assert implementation["package_payload"] == measured["package_payload"]
    assert implementation["source"] == {
        "commit": "56de400bd4e157f70cf1538fbc464b9dbc00257b",
        "kind": "git_worktree",
        "tree": "1b265941e195f053915caa27089f1dd484b3a2c7",
        "worktree_clean": True,
    }
    assert manifest["metadata"]["implementation"] == implementation
    assert result["provenance"]["implementation_sha256"] == implementation["components_sha256"]
    assert manifest["metadata"]["implementation_sha256"] == implementation["components_sha256"]
    source = manifest["metadata"]["source_provenance"]
    assert source["source_identity"]["git_commit"] == ("bf755a24450ff7c17328fa6d447f36bea8ea0fe5")
    assert source["source_identity"]["git_tree"] == ("1a2c4ff91a7504642a1bae05a9487fa2e898e0b6")
    assert source["source_identity"]["git_blob_sha1"] == (
        "9a64dc98e8edbe1ec39756611a6cb3b73b4994b9"
    )
    assert source["source_identity"]["path"] == (
        "examples/synthetic_quickstart/evidence_preview/eval-evidence.json"
    )
    assert manifest["metadata"]["source_trust"]["reviewed"] is True
    assert manifest["metadata"]["source_trust"]["source_identity_verified"] is True
    assert (
        manifest["metadata"]["source_trust"]["source_identity_proof_sha256"]
        == "0eee8d88dbc8b1ece4b4992aa3103718583b9c46124c5fbb4cdce84aced0ec21"
    )
    assert (PACK / "inputs/source-identity-proof.json").read_bytes() == (
        ROOT
        / "src/eval_ground_truth_lab/resources/trader_risk_audit"
        / "synthetic_quickstart_v1.git-proof.json"
    ).read_bytes()
    assert manifest["metadata"]["provenance_sha256"] == (
        "3cd4339892665f5ed0003856a4b251e7524733a4ce5c99fac834d84fcdf8e402"
    )


def test_committed_trader_run_seal_and_claim_boundary_are_intact() -> None:
    run_path = PACK / "run/trader-synthetic-quickstart-v1-20260713.json"
    seal_path = PACK / "run/trader-synthetic-quickstart-v1-20260713.sha256"
    expected_seal = f"sha256:{hashlib.sha256(run_path.read_bytes()).hexdigest()}  {run_path.name}"
    report = (PACK / "replay-report.md").read_text(encoding="utf-8").lower()
    result = _json(PACK / "replay-result.json")
    manifest = _json(MANIFEST)

    assert seal_path.read_text(encoding="utf-8").strip() == expected_seal
    assert result["run"]["status"] == "completed"
    assert manifest["metadata"]["run"] == {
        field: result["run"][field]
        for field in (
            "candidate_version",
            "dataset_hash",
            "record_sha256",
            "run_id",
            "seal_sha256",
            "status",
            "validator_version",
        )
    }
    assert (
        manifest["metadata"]["run"]["record_sha256"]
        == hashlib.sha256(run_path.read_bytes()).hexdigest()
    )
    assert (
        manifest["metadata"]["run"]["seal_sha256"]
        == hashlib.sha256(seal_path.read_bytes()).hexdigest()
    )
    for required in (
        "fully synthetic",
        "not a financial-performance evaluation",
        "external-user case study",
        "does not validate suitable risk thresholds",
    ):
        assert required in report


def test_committed_trader_replay_pack_has_no_workstation_or_secret_markers() -> None:
    forbidden = (
        b"/home/",
        b"/Users/",
        b"OPENAI_API_KEY",
        b"ANTHROPIC_API_KEY",
        b"BEGIN PRIVATE KEY",
        b"account_id",
        b"api_key",
        b"private_key",
        b"trades.csv",
    )
    for path in PACK.rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            assert not any(marker.lower() in raw.lower() for marker in forbidden), path


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)
