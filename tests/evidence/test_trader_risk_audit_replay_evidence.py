from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval_ground_truth_lab import trader_replay as replay_module
from eval_ground_truth_lab.adapters import trader_risk_audit as adapter_module
from eval_ground_truth_lab.evidence import sha256_file, verify_evidence_manifest
from eval_ground_truth_lab.validators import trader_risk_audit as validator_module

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "docs/evidence/integrations/trader-risk-audit-synthetic-v1"
MANIFEST = PACK / (
    "sha256-c57f858899962179179109d33e165f0c8fbc3744c3cfaaffaea27e9179a0dd63.manifest.json"
)


def test_committed_trader_replay_pack_is_verified_and_pinned_to_current_code() -> None:
    verification = verify_evidence_manifest(MANIFEST)
    manifest = _json(MANIFEST)
    result = _json(PACK / "replay-result.json")

    assert verification.artifact_count == 7
    assert verification.content_address == (
        "sha256:c57f858899962179179109d33e165f0c8fbc3744c3cfaaffaea27e9179a0dd63"
    )
    assert result["gate"] == {"failed_validator_count": 0, "passed": True}
    assert result["dataset"]["dataset_hash"] == (
        "df201d0787c6ea31868f7f6465a2fb9895b6f14b78cb01e13e0f9ff244e5b67a"
    )
    expected_implementation = {
        "adapter": sha256_file(Path(adapter_module.__file__)),
        "runner": sha256_file(Path(replay_module.__file__)),
        "validators": sha256_file(Path(validator_module.__file__)),
    }
    assert result["provenance"]["implementation_sha256"] == expected_implementation
    assert manifest["metadata"]["implementation_sha256"] == expected_implementation
    assert manifest["metadata"]["source_git_commit"] == ("bf755a24450ff7c17328fa6d447f36bea8ea0fe5")
    assert manifest["metadata"]["source_git_tree"] == ("1a2c4ff91a7504642a1bae05a9487fa2e898e0b6")
    assert manifest["metadata"]["source_git_blob_sha1"] == (
        "9a64dc98e8edbe1ec39756611a6cb3b73b4994b9"
    )
    assert manifest["metadata"]["source_path"] == (
        "examples/synthetic_quickstart/evidence_preview/eval-evidence.json"
    )
    assert manifest["metadata"]["provenance_sha256"] == (
        "3cd4339892665f5ed0003856a4b251e7524733a4ce5c99fac834d84fcdf8e402"
    )


def test_committed_trader_run_seal_and_claim_boundary_are_intact() -> None:
    run_path = PACK / "run/trader-synthetic-quickstart-v1-20260713.json"
    seal_path = PACK / "run/trader-synthetic-quickstart-v1-20260713.sha256"
    expected_seal = f"sha256:{hashlib.sha256(run_path.read_bytes()).hexdigest()}  {run_path.name}"
    report = (PACK / "replay-report.md").read_text(encoding="utf-8").lower()

    assert seal_path.read_text(encoding="utf-8").strip() == expected_seal
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
