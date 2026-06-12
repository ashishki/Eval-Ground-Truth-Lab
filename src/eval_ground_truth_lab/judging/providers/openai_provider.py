from __future__ import annotations

import json
import os
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.judging.runner import JudgeProviderResult, JudgeRequest

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/chat/completions"
ALLOWED_QUALITY_OUTCOMES = frozenset({"pass", "ambiguous", "fail"})


class OpenAIJudgeProviderError(RuntimeError):
    """Raised when the OpenAI judge provider returns an invalid result."""


@dataclass(frozen=True)
class OpenAIJudgeProviderConfig:
    api_key: str
    model: str = "gpt-4o-mini"
    endpoint: str = OPENAI_RESPONSES_ENDPOINT
    timeout_seconds: float = 30.0
    input_cost_per_1k_tokens_usd: float = 0.0
    output_cost_per_1k_tokens_usd: float = 0.0

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> OpenAIJudgeProviderConfig | None:
        source = environ or os.environ
        api_key = source.get("OPENAI_API_KEY") or source.get("LLM_JUDGE_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            model=source.get("OPENAI_JUDGE_MODEL", "gpt-4o-mini"),
        )


OpenAITransport = Callable[[OpenAIJudgeProviderConfig, dict[str, Any]], dict[str, Any]]


class OpenAIJudgeProvider:
    def __init__(
        self,
        config: OpenAIJudgeProviderConfig,
        *,
        transport: OpenAITransport | None = None,
    ) -> None:
        self.config = config
        self._transport = transport or _default_transport

    def __call__(self, request: JudgeRequest) -> JudgeProviderResult:
        payload = self._build_payload(request)
        started = time.perf_counter()
        response = self._transport(self.config, payload)
        latency_ms = (time.perf_counter() - started) * 1000
        structured = _extract_structured_output(response)
        usage = _usage(response)
        input_tokens = _int_field(usage, "prompt_tokens")
        output_tokens = _int_field(usage, "completion_tokens")
        return JudgeProviderResult(
            score=_score(structured),
            explanation=_required_string(structured, "explanation"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimated_cost_usd(
                config=self.config,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
            latency_ms=latency_ms,
            model=str(response.get("model") or self.config.model),
            quality_outcome=_quality_outcome(structured),
        )

    def _build_payload(self, request: JudgeRequest) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a bounded eval judge. Score only the supplied "
                        "candidate output against the rubric. Deterministic "
                        "validators remain authoritative."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "case_id": request.case_id,
                            "rubric_version": request.rubric_version,
                            "candidate_output": request.candidate_output,
                        },
                        sort_keys=True,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "eval_judge_result",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                            },
                            "explanation": {"type": "string"},
                            "quality_outcome": {
                                "type": "string",
                                "enum": sorted(ALLOWED_QUALITY_OUTCOMES),
                            },
                        },
                        "required": ["score", "explanation", "quality_outcome"],
                    },
                },
            },
        }


def _default_transport(
    config: OpenAIJudgeProviderConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        config.endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise OpenAIJudgeProviderError("OpenAI response must be a JSON object")
    return parsed


def _extract_structured_output(response: Mapping[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenAIJudgeProviderError("OpenAI response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise OpenAIJudgeProviderError("OpenAI choice must be an object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise OpenAIJudgeProviderError("OpenAI choice missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise OpenAIJudgeProviderError("OpenAI message content must be a JSON string")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenAIJudgeProviderError("OpenAI structured output was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise OpenAIJudgeProviderError("OpenAI structured output must be a JSON object")
    return parsed


def _usage(response: Mapping[str, Any]) -> Mapping[str, Any]:
    usage = response.get("usage", {})
    if not isinstance(usage, Mapping):
        raise OpenAIJudgeProviderError("OpenAI usage must be an object")
    return usage


def _score(structured: Mapping[str, Any]) -> float:
    value = structured.get("score")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise OpenAIJudgeProviderError("OpenAI judge score must be numeric")
    score = float(value)
    if not 0 <= score <= 1:
        raise OpenAIJudgeProviderError("OpenAI judge score must be between 0 and 1")
    return score


def _quality_outcome(structured: Mapping[str, Any]) -> str:
    value = _required_string(structured, "quality_outcome")
    if value not in ALLOWED_QUALITY_OUTCOMES:
        raise OpenAIJudgeProviderError(f"Unknown OpenAI judge quality_outcome: {value}")
    return value


def _required_string(structured: Mapping[str, Any], field: str) -> str:
    value = structured.get(field)
    if not isinstance(value, str) or not value:
        raise OpenAIJudgeProviderError(f"OpenAI judge field {field!r} must be a string")
    return value


def _int_field(usage: Mapping[str, Any], field: str) -> int:
    value = usage.get(field, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise OpenAIJudgeProviderError(f"OpenAI usage field {field!r} must be an integer")
    if value < 0:
        raise OpenAIJudgeProviderError(f"OpenAI usage field {field!r} must be non-negative")
    return value


def _estimated_cost_usd(
    *,
    config: OpenAIJudgeProviderConfig,
    input_tokens: int,
    output_tokens: int,
) -> float:
    input_cost = (input_tokens / 1000) * config.input_cost_per_1k_tokens_usd
    output_cost = (output_tokens / 1000) * config.output_cost_per_1k_tokens_usd
    return round(input_cost + output_cost, 10)
