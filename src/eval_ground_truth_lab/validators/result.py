from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eval_ground_truth_lab.execution_binding import EXECUTION_BINDING_SHA256

LOADED_EXECUTION_BINDING_SHA256 = EXECUTION_BINDING_SHA256


@dataclass(frozen=True)
class ValidationResult:
    case_id: str
    validator_id: str
    passed: bool
    category: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
