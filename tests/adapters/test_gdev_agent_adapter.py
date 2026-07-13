from __future__ import annotations

import copy
import hashlib
import hmac
import json
from http.client import RemoteDisconnected

import pytest

from eval_ground_truth_lab.adapters import (
    GdevAgentConfig,
    GdevAgentHttpAdapter,
    GdevAgentHttpResponse,
    GdevRequestNamespace,
    MissingGdevRequestNamespaceError,
    UnsafeAdapterInputError,
)


def _config() -> GdevAgentConfig:
    return GdevAgentConfig(
        base_url="http://localhost:8000",
        tenant_slug="test-tenant-a",
        tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        webhook_secret="test-webhook-secret-a",
    )


def _case() -> dict[str, object]:
    return {
        "id": "gdev-billing-refund-001",
        "input": {
            "tenant_slug": "ignored-case-tenant",
            "message_id": "eval-billing-refund-001",
            "user_id": "eval-user-001",
            "text": "I was charged twice for gems and want a refund.",
        },
        "expected": {"category": "billing"},
        "metadata": {"slice": "billing_refund", "synthetic": True},
    }


def _namespace(
    *,
    run_id: str = "run-a",
    candidate_version: str = "candidate-a",
) -> GdevRequestNamespace:
    return GdevRequestNamespace(
        run_id=run_id,
        candidate_version=candidate_version,
        component_revision="a" * 40,
        dataset_hash="b" * 64,
    )


def _gdev_pending_response() -> dict[str, object]:
    return {
        "status": "pending",
        "classification": {"category": "billing", "urgency": "high", "confidence": 0.86},
        "action": {
            "tool": "create_ticket_and_reply",
            "payload": {"category": "billing"},
            "risky": True,
            "risk_reason": "billing/refund requires approval",
        },
        "draft_response": "We will route this to review.",
        "pending": {"pending_id": "pending-001", "reason": "manual approval required"},
    }


def test_adapter_uses_configured_base_url_only() -> None:
    captured: list[tuple[str, dict[str, object]]] = []

    def fake_transport(url: str, body: bytes, headers: dict[str, str]) -> GdevAgentHttpResponse:
        captured.append((url, json.loads(body.decode("utf-8"))))
        assert headers["X-Tenant-Slug"] == "test-tenant-a"
        return GdevAgentHttpResponse(status_code=200, output=_gdev_pending_response())

    request_namespace = _namespace()
    adapter = GdevAgentHttpAdapter(
        _config(),
        request_namespace=request_namespace,
        transport=fake_transport,
    )

    result = adapter.invoke(_case())

    assert captured == [
        (
            "http://localhost:8000/webhook",
            {
                "request_id": request_namespace.scoped_id("request_id", "gdev-billing-refund-001"),
                "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "message_id": request_namespace.scoped_id("message_id", "eval-billing-refund-001"),
                "user_id": "eval-user-001",
                "text": "I was charged twice for gems and want a refund.",
                "metadata": {
                    "eval_case_id": "gdev-billing-refund-001",
                    "eval_request_namespace": request_namespace.identifier,
                },
            },
        )
    ]
    assert result.output["status"] == "pending"
    assert result.output["category"] == "billing"
    assert result.output["requires_human"] is True
    assert result.output["risk_reason"] == "billing/refund requires approval"
    assert result.status_code == 200
    assert result.exit_code == 0
    assert result.trace_id
    assert result.operation_name == "candidate.gdev_agent.http"


def test_case_cannot_override_network_or_secret_boundary() -> None:
    adapter = GdevAgentHttpAdapter(
        _config(),
        request_namespace=_namespace(),
        transport=lambda *_args: GdevAgentHttpResponse(status_code=200, output={}),
    )
    forbidden_fields = [
        "base_url",
        "host",
        "endpoint",
        "webhook_secret",
        "tenant_secret",
        "auth_token",
        "command",
        "request_namespace",
        "request_namespace_id",
    ]

    for field in forbidden_fields:
        case = _case()
        case_input = dict(case["input"])  # type: ignore[arg-type]
        case_input[field] = "https://attacker.example.test"
        case["input"] = case_input

        with pytest.raises(UnsafeAdapterInputError):
            adapter.invoke(case)


def test_webhook_signature_uses_configured_secret() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url: str, body: bytes, headers: dict[str, str]) -> GdevAgentHttpResponse:
        captured["url"] = url
        captured["body"] = body
        captured["headers"] = headers
        return GdevAgentHttpResponse(status_code=200, output=_gdev_pending_response())

    adapter = GdevAgentHttpAdapter(
        _config(),
        request_namespace=_namespace(),
        transport=fake_transport,
    )
    adapter.invoke(_case())

    expected = (
        "sha256="
        + hmac.new(
            b"test-webhook-secret-a",
            captured["body"],  # type: ignore[arg-type]
            hashlib.sha256,
        ).hexdigest()
    )
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["X-Webhook-Signature"] == expected
    assert headers["Content-Type"] == "application/json"


def test_adapter_uses_mocked_transport() -> None:
    calls = 0

    def fake_transport(_url: str, _body: bytes, _headers: dict[str, str]) -> GdevAgentHttpResponse:
        nonlocal calls
        calls += 1
        return GdevAgentHttpResponse(
            status_code=200,
            output={
                "status": "executed",
                "classification": {
                    "category": "bug_report",
                    "urgency": "low",
                    "confidence": 0.91,
                },
                "action": {"tool": "create_ticket_and_reply", "risky": False},
            },
        )

    adapter = GdevAgentHttpAdapter(
        _config(),
        request_namespace=_namespace(),
        transport=fake_transport,
    )

    result = adapter.invoke(_case())

    assert calls == 1
    assert result.output["status"] == "executed"
    assert result.output["category"] == "bug_report"
    assert result.output["requires_human"] is False


def test_network_disconnect_normalizes_to_adapter_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_urlopen(*_args: object, **_kwargs: object) -> object:
        raise RemoteDisconnected("remote end closed connection without response")

    monkeypatch.setattr(
        "eval_ground_truth_lab.adapters.gdev_agent.request.urlopen",
        broken_urlopen,
    )
    adapter = GdevAgentHttpAdapter(_config(), request_namespace=_namespace())

    result = adapter.invoke(_case())

    assert result.status_code == 599
    assert result.exit_code == 1
    assert result.output["status"] == "error"
    assert result.output["category"] == "adapter_error"
    assert result.output["adapter_error"] is True
    assert "RemoteDisconnected" in result.output["risk_reason"]


def test_live_adapter_rejects_invoke_without_request_namespace() -> None:
    transport_called = False

    def fake_transport(*_args: object) -> GdevAgentHttpResponse:
        nonlocal transport_called
        transport_called = True
        return GdevAgentHttpResponse(status_code=200, output={})

    adapter = GdevAgentHttpAdapter(_config(), transport=fake_transport)

    with pytest.raises(MissingGdevRequestNamespaceError, match="request namespace"):
        adapter.invoke(_case())

    assert transport_called is False


def test_request_namespace_is_stable_within_run_and_distinct_across_runs() -> None:
    payloads: list[dict[str, object]] = []

    def fake_transport(
        _url: str,
        body: bytes,
        _headers: dict[str, str],
    ) -> GdevAgentHttpResponse:
        payloads.append(json.loads(body.decode("utf-8")))
        return GdevAgentHttpResponse(status_code=200, output=_gdev_pending_response())

    original_case = _case()
    original_snapshot = copy.deepcopy(original_case)
    namespace_a = _namespace(run_id="run-a", candidate_version="candidate-a")
    namespace_b = _namespace(run_id="run-b", candidate_version="candidate-b")
    adapter_a = GdevAgentHttpAdapter(
        _config(),
        request_namespace=namespace_a,
        transport=fake_transport,
    )
    adapter_b = GdevAgentHttpAdapter(
        _config(),
        request_namespace=namespace_b,
        transport=fake_transport,
    )

    adapter_a.invoke(original_case)
    adapter_a.invoke(original_case)
    adapter_b.invoke(original_case)

    assert payloads[0]["request_id"] == payloads[1]["request_id"]
    assert payloads[0]["message_id"] == payloads[1]["message_id"]
    assert payloads[0]["request_id"] != payloads[2]["request_id"]
    assert payloads[0]["message_id"] != payloads[2]["message_id"]
    assert namespace_a.identifier != namespace_b.identifier
    assert payloads[0]["metadata"] == {
        "eval_case_id": "gdev-billing-refund-001",
        "eval_request_namespace": namespace_a.identifier,
    }
    assert payloads[2]["metadata"] == {
        "eval_case_id": "gdev-billing-refund-001",
        "eval_request_namespace": namespace_b.identifier,
    }
    assert original_case == original_snapshot


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("run_id", "run-b"),
        ("candidate_version", "candidate-b"),
        ("component_revision", "c" * 40),
        ("dataset_hash", "d" * 64),
    ),
)
def test_each_namespace_dimension_changes_scoped_ids(field: str, replacement: str) -> None:
    context = {
        "run_id": "run-a",
        "candidate_version": "candidate-a",
        "component_revision": "a" * 40,
        "dataset_hash": "b" * 64,
    }
    baseline = GdevRequestNamespace(**context)
    context[field] = replacement
    changed = GdevRequestNamespace(**context)

    assert baseline.identifier != changed.identifier
    assert baseline.scoped_id("request_id", "case-a") != changed.scoped_id("request_id", "case-a")
    assert baseline.scoped_id("message_id", "message-a") != changed.scoped_id(
        "message_id", "message-a"
    )


@pytest.mark.parametrize(
    "field",
    ("run_id", "candidate_version", "component_revision", "dataset_hash"),
)
def test_request_namespace_rejects_empty_context_fields(field: str) -> None:
    values = {
        "run_id": "run-a",
        "candidate_version": "candidate-a",
        "component_revision": "a" * 40,
        "dataset_hash": "b" * 64,
    }
    values[field] = ""

    with pytest.raises(ValueError, match=field):
        GdevRequestNamespace(**values)
