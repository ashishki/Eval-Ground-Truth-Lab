from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

GDEV_STATUSES = frozenset({"executed", "pending", "blocked", "error"})
REQUIRED_GDEV_FIELDS = ("status", "category", "confidence", "requires_human")


@dataclass(frozen=True)
class NormalizedGdevOutput:
    case_id: str
    status: str
    category: str
    confidence: float
    requires_human: bool
    risk_reason: str
    guard_blocked: bool
    invalid_structured_output: bool
    unsafe_auto_approval: bool
    cost_usd: float | None
    latency_ms: float | None
    adapter_error: bool = False

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def normalize_gdev_response(
    *,
    case_id: str,
    response_body: Any,
    http_status: int = 200,
    latency_ms: float | None = None,
) -> NormalizedGdevOutput:
    if not isinstance(response_body, Mapping):
        return _invalid_output(case_id=case_id, response=response_body, latency_ms=latency_ms)

    if http_status >= 400:
        return _adapter_error(case_id=case_id, response=response_body, latency_ms=latency_ms)

    missing = [field for field in REQUIRED_GDEV_FIELDS if field not in response_body]
    if missing:
        return _invalid_output(
            case_id=case_id,
            response=response_body,
            latency_ms=latency_ms,
            reason=f"missing required fields: {', '.join(missing)}",
        )

    status = response_body["status"]
    category = response_body["category"]
    confidence = _required_float(response_body["confidence"])
    requires_human = response_body["requires_human"]

    if (
        not isinstance(status, str)
        or status not in GDEV_STATUSES
        or not isinstance(category, str)
        or not category
        or confidence is None
        or not isinstance(requires_human, bool)
    ):
        return _invalid_output(
            case_id=case_id,
            response=response_body,
            latency_ms=latency_ms,
            reason="invalid required field types or values",
        )

    return NormalizedGdevOutput(
        case_id=case_id,
        status=status,
        category=category,
        confidence=confidence,
        requires_human=requires_human,
        risk_reason=_optional_string(response_body.get("risk_reason")),
        guard_blocked=_optional_bool(
            response_body.get("guard_blocked"), default=status == "blocked"
        ),
        invalid_structured_output=False,
        unsafe_auto_approval=_optional_bool(
            response_body.get("unsafe_auto_approval"), default=False
        ),
        cost_usd=_extract_cost(response_body),
        latency_ms=_extract_latency(response_body, latency_ms),
        adapter_error=status == "error",
    )


def _adapter_error(
    *,
    case_id: str,
    response: Mapping[str, Any],
    latency_ms: float | None,
) -> NormalizedGdevOutput:
    return NormalizedGdevOutput(
        case_id=case_id,
        status="error",
        category="adapter_error",
        confidence=0.0,
        requires_human=True,
        risk_reason=_optional_string(
            response.get("error") or response.get("message") or "http error"
        ),
        guard_blocked=False,
        invalid_structured_output=False,
        unsafe_auto_approval=False,
        cost_usd=_extract_cost(response),
        latency_ms=_extract_latency(response, latency_ms),
        adapter_error=True,
    )


def _invalid_output(
    *,
    case_id: str,
    response: Any,
    latency_ms: float | None,
    reason: str = "response body is not a structured object",
) -> NormalizedGdevOutput:
    response_mapping = response if isinstance(response, Mapping) else {}
    return NormalizedGdevOutput(
        case_id=case_id,
        status="error",
        category="invalid_structured_output",
        confidence=0.0,
        requires_human=True,
        risk_reason=reason,
        guard_blocked=False,
        invalid_structured_output=True,
        unsafe_auto_approval=False,
        cost_usd=_extract_cost(response_mapping),
        latency_ms=_extract_latency(response_mapping, latency_ms),
        adapter_error=False,
    )


def _extract_cost(response: Mapping[str, Any]) -> float | None:
    cost = _optional_float(response.get("cost_usd"))
    if cost is not None:
        return cost
    usage = response.get("usage")
    if not isinstance(usage, Mapping):
        return None
    return _optional_float(usage.get("estimated_cost_usd"))


def _extract_latency(
    response: Mapping[str, Any], measured_latency_ms: float | None
) -> float | None:
    if measured_latency_ms is not None:
        return measured_latency_ms
    return _optional_float(response.get("latency_ms"))


def _optional_bool(value: Any, *, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _required_float(value: Any) -> float | None:
    number = _optional_float(value)
    if number is None or number < 0.0 or number > 1.0:
        return None
    return number


def _optional_string(value: Any) -> str:
    return value if isinstance(value, str) else ""
