from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CostTelemetryEntry:
    project: str
    workflow: str
    role: str
    model: str
    environment: str
    case_id: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: float
    retry_count: int
    tool_call_count: int | str
    quality_outcome: str

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_mapping(self) -> dict[str, int | float | str]:
        return {
            "project": self.project,
            "workflow": self.workflow,
            "role": self.role,
            "model": self.model,
            "environment": self.environment,
            "case_id": self.case_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "tool_call_count": self.tool_call_count,
            "quality_outcome": self.quality_outcome,
        }


class JsonlTelemetrySink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, entry: CostTelemetryEntry) -> None:
        with self.path.open("a", encoding="utf-8") as telemetry_file:
            telemetry_file.write(json.dumps(entry.to_mapping(), sort_keys=True))
            telemetry_file.write("\n")
