from __future__ import annotations

from eval_ground_truth_lab.judging import JudgeProviderResult, final_case_decision


def test_judge_cannot_override_blocking_validator() -> None:
    decision = final_case_decision(
        deterministic_results=(
            {
                "validator_id": "structured_output.required_fields",
                "passed": False,
                "category": "invalid_structured_output",
            },
        ),
        judge_result=JudgeProviderResult(
            score=1.0,
            explanation="Looks acceptable",
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.01,
            latency_ms=100.0,
            model="judge-small",
            quality_outcome="pass",
        ),
    )

    assert decision.passed is False
    assert decision.source == "deterministic"
    assert "cannot be overridden" in decision.reason
