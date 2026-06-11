from __future__ import annotations

from eval_ground_truth_lab.compare import ComparisonReport


def comparison_exit_code(report: ComparisonReport) -> int:
    return 1 if report.has_blocking_failure else 0
