from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab.cli import main
from eval_ground_truth_lab.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets/gdev_agent/triage_v1.jsonl"
MANIFEST_PATH = ROOT / "datasets/gdev_agent/manifest.json"
REQUIRED_SLICES = {
    "billing_refund",
    "account_access",
    "bug_report",
    "moderation_report",
    "legal_gdpr",
    "low_confidence",
    "prompt_injection",
    "unsafe_url",
    "secret_leak_attempt",
    "duplicate_webhook",
    "cross_tenant_boundary",
}
REQUIRED_INPUT_FIELDS = {"tenant_slug", "message_id", "user_id", "text"}
REQUIRED_EXPECTED_FIELDS = {
    "category",
    "requires_human",
    "expected_status",
    "guard_behavior",
    "unsafe_auto_approval_allowed",
}
REQUIRED_METADATA_FIELDS = {"slice", "risk", "synthetic"}


def test_gdev_agent_dataset_has_50_unique_synthetic_cases() -> None:
    dataset = load_dataset(DATASET_PATH)
    case_ids = [case.id for case in dataset.cases]

    assert dataset.metadata.case_count >= 50
    assert len(case_ids) == len(set(case_ids))
    assert all(case.metadata["synthetic"] is True for case in dataset.cases)


def test_gdev_agent_dataset_case_shape() -> None:
    dataset = load_dataset(DATASET_PATH)

    for case in dataset.cases:
        assert REQUIRED_INPUT_FIELDS.issubset(case.input)
        assert REQUIRED_EXPECTED_FIELDS.issubset(case.expected)
        assert REQUIRED_METADATA_FIELDS.issubset(case.metadata)
        assert isinstance(case.input["text"], str) and case.input["text"].strip()
        assert case.input["tenant_slug"].startswith("test-tenant-")
        assert case.input["message_id"].startswith("eval-")
        assert case.input["user_id"].startswith("eval-user-")


def test_gdev_agent_dataset_slice_coverage() -> None:
    dataset = load_dataset(DATASET_PATH)
    observed_slices = {case.metadata["slice"] for case in dataset.cases}

    assert REQUIRED_SLICES.issubset(observed_slices)


def test_gdev_agent_manifest_hash_matches_dataset(capsys) -> None:
    manifest = _load_manifest()
    dataset = load_dataset(DATASET_PATH)

    assert manifest["case_count"] == dataset.metadata.case_count
    assert manifest["dataset_hash"] == dataset.metadata.dataset_hash
    assert manifest["cases_path"] == "datasets/gdev_agent/triage_v1.jsonl"

    exit_code = main(["dataset-inspect", "--dataset", str(DATASET_PATH)])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["case_count"] == manifest["case_count"]
    assert output["dataset_hash"] == manifest["dataset_hash"]
    assert output["dataset_id"] == manifest["dataset_id"]


def test_gdev_agent_dataset_contains_no_real_data() -> None:
    raw_text = DATASET_PATH.read_text(encoding="utf-8").lower()
    forbidden_markers = (
        "sk-",
        "api_key",
        "bearer ",
        "password",
        "private key",
        "customer@example.com",
        "real-user",
    )
    dataset = load_dataset(DATASET_PATH)

    assert not any(marker in raw_text for marker in forbidden_markers)
    assert all(case.metadata["synthetic"] is True for case in dataset.cases)


def _load_manifest() -> dict[str, object]:
    with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)
