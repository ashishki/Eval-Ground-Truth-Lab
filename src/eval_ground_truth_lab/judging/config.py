from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JudgeConfig:
    provider_api_key: str | None
    per_run_budget_usd: float | None
    cost_per_call_estimate_usd: float
    project: str = "eval-ground-truth-lab"
    workflow: str = "judge"
    role: str = "optional-rubric-judge"
    model: str = "cheap-structured-output-judge"
    environment: str = "local"
    max_retries: int = 1

    def __post_init__(self) -> None:
        if self.cost_per_call_estimate_usd <= 0:
            raise ValueError("cost_per_call_estimate_usd must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

    @property
    def enabled(self) -> bool:
        return (
            bool(self.provider_api_key)
            and self.per_run_budget_usd is not None
            and (self.per_run_budget_usd > 0)
        )
