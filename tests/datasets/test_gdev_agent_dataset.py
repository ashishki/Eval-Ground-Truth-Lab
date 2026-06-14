from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab.cli import main
from eval_ground_truth_lab.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "datasets/gdev_agent/triage_v1.jsonl"
CHALLENGE_DATASET_PATH = ROOT / "datasets/gdev_agent/challenge_v1.jsonl"
CHALLENGE_MANIFEST_PATH = ROOT / "datasets/gdev_agent/challenge_manifest.json"
CHALLENGE_THRESHOLDS_PATH = ROOT / "datasets/gdev_agent/challenge_thresholds.json"
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
REQUIRED_CHALLENGE_SLICES = {
    "ambiguous_multi_intent",
    "refund_pressure",
    "account_takeover",
    "moderation_edge",
    "legal_privacy",
    "obfuscated_injection",
    "unsafe_link_social",
    "cross_tenant_escalation",
    "malformed_user_input",
    "provider_error_simulation",
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
REQUIRED_CHALLENGE_METADATA_FIELDS = {
    "challenge_type",
    "expected_failure",
    "human_review_required",
    *REQUIRED_METADATA_FIELDS,
}


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


def test_gdev_agent_challenge_dataset_shape_and_slices(capsys) -> None:
    dataset = load_dataset(CHALLENGE_DATASET_PATH)
    case_ids = [case.id for case in dataset.cases]
    observed_slices = {case.metadata["slice"] for case in dataset.cases}

    assert dataset.metadata.case_count == 100
    assert len(case_ids) == len(set(case_ids))
    assert REQUIRED_CHALLENGE_SLICES == observed_slices
    assert sum(case.metadata["expected_failure"] is True for case in dataset.cases) == 10
    assert all(case.metadata["human_review_required"] is True for case in dataset.cases)

    exit_code = main(["dataset-inspect", "--dataset", str(CHALLENGE_DATASET_PATH)])
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["dataset_id"] == "challenge_v1"
    assert output["case_count"] == 100
    assert output["dataset_hash"] == dataset.metadata.dataset_hash


def test_gdev_agent_challenge_dataset_case_shape() -> None:
    dataset = load_dataset(CHALLENGE_DATASET_PATH)

    for case in dataset.cases:
        assert REQUIRED_INPUT_FIELDS.issubset(case.input)
        assert REQUIRED_EXPECTED_FIELDS.issubset(case.expected)
        assert REQUIRED_CHALLENGE_METADATA_FIELDS.issubset(case.metadata)
        assert case.input["message_id"].startswith("challenge-")
        assert case.input["user_id"].startswith("challenge-user-")
        assert case.input["tenant_slug"].startswith("test-tenant-")
        assert case.metadata["synthetic"] is True


def test_gdev_agent_challenge_manifest_hash_matches_dataset() -> None:
    dataset = load_dataset(CHALLENGE_DATASET_PATH)
    with CHALLENGE_MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)

    assert manifest["case_count"] == dataset.metadata.case_count
    assert manifest["dataset_hash"] == dataset.metadata.dataset_hash
    assert manifest["cases_path"] == "datasets/gdev_agent/challenge_v1.jsonl"
    assert manifest["threshold_config"] == "datasets/gdev_agent/challenge_thresholds.json"
    assert set(manifest["slices"]) == REQUIRED_CHALLENGE_SLICES


def test_gdev_agent_challenge_thresholds_are_diagnostic() -> None:
    with CHALLENGE_THRESHOLDS_PATH.open(encoding="utf-8") as thresholds_file:
        thresholds = json.load(thresholds_file)

    assert thresholds["version"] == "gdev-agent-challenge-thresholds-v1"
    assert thresholds["expected_failure_matched_min"] > 0
    assert thresholds["unexpected_fail_count_max"] > 0
    assert thresholds["human_review_required_count_min"] >= 80
    assert thresholds["max_unsafe_auto_approval_rate"] == 0.0


def test_gdev_agent_challenge_docs_and_report_are_linked() -> None:
    challenge_doc = (ROOT / "docs/GDEV_AGENT_CHALLENGE_SET.md").read_text(encoding="utf-8")
    report = (ROOT / "reports/gdev-agent/challenge_report.md").read_text(encoding="utf-8")
    evidence_index = (ROOT / "docs/EVIDENCE_INDEX.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for required_text in (
        "datasets/gdev_agent/challenge_v1.jsonl",
        "datasets/gdev_agent/challenge_manifest.json",
        "expected_failure_matched",
        "unexpected_pass_count",
        "human_review_required_count",
        "not a passing baseline",
    ):
        assert required_text in challenge_doc
        assert required_text in report

    assert "docs/GDEV_AGENT_CHALLENGE_SET.md" in evidence_index
    assert "reports/gdev-agent/challenge_report.md" in evidence_index
    assert "challenge_report.md" in readme


def test_gdev_agent_challenge_dataset_contains_no_real_data() -> None:
    raw_text = CHALLENGE_DATASET_PATH.read_text(encoding="utf-8").lower()
    forbidden_markers = (
        "sk-",
        "api_key",
        "bearer ",
        "password",
        "private key",
        "customer@example.com",
        "real-user",
    )
    dataset = load_dataset(CHALLENGE_DATASET_PATH)

    assert not any(marker in raw_text for marker in forbidden_markers)
    assert all(case.metadata["synthetic"] is True for case in dataset.cases)


def _load_manifest() -> dict[str, object]:
    with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)
