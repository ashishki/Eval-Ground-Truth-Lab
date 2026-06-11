from __future__ import annotations

from eval_ground_truth_lab.cli import main


def test_seeded_unsafe_regression_fails_ci_gate(tmp_path) -> None:
    exit_code = main(
        [
            "seeded-smoke",
            "--dataset",
            "datasets/smoke/seeded_regressions.jsonl",
            "--report",
            str(tmp_path / "seeded-smoke.md"),
        ]
    )

    assert exit_code == 1
