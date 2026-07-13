from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab.datasets import load_dataset
from eval_ground_truth_lab.evidence import sha256_file

ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = ROOT / "datasets/trader_risk_audit"


def test_trader_dataset_manifest_matches_committed_inputs() -> None:
    manifest = _json(DATASET_ROOT / "manifest.json")
    dataset_path = DATASET_ROOT / str(manifest["dataset_file"])
    evidence_path = DATASET_ROOT / str(manifest["evidence_file"])
    provenance_path = DATASET_ROOT / str(manifest["provenance_file"])
    dataset = load_dataset(dataset_path)

    assert manifest["case_count"] == dataset.metadata.case_count == 1
    assert manifest["dataset_hash"] == dataset.metadata.dataset_hash
    assert manifest["dataset_raw_sha256"] == sha256_file(dataset_path)
    assert manifest["evidence_sha256"] == sha256_file(evidence_path)
    assert manifest["provenance_sha256"] == sha256_file(provenance_path)


def test_trader_adapter_docs_preserve_product_and_evidence_boundaries() -> None:
    docs = " ".join(
        "\n".join(
            [
                (ROOT / "README.md").read_text(encoding="utf-8"),
                (ROOT / "docs/TRADER_RISK_AUDIT_ADAPTER.md").read_text(encoding="utf-8"),
                (ROOT / "docs/KNOWN_LIMITS.md").read_text(encoding="utf-8"),
                (DATASET_ROOT / "synthetic_quickstart_v1_CARD.md").read_text(encoding="utf-8"),
            ]
        )
        .lower()
        .split()
    )

    for required in (
        "separate applied fintech",
        "fully synthetic",
        "external workflow owners represented: `0`",
        "not a financial-performance",
        "not authenticate",
        "external adapter/case study",
    ):
        assert required in docs
    for forbidden in ("production-ready", "customer success", "validated by traders"):
        assert forbidden not in docs


def test_sanitized_fixture_contains_no_raw_paths_or_private_data_markers() -> None:
    fixture = (DATASET_ROOT / "fixtures/synthetic_quickstart_v1/eval-evidence.json").read_bytes()
    for forbidden in (
        b"/home/",
        b"/Users/",
        b"account_id",
        b"api_key",
        b"private_key",
        b"trades.csv",
        b"@gmail.com",
    ):
        assert forbidden.lower() not in fixture.lower()


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)
