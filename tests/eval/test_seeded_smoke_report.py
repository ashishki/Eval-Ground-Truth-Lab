from __future__ import annotations

from eval_ground_truth_lab.cli import main
from eval_ground_truth_lab.datasets import load_dataset


def test_seeded_report_links_required_evidence(tmp_path) -> None:
    report_path = tmp_path / "seeded-smoke.md"
    dataset = load_dataset("datasets/smoke/seeded_regressions.jsonl")

    exit_code = main(
        [
            "seeded-smoke",
            "--dataset",
            str(dataset.metadata.source_path),
            "--report",
            str(report_path),
        ]
    )

    report = report_path.read_text(encoding="utf-8")
    assert exit_code == 1
    assert dataset.metadata.dataset_hash in report
    assert "seeded-smoke-baseline-run.json" in report
    assert "seeded-smoke-candidate-run.json" in report
    assert "datasets/smoke/thresholds.json" in report
    assert "src/eval_ground_truth_lab/reports/taxonomy.py" in report
