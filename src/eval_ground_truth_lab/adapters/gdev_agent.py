from __future__ import annotations

import hashlib
import hmac
import http.client as http_client
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from urllib import error, request

from eval_ground_truth_lab.adapters.base import AdapterResult, UnsafeAdapterInputError
from eval_ground_truth_lab.adapters.gdev_normalizer import normalize_gdev_response
from eval_ground_truth_lab.tracing import start_trace

FORBIDDEN_GDEV_CASE_FIELDS = frozenset(
    {
        "auth_token",
        "base_url",
        "cmd",
        "command",
        "endpoint",
        "host",
        "request_namespace",
        "request_namespace_id",
        "tenant_id",
        "tenant_secret",
        "token",
        "uri",
        "url",
        "webhook_secret",
    }
)

REQUEST_NAMESPACE_SCHEMA_VERSION = "gdev-agent-request-namespace-v1"
_SCOPED_ID_KINDS = frozenset({"message_id", "request_id"})


class MissingGdevRequestNamespaceError(ValueError):
    """Raised when a live HTTP adapter is invoked without run-scoped IDs."""


@dataclass(frozen=True)
class GdevRequestNamespace:
    """Deterministic namespace for IDs sent to a stateful gdev-agent service."""

    run_id: str
    candidate_version: str
    component_revision: str
    dataset_hash: str

    def __post_init__(self) -> None:
        for field_name in (
            "run_id",
            "candidate_version",
            "component_revision",
            "dataset_hash",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    @property
    def context_sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.context_mapping())).hexdigest()

    @property
    def identifier(self) -> str:
        return f"gdev-eval-v1-{self.context_sha256}"

    def context_mapping(self) -> dict[str, str]:
        return {
            "candidate_version": self.candidate_version,
            "component_revision": self.component_revision,
            "dataset_hash": self.dataset_hash,
            "run_id": self.run_id,
            "schema_version": REQUEST_NAMESPACE_SCHEMA_VERSION,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "context": self.context_mapping(),
            "context_sha256": self.context_sha256,
            "identifier": self.identifier,
            "schema_version": REQUEST_NAMESPACE_SCHEMA_VERSION,
        }

    def scoped_id(self, kind: str, original_id: str) -> str:
        if kind not in _SCOPED_ID_KINDS:
            raise ValueError(f"Unsupported gdev ID kind: {kind}")
        if not isinstance(original_id, str) or not original_id:
            raise ValueError("original_id must be a non-empty string")
        case_digest = hashlib.sha256(
            _canonical_json_bytes({"kind": kind, "original_id": original_id})
        ).hexdigest()
        return f"{self.identifier}-{kind}-{case_digest[:24]}"


@dataclass(frozen=True)
class GdevAgentConfig:
    base_url: str
    tenant_slug: str
    tenant_id: str
    webhook_secret: str

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        base_url: str | None = None,
    ) -> GdevAgentConfig:
        source = environ or os.environ
        return cls(
            base_url=base_url or source.get("GDEV_AGENT_BASE_URL", "http://localhost:8000"),
            tenant_slug=source.get("GDEV_AGENT_TENANT_SLUG", "test-tenant-a"),
            tenant_id=source.get(
                "GDEV_AGENT_TENANT_ID",
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            ),
            webhook_secret=source.get("GDEV_AGENT_WEBHOOK_SECRET", "test-webhook-secret-a"),
        )

    @property
    def webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/webhook"


@dataclass(frozen=True)
class GdevAgentHttpResponse:
    status_code: int
    output: Any


class GdevAgentHttpAdapter:
    def __init__(
        self,
        config: GdevAgentConfig,
        *,
        request_namespace: GdevRequestNamespace | None = None,
        transport: Callable[[str, bytes, dict[str, str]], GdevAgentHttpResponse] | None = None,
    ) -> None:
        if not config.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must be an http(s) URL")
        self.config = config
        self.request_namespace = request_namespace
        self._transport = transport or _post_signed_json

    def with_request_namespace(
        self, request_namespace: GdevRequestNamespace
    ) -> GdevAgentHttpAdapter:
        """Return an equivalent adapter bound to one immutable eval-run namespace."""

        return GdevAgentHttpAdapter(
            self.config,
            request_namespace=request_namespace,
            transport=self._transport,
        )

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        if self.request_namespace is None:
            raise MissingGdevRequestNamespaceError(
                "GdevAgentHttpAdapter requires a deterministic request namespace before invoke"
            )
        _reject_forbidden_fields(case)
        trace = start_trace("candidate.gdev_agent.http")
        payload = _build_webhook_payload(
            case=case,
            config=self.config,
            request_namespace=self.request_namespace,
        )
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = _signed_headers(
            body=body,
            tenant_slug=self.config.tenant_slug,
            webhook_secret=self.config.webhook_secret,
        )

        started = perf_counter()
        response = self._transport(self.config.webhook_url, body, headers)
        latency_ms = (perf_counter() - started) * 1000
        output = normalize_gdev_response(
            case_id=str(case["id"]),
            response_body=response.output,
            http_status=response.status_code,
            latency_ms=latency_ms,
        )
        return AdapterResult(
            output=output.to_mapping(),
            status_code=response.status_code,
            latency_ms=latency_ms,
            exit_code=0 if 200 <= response.status_code < 400 else 1,
            trace_id=trace.trace_id,
            operation_name=trace.operation_name,
        )


def _build_webhook_payload(
    *,
    case: Mapping[str, Any],
    config: GdevAgentConfig,
    request_namespace: GdevRequestNamespace,
) -> dict[str, Any]:
    case_input = case.get("input")
    if not isinstance(case_input, Mapping):
        raise ValueError("gdev-agent case input must be an object")
    text = case_input.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("gdev-agent case input.text is required")

    metadata = case_input.get("metadata")
    payload_metadata = dict(metadata) if isinstance(metadata, Mapping) else {}
    payload_metadata["eval_case_id"] = str(case["id"])
    payload_metadata["eval_request_namespace"] = request_namespace.identifier

    request_id = _optional_string(case_input.get("request_id")) or str(case["id"])
    message_id = _optional_string(case_input.get("message_id")) or str(case["id"])

    return {
        "request_id": request_namespace.scoped_id("request_id", request_id),
        "tenant_id": config.tenant_id,
        "message_id": request_namespace.scoped_id("message_id", message_id),
        "user_id": _optional_string(case_input.get("user_id")),
        "text": text,
        "metadata": payload_metadata,
    }


def _signed_headers(
    *,
    body: bytes,
    tenant_slug: str,
    webhook_secret: str,
) -> dict[str, str]:
    signature = (
        "sha256="
        + hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
    )
    return {
        "Content-Type": "application/json",
        "X-Tenant-Slug": tenant_slug,
        "X-Webhook-Signature": signature,
    }


def _post_signed_json(
    url: str,
    body: bytes,
    headers: dict[str, str],
) -> GdevAgentHttpResponse:
    http_request = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(http_request, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
            return GdevAgentHttpResponse(
                status_code=response.status,
                output=_decode_json_body(raw_body),
            )
    except error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8")
        return GdevAgentHttpResponse(
            status_code=exc.code,
            output=_decode_json_body(raw_body),
        )
    except (error.URLError, TimeoutError, http_client.HTTPException, OSError) as exc:
        return GdevAgentHttpResponse(
            status_code=599,
            output={
                "detail": f"{exc.__class__.__name__}: {exc}",
                "error_type": exc.__class__.__name__,
            },
        )


def _decode_json_body(raw_body: str) -> Any:
    if not raw_body:
        return None
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {"detail": raw_body}


def _reject_forbidden_fields(value: Any, path: str = "case") -> None:
    if not isinstance(value, Mapping):
        return
    present = sorted(field for field in FORBIDDEN_GDEV_CASE_FIELDS if field in value)
    if present:
        raise UnsafeAdapterInputError(
            f"Eval case cannot define gdev-agent adapter fields at {path}: " + ", ".join(present)
        )
    for key, nested in value.items():
        if isinstance(nested, Mapping):
            _reject_forbidden_fields(nested, f"{path}.{key}")


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
