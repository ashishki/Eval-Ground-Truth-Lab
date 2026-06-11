from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab.datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]


def test_v1_manifest_has_at_least_100_cases() -> None:
    manifest = _load_json("datasets/v1/manifest.json")
    dataset = load_dataset(ROOT / manifest["cases_path"])

    assert manifest["case_count"] >= 100
    assert dataset.metadata.case_count >= 100
    assert manifest["dataset_hash"] == dataset.metadata.dataset_hash


def test_seeded_regression_manifest_has_at_least_5_regressions() -> None:
    manifest = _load_json("datasets/v1/seeded_regressions.json")
    regressions = manifest["regressions"]

    assert len(regressions) >= 5
    assert all(regression["expected_failing_gate_ids"] for regression in regressions)
    assert {
        "unsafe_auto_approval_rate",
        "invalid_output_rate",
        "cost_per_case_delta",
        "accuracy_delta",
        "latency_ms_p95_delta",
    }.issubset(
        {
            gate_id
            for regression in regressions
            for gate_id in regression["expected_failing_gate_ids"]
        }
    )


def test_v1_report_links_required_ci_failures() -> None:
    report = (ROOT / "reports/v1/evidence_report.md").read_text(encoding="utf-8")

    for required_text in (
        "unsafe regression",
        "invalid structured output",
        "excessive cost increase",
        "material accuracy drop",
        ".github/workflows/ci.yml",
        "tests/eval/test_seeded_smoke_gate.py",
        "datasets/smoke/seeded_regressions.jsonl",
    ):
        assert required_text in report


def _load_json(path: str) -> dict[str, object]:
    with (ROOT / path).open(encoding="utf-8") as json_file:
        return json.load(json_file)
