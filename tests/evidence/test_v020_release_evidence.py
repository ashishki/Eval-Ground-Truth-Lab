from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab.evidence import verify_evidence_manifest

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/evidence/releases/v0.2.0"
PACK = RELEASE / "gdev-agent-challenge"
MANIFEST = PACK / (
    "sha256-656face21f27b496d4d3e8bb0b588824f5737d122c1275c710f3e5b15ff94b4b.manifest.json"
)


def test_v020_canonical_failed_challenge_is_verified_and_reconciled() -> None:
    verification = verify_evidence_manifest(MANIFEST)
    result = _json(PACK / "challenge-run.json")
    manifest = _json(MANIFEST)

    assert verification.artifact_count == 4
    assert verification.content_address == (
        "sha256:656face21f27b496d4d3e8bb0b588824f5737d122c1275c710f3e5b15ff94b4b"
    )
    assert result["gate"]["passed"] is False
    assert set(result["gate"]["failed_thresholds"]) == {
        "blocking_failure_count_max",
        "classification_accuracy_min",
        "human_escalation_recall_min",
        "human_review_required_count_min",
        "unexpected_fail_count_max",
    }
    assert result["metrics"]["total_case_count"] == 100
    assert result["metrics"]["candidate_scope_case_count"] == 90
    assert result["metrics"]["expected_failure_case_count"] == 10
    assert result["metrics"]["expected_failure_matched"] == 1.0
    assert result["metrics"]["unexpected_fail_count"] == 68
    assert result["metrics"]["blocking_failure_count"] == 58
    assert result["metrics"]["classification_accuracy"] == pytest.approx(0.2444444444)
    assert result["metrics"]["human_escalation_recall"] == 0.46

    provenance = result["provenance"]
    assert provenance["fixture"] is False
    assert provenance["component_worktree_state"] == "clean"
    assert provenance["component_revision"] == ("0e4c5f0fd50382bbf12ffd35cfca4632384fb0cc")
    assert provenance["component_image_digest"] == (
        "sha256:7dc9fef2ec6fe25745405546ec69f6a6f64c1bfa9f052dc54abfd65498a6f6da"
    )
    namespace = provenance["request_namespace"]
    assert namespace["adapter_mode"] == "gdev_http_namespaced"
    assert namespace["applied"] is True
    assert namespace["applied_fields"] == ["message_id", "request_id"]
    assert namespace["context"]["dataset_hash"] == result["dataset"]["dataset_hash"]
    assert manifest["metadata"]["request_namespace"] == namespace
    assert manifest["metadata"]["gate_passed"] is False


def test_v020_release_docs_preserve_failure_and_public_dataset_boundary() -> None:
    release_readme = (RELEASE / "README.md").read_text(encoding="utf-8")
    dataset_card = (ROOT / "datasets/gdev_agent/challenge_v1_CARD.md").read_text(encoding="utf-8")
    protocol = (ROOT / "docs/GDEV_AGENT_BENCHMARK_PROTOCOL.md").read_text(encoding="utf-8")
    review = (ROOT / "docs/HUMAN_REVIEW.md").read_text(encoding="utf-8")

    for required in (
        "gate FAIL",
        "68",
        "58",
        "not a blind holdout",
        "does not establish",
        "not a feedback-driven maintenance release",
    ):
        assert required.lower() in release_readme.lower()

    assert "public development diagnostic" in dataset_card
    assert "Independent annotators | `0`" in dataset_card
    assert "External workflow owners represented | `0`" in dataset_card
    assert "Freeze-before-run contract" in protocol
    assert "Leakage and contamination controls" in protocol
    assert "independent_annotator_count=0" in protocol
    assert "no independent annotator" in review
    assert "human_review_required=true" in review


def test_v020_evidence_has_no_absolute_workstation_or_secret_markers() -> None:
    forbidden = (
        b"/home/",
        b"/Users/",
        b"OPENAI_API_KEY",
        b"ANTHROPIC_API_KEY",
        b"MISTRAL_API_KEY",
        b"audit-owner-local-only",
        b"audit-app-local-only",
    )

    for path in PACK.rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            assert not any(marker in raw for marker in forbidden), path


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)
