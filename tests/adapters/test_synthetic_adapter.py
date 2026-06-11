from __future__ import annotations

from eval_ground_truth_lab.adapters import SyntheticDemoAdapter


def test_synthetic_adapter_is_deterministic() -> None:
    adapter = SyntheticDemoAdapter(
        {
            "case-001": {
                "category": "billing",
                "correct": True,
                "labels": ["refund"],
            }
        }
    )
    case = {"id": "case-001", "input": {"ticket": "Refund request"}}

    first = adapter.invoke(case)
    second = adapter.invoke(case)
    first.output["labels"].append("mutated")

    assert second.output == {
        "category": "billing",
        "correct": True,
        "labels": ["refund"],
    }
