from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.judging.config import JudgeConfig
from eval_ground_truth_lab.judging.telemetry import CostTelemetryEntry, JsonlTelemetrySink


class JudgeError(RuntimeError):
    """Base error for optional judge failures."""


class JudgeDisabledError(JudgeError):
    """Raised when judge mode is requested without required config."""


class BudgetExceededError(JudgeError):
    """Raised before a judge call that would exceed the configured budget."""


@dataclass(frozen=True)
class JudgeRequest:
    case_id: str
    candidate_output: Any
    rubric_version: str


@dataclass(frozen=True)
class JudgeProviderResult:
    score: float
    explanation: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    model: str
    quality_outcome: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 1:
            raise ValueError("score must be between 0 and 1")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("token counts must be non-negative")
        if self.estimated_cost_usd < 0:
            raise ValueError("estimated_cost_usd must be non-negative")
        if self.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")


class JudgeRunner:
    def __init__(
        self,
        *,
        config: JudgeConfig,
        provider: Callable[[JudgeRequest], JudgeProviderResult],
        telemetry_sink: JsonlTelemetrySink,
    ) -> None:
        self.config = config
        self._provider = provider
        self._telemetry_sink = telemetry_sink
        self._spent_usd = 0.0
        self._call_count = 0

    @property
    def spent_usd(self) -> float:
        return self._spent_usd

    @property
    def call_count(self) -> int:
        return self._call_count

    def judge_case(
        self,
        *,
        case_id: str,
        candidate_output: Any,
        rubric_version: str,
        retry_count: int = 0,
    ) -> JudgeProviderResult:
        if not self.config.enabled:
            raise JudgeDisabledError(
                "Judge mode requires provider credentials and a positive budget"
            )
        if retry_count > self.config.max_retries:
            raise ValueError("retry_count exceeds configured max_retries")
        self._ensure_budget_available()

        request = JudgeRequest(
            case_id=case_id,
            candidate_output=candidate_output,
            rubric_version=rubric_version,
        )
        result = self._provider(request)
        self._spent_usd += result.estimated_cost_usd
        self._call_count += 1
        self._telemetry_sink.emit(
            CostTelemetryEntry(
                project=self.config.project,
                workflow=self.config.workflow,
                role=self.config.role,
                model=result.model or self.config.model,
                environment=self.config.environment,
                case_id=case_id,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                estimated_cost_usd=result.estimated_cost_usd,
                latency_ms=result.latency_ms,
                retry_count=retry_count,
                tool_call_count="n/a",
                quality_outcome=result.quality_outcome,
            )
        )
        return result

    def _ensure_budget_available(self) -> None:
        assert self.config.per_run_budget_usd is not None
        projected = self._spent_usd + self.config.cost_per_call_estimate_usd
        if projected > self.config.per_run_budget_usd:
            raise BudgetExceededError(
                f"Projected judge spend {projected:.6g} exceeds budget "
                f"{self.config.per_run_budget_usd:.6g}"
            )
