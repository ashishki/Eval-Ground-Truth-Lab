from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.judging.runner import JudgeProviderResult


@dataclass(frozen=True)
class FinalDecision:
    passed: bool
    source: str
    reason: str


def final_case_decision(
    *,
    deterministic_results: tuple[dict[str, Any], ...],
    judge_result: JudgeProviderResult | None,
    judge_pass_threshold: float = 0.5,
) -> FinalDecision:
    blocking_failure = next(
        (result for result in deterministic_results if result.get("passed") is False),
        None,
    )
    if blocking_failure is not None:
        return FinalDecision(
            passed=False,
            source="deterministic",
            reason=(
                "Deterministic validator failure cannot be overridden by judge: "
                f"{blocking_failure.get('validator_id', '<unknown>')}"
            ),
        )

    if judge_result is None:
        return FinalDecision(
            passed=True,
            source="deterministic",
            reason="No deterministic blocking failures and no judge result",
        )

    reason = (
        f"Judge score {judge_result.score:.3g} compared to threshold {judge_pass_threshold:.3g}"
    )
    return FinalDecision(
        passed=judge_result.score >= judge_pass_threshold,
        source="judge",
        reason=reason,
    )
