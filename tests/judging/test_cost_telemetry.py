from __future__ import annotations

import json

from eval_ground_truth_lab.judging import (
    JsonlTelemetrySink,
    JudgeConfig,
    JudgeProviderResult,
    JudgeRequest,
    JudgeRunner,
)


def test_judge_call_emits_required_telemetry_fields(tmp_path) -> None:
    telemetry_path = tmp_path / "ai_cost_telemetry.jsonl"

    def provider(request: JudgeRequest) -> JudgeProviderResult:
        return JudgeProviderResult(
            score=0.55,
            explanation=f"Scored {request.case_id}",
            input_tokens=120,
            output_tokens=30,
            estimated_cost_usd=0.04,
            latency_ms=95.0,
            model="judge-small",
            quality_outcome="ambiguous",
        )

    runner = JudgeRunner(
        config=JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=2.00,
            cost_per_call_estimate_usd=0.04,
            project="eval-ground-truth-lab",
            workflow="subjective-eval",
            role="rubric-judge",
            model="judge-small",
            environment="test",
        ),
        provider=provider,
        telemetry_sink=JsonlTelemetrySink(telemetry_path),
    )

    runner.judge_case(
        case_id="case-telemetry",
        candidate_output={"answer": "maybe"},
        rubric_version="rubric-v1",
        retry_count=1,
    )
    entry = json.loads(telemetry_path.read_text(encoding="utf-8").splitlines()[0])

    assert entry["project"] == "eval-ground-truth-lab"
    assert entry["workflow"] == "subjective-eval"
    assert entry["role"] == "rubric-judge"
    assert entry["model"] == "judge-small"
    assert entry["environment"] == "test"
    assert entry["input_tokens"] == 120
    assert entry["output_tokens"] == 30
    assert entry["total_tokens"] == 150
    assert entry["estimated_cost_usd"] == 0.04
    assert entry["latency_ms"] == 95.0
    assert entry["retry_count"] == 1
    assert entry["tool_call_count"] == "n/a"
    assert entry["quality_outcome"] == "ambiguous"
