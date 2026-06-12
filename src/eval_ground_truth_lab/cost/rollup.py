from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class CostRollupError(ValueError):
    """Raised when telemetry JSONL cannot be rolled up deterministically."""


def rollup_telemetry(path: str | Path) -> dict[str, Any]:
    entries = _load_entries(Path(path))
    cost_by_model: dict[str, float] = defaultdict(float)
    cost_by_workflow: dict[str, float] = defaultdict(float)
    cost_by_case: dict[str, float] = defaultdict(float)
    quality_outcomes: Counter[str] = Counter()
    latencies: list[float] = []

    total_cost = 0.0
    total_tokens = 0
    retry_count = 0

    for entry in entries:
        cost = _number(entry, "estimated_cost_usd")
        total_cost += cost
        total_tokens += _total_tokens(entry)
        retry_count += int(_number(entry, "retry_count"))
        latencies.append(_number(entry, "latency_ms"))

        model = _string(entry, "model")
        workflow = _string(entry, "workflow")
        case_id = _string(entry, "case_id")
        quality_outcome = _string(entry, "quality_outcome")

        cost_by_model[model] += cost
        cost_by_workflow[workflow] += cost
        cost_by_case[case_id] += cost
        quality_outcomes[quality_outcome] += 1

    return {
        "entry_count": len(entries),
        "judge_call_count": len(entries),
        "total_cost_usd": _round_cost(total_cost),
        "total_tokens": total_tokens,
        "cost_by_model": _round_mapping(cost_by_model),
        "cost_by_workflow": _round_mapping(cost_by_workflow),
        "cost_by_case": _round_mapping(cost_by_case),
        "latency_p95": _percentile(latencies, 0.95),
        "retry_count": retry_count,
        "quality_outcome_distribution": dict(sorted(quality_outcomes.items())),
    }


def _load_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as telemetry_file:
        for line_number, line in enumerate(telemetry_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise CostRollupError(
                    f"Telemetry line {line_number} is not valid JSON: {exc.msg}"
                ) from exc
            if not isinstance(raw, dict):
                raise CostRollupError(f"Telemetry line {line_number} must be a JSON object")
            entries.append(raw)
    return entries


def _total_tokens(entry: dict[str, Any]) -> int:
    total_tokens = entry.get("total_tokens")
    if isinstance(total_tokens, int) and not isinstance(total_tokens, bool):
        return total_tokens
    return int(_number(entry, "input_tokens") + _number(entry, "output_tokens"))


def _number(entry: dict[str, Any], field: str) -> float:
    value = entry.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CostRollupError(f"Telemetry field {field!r} must be numeric")
    return float(value)


def _string(entry: dict[str, Any], field: str) -> str:
    value = entry.get(field)
    if not isinstance(value, str) or not value:
        raise CostRollupError(f"Telemetry field {field!r} must be a non-empty string")
    return value


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _round_mapping(values: dict[str, float]) -> dict[str, float]:
    return {key: _round_cost(value) for key, value in sorted(values.items())}


def _round_cost(value: float) -> float:
    return round(value, 10)
