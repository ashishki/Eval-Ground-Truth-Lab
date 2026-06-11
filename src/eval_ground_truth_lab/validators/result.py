from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    case_id: str
    validator_id: str
    passed: bool
    category: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
