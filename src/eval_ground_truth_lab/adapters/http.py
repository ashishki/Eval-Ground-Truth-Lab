from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from urllib import request

from eval_ground_truth_lab.adapters.base import AdapterResult, UnsafeAdapterInputError
from eval_ground_truth_lab.tracing import start_trace

FORBIDDEN_HTTP_FIELDS = frozenset({"url", "uri", "endpoint", "base_url", "host"})


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    output: Any


class HttpCandidateAdapter:
    def __init__(
        self,
        base_url: str,
        *,
        transport: Callable[[str, dict[str, Any]], HttpResponse] | None = None,
    ) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must be an http(s) URL")
        self.base_url = base_url
        self._transport = transport or _post_json

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        _reject_forbidden_fields(case, FORBIDDEN_HTTP_FIELDS)
        trace = start_trace("candidate.http")
        started = perf_counter()
        response = self._transport(self.base_url, {"case": dict(case)})
        latency_ms = (perf_counter() - started) * 1000
        return AdapterResult(
            output=response.output,
            status_code=response.status_code,
            latency_ms=latency_ms,
            exit_code=0 if 200 <= response.status_code < 400 else 1,
            trace_id=trace.trace_id,
            operation_name=trace.operation_name,
        )


def _reject_forbidden_fields(case: Mapping[str, Any], forbidden_fields: frozenset[str]) -> None:
    present = sorted(field for field in forbidden_fields if field in case)
    if present:
        raise UnsafeAdapterInputError(
            f"Eval case cannot define network destination fields: {', '.join(present)}"
        )


def _post_json(url: str, payload: dict[str, Any]) -> HttpResponse:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    http_request = request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return HttpResponse(
            status_code=response.status,
            output=json.loads(body) if body else None,
        )
