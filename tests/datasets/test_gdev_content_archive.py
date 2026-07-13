from __future__ import annotations

import hashlib
import json
from pathlib import Path

from eval_ground_truth_lab.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets/gdev_content_archive/stub_cases_v1.jsonl"
MANIFEST_PATH = ROOT / "datasets/gdev_content_archive/manifest.json"
CARD_PATH = ROOT / "datasets/gdev_content_archive/stub_cases_v1_CARD.md"
SOURCE_REVISION = "44dd93760de2cccf0667f393d7c231bdfbbcabc0"
SOURCE_RAW_SHA256 = "b7f6e682af5157034da13682c11cd88fa82b4a3a9c34b593a6bba69dd664a34f"


def test_archived_stub_cases_have_exact_verified_scope() -> None:
    dataset = load_dataset(DATASET_PATH)

    assert dataset.metadata.case_count == 6
    assert [case.id for case in dataset.cases] == [
        "legacy-gdev-content-C-001",
        "legacy-gdev-content-C-002",
        "legacy-gdev-content-C-003",
        "legacy-gdev-content-C-004",
        "legacy-gdev-content-C-005",
        "legacy-gdev-content-C-NEG-001",
    ]
    assert sum(case.expected["pipeline_ok"] is False for case in dataset.cases) == 1
    assert all(case.metadata["synthetic"] is True for case in dataset.cases)
    assert all(case.metadata["source_revision"] == SOURCE_REVISION for case in dataset.cases)
    assert all(case.metadata["source_track"] == "deterministic_stub" for case in dataset.cases)


def test_archived_stub_manifest_matches_content() -> None:
    dataset = load_dataset(DATASET_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["case_count"] == dataset.metadata.case_count
    assert manifest["dataset_hash"] == dataset.metadata.dataset_hash
    assert manifest["dataset_raw_sha256"] == hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
    assert manifest["source_raw_sha256"] == SOURCE_RAW_SHA256
    assert manifest["source_revision"] == SOURCE_REVISION
    assert manifest["source_replay"]["expectation_match_rate"] == 1.0
    assert manifest["source_replay"]["provider"] == "stub"
    assert manifest["benchmark_status"] == "archive_only_not_release_gate"
    assert manifest["license"] == "Apache-2.0"


def test_archived_stub_card_preserves_limitations() -> None:
    card = CARD_PATH.read_text(encoding="utf-8")

    assert "20 `TC-*.json` LLM cases were not migrated" in card
    assert "not part of the canonical v0.2.0" in card
    assert "Real-user or production data | None claimed or observed" in card
    assert SOURCE_REVISION in card
    assert SOURCE_RAW_SHA256 in card
