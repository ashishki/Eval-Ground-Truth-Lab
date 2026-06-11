from __future__ import annotations

from eval_ground_truth_lab.reports import REQUIRED_FAILURE_LABELS


def test_required_taxonomy_labels_present() -> None:
    assert {
        "unsafe_auto_approval",
        "invalid_structured_output",
        "missing_evidence",
        "low_confidence",
        "accuracy_regression",
        "cost_regression",
        "latency_regression",
    }.issubset(REQUIRED_FAILURE_LABELS)
