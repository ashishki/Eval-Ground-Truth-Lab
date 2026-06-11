from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class AdapterError(RuntimeError):
    """Base error for candidate adapter failures."""


class UnsafeAdapterInputError(AdapterError):
    """Raised when eval case input attempts to control adapter execution."""


@dataclass(frozen=True)
class AdapterResult:
    output: Any
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    latency_ms: float = 0.0
    status_code: int | None = None
    trace_id: str | None = None
    operation_name: str | None = None
