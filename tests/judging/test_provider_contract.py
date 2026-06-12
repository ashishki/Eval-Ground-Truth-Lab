from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval_ground_truth_lab.judging import (
    BudgetExceededError,
    JsonlTelemetrySink,
    JudgeConfig,
    JudgeDisabledError,
    JudgeRequest,
    JudgeRunner,
    final_case_decision,
)
from eval_ground_truth_lab.judging.providers import (
    OpenAIJudgeProvider,
    OpenAIJudgeProviderConfig,
)
from eval_ground_truth_lab.review import HumanReviewQueue


def test_provider_disabled_without_api_key_or_budget(tmp_path: Path) -> None:
    provider = _provider_that_must_not_be_called()
    disabled_configs = [
        JudgeConfig(
            provider_api_key=None,
            per_run_budget_usd=1.0,
            cost_per_call_estimate_usd=0.01,
        ),
        JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=0.0,
            cost_per_call_estimate_usd=0.01,
        ),
    ]

    assert OpenAIJudgeProviderConfig.from_environment({}) is None
    for config in disabled_configs:
        runner = JudgeRunner(
            config=config,
            provider=provider,
            telemetry_sink=JsonlTelemetrySink(tmp_path / "telemetry.jsonl"),
        )
        with pytest.raises(JudgeDisabledError):
            runner.judge_case(
                case_id="judge-disabled-001",
                candidate_output={},
                rubric_version="judge-rubric-v1",
            )


def test_provider_uses_structured_output_contract() -> None:
    captured: dict[str, Any] = {}
    provider = OpenAIJudgeProvider(
        _openai_config(),
        transport=_fake_openai_transport(captured=captured),
    )

    result = provider(
        JudgeRequest(
            case_id="judge-ambiguous-001",
            candidate_output={"answer": "maybe"},
            rubric_version="judge-rubric-v1",
        )
    )

    payload = captured["payload"]
    assert captured["api_key"] == "test-openai-key"
    assert payload["response_format"]["type"] == "json_schema"
    schema = payload["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert set(schema["schema"]["required"]) == {"score", "explanation", "quality_outcome"}
    assert result.score == 0.55
    assert result.explanation == "Ambiguous enough for human review."
    assert result.input_tokens == 100
    assert result.output_tokens == 20
    assert result.estimated_cost_usd == pytest.approx(0.0014)
    assert result.model == "gpt-4o-mini"
    assert result.quality_outcome == "ambiguous"


def test_budget_precheck_happens_before_provider_call(tmp_path: Path) -> None:
    calls: list[JudgeRequest] = []

    def provider(request: JudgeRequest):
        calls.append(request)
        raise AssertionError("provider must not run after failed budget precheck")

    runner = JudgeRunner(
        config=JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=0.005,
            cost_per_call_estimate_usd=0.01,
        ),
        provider=provider,
        telemetry_sink=JsonlTelemetrySink(tmp_path / "telemetry.jsonl"),
    )

    with pytest.raises(BudgetExceededError):
        runner.judge_case(
            case_id="judge-budget-001",
            candidate_output={},
            rubric_version="judge-rubric-v1",
        )

    assert calls == []


def test_provider_records_telemetry(tmp_path: Path) -> None:
    telemetry_path = tmp_path / "ai_cost_telemetry.jsonl"
    provider = OpenAIJudgeProvider(
        _openai_config(),
        transport=_fake_openai_transport(captured={}),
    )
    runner = JudgeRunner(
        config=JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=1.0,
            cost_per_call_estimate_usd=0.01,
            workflow="judge-provider-contract",
            model="gpt-4o-mini",
            environment="test",
        ),
        provider=provider,
        telemetry_sink=JsonlTelemetrySink(telemetry_path),
    )

    runner.judge_case(
        case_id="judge-telemetry-001",
        candidate_output={"answer": "maybe"},
        rubric_version="judge-rubric-v1",
        retry_count=1,
    )
    entry = json.loads(telemetry_path.read_text(encoding="utf-8").splitlines()[0])

    assert entry["input_tokens"] == 100
    assert entry["output_tokens"] == 20
    assert entry["total_tokens"] == 120
    assert entry["estimated_cost_usd"] == pytest.approx(0.0014)
    assert entry["latency_ms"] >= 0
    assert entry["retry_count"] == 1
    assert entry["model"] == "gpt-4o-mini"
    assert entry["quality_outcome"] == "ambiguous"


def test_judge_routes_ambiguous_cases_without_overriding_deterministic_failure(
    tmp_path: Path,
) -> None:
    provider = OpenAIJudgeProvider(
        _openai_config(),
        transport=_fake_openai_transport(captured={}),
    )
    runner = JudgeRunner(
        config=JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=1.0,
            cost_per_call_estimate_usd=0.01,
        ),
        provider=provider,
        telemetry_sink=JsonlTelemetrySink(tmp_path / "telemetry.jsonl"),
    )
    candidate_output = {"answer": "maybe"}

    judge_result = runner.judge_case(
        case_id="judge-ambiguous-001",
        candidate_output=candidate_output,
        rubric_version="judge-rubric-v1",
    )
    review_queue = HumanReviewQueue()
    review_item = review_queue.add_from_judge_result(
        case_id="judge-ambiguous-001",
        candidate_output=candidate_output,
        rubric_version="judge-rubric-v1",
        judge_result=judge_result,
    )
    decision = final_case_decision(
        deterministic_results=(
            {
                "validator_id": "gdev.unsafe_auto_approval",
                "passed": False,
                "category": "unsafe_auto_approval",
            },
        ),
        judge_result=judge_result,
    )

    assert judge_result.quality_outcome == "ambiguous"
    assert review_item.reviewer_status == "pending"
    assert review_queue.list_entries() == (review_item,)
    assert decision.passed is False
    assert decision.source == "deterministic"
    assert "cannot be overridden" in decision.reason


def _openai_config() -> OpenAIJudgeProviderConfig:
    return OpenAIJudgeProviderConfig(
        api_key="test-openai-key",
        input_cost_per_1k_tokens_usd=0.01,
        output_cost_per_1k_tokens_usd=0.02,
    )


def _fake_openai_transport(*, captured: dict[str, Any]):
    def transport(
        config: OpenAIJudgeProviderConfig,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        captured["api_key"] = config.api_key
        captured["payload"] = payload
        return {
            "model": config.model,
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "score": 0.55,
                                "explanation": "Ambiguous enough for human review.",
                                "quality_outcome": "ambiguous",
                            },
                            sort_keys=True,
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }

    return transport


def _provider_that_must_not_be_called():
    def provider(_request: JudgeRequest):
        raise AssertionError("provider must not be called")

    return provider
