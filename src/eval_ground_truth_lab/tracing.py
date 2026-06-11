from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    operation_name: str


def start_trace(operation_name: str) -> TraceContext:
    return TraceContext(trace_id=str(uuid4()), operation_name=operation_name)
