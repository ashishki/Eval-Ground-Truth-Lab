from __future__ import annotations

import pytest

from eval_ground_truth_lab.judging import (
    JsonlTelemetrySink,
    JudgeConfig,
    JudgeDisabledError,
    JudgeProviderResult,
    JudgeRequest,
    JudgeRunner,
)


def test_judge_disabled_without_credentials_or_budget(tmp_path) -> None:
    def provider(_: JudgeRequest) -> JudgeProviderResult:
        raise AssertionError("provider must not be called when judge is disabled")

    disabled_configs = [
        JudgeConfig(
            provider_api_key=None,
            per_run_budget_usd=2.00,
            cost_per_call_estimate_usd=0.01,
        ),
        JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=None,
            cost_per_call_estimate_usd=0.01,
        ),
        JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=0.0,
            cost_per_call_estimate_usd=0.01,
        ),
    ]

    for config in disabled_configs:
        runner = JudgeRunner(
            config=config,
            provider=provider,
            telemetry_sink=JsonlTelemetrySink(tmp_path / "telemetry.jsonl"),
        )
        with pytest.raises(JudgeDisabledError):
            runner.judge_case(
                case_id="case-001",
                candidate_output={},
                rubric_version="rubric-v1",
            )


def test_judge_config_rejects_non_positive_cost_reservation() -> None:
    with pytest.raises(ValueError, match="cost_per_call_estimate_usd"):
        JudgeConfig(
            provider_api_key="test-key",
            per_run_budget_usd=2.00,
            cost_per_call_estimate_usd=0.0,
        )
