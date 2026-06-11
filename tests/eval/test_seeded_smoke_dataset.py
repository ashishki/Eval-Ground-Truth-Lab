from __future__ import annotations

from eval_ground_truth_lab.datasets import load_dataset


def test_seeded_smoke_dataset_covers_blocking_regressions() -> None:
    dataset = load_dataset("datasets/smoke/seeded_regressions.jsonl")
    regression_classes = {case.metadata.get("blocking_regression_class") for case in dataset.cases}

    assert regression_classes == {
        "unsafe_auto_approval",
        "invalid_structured_output",
        "excessive_cost_increase",
        "material_accuracy_drop",
    }
