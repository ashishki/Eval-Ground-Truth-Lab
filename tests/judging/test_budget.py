from __future__ import annotations

import pytest

from eval_ground_truth_lab.judging import (
    BudgetExceededError,
    JsonlTelemetrySink,
    JudgeConfig,
    JudgeProviderResult,
    JudgeRequest,
    JudgeRunner,
)


def test_judge_stops_before_budget_overrun(tmp_path) -> None:
    calls: list[JudgeRequest] = []

    def provider(request: JudgeRequest) -> JudgeProviderResult:
        calls.append(request)
        return JudgeProviderResult(
            score=0.7,
            explanation="Rubric matched",
            input_tokens=100,
            output_tokens=25,
            estimated_cost_usd=0.06,
            latency_ms=80.0,
            model="judge-small",
            quality_outcome="pass",
        )

    runner = JudgeRunner(
        config=JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=0.10,
            cost_per_call_estimate_usd=0.06,
        ),
        provider=provider,
        telemetry_sink=JsonlTelemetrySink(tmp_path / "telemetry.jsonl"),
    )

    runner.judge_case(case_id="case-001", candidate_output={}, rubric_version="rubric-v1")
    with pytest.raises(BudgetExceededError):
        runner.judge_case(case_id="case-002", candidate_output={}, rubric_version="rubric-v1")

    assert len(calls) == 1
    assert runner.spent_usd == 0.06
