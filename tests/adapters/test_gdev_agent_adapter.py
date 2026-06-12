from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from eval_ground_truth_lab.adapters import (
    GdevAgentConfig,
    GdevAgentHttpAdapter,
    GdevAgentHttpResponse,
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

    adapter = GdevAgentHttpAdapter(_config(), transport=fake_transport)

    result = adapter.invoke(_case())

    assert captured == [
        (
            "http://localhost:8000/webhook",
            {
                "request_id": "gdev-billing-refund-001",
                "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "message_id": "eval-billing-refund-001",
                "user_id": "eval-user-001",
                "text": "I was charged twice for gems and want a refund.",
                "metadata": {"eval_case_id": "gdev-billing-refund-001"},
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

    adapter = GdevAgentHttpAdapter(_config(), transport=fake_transport)
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

    adapter = GdevAgentHttpAdapter(_config(), transport=fake_transport)

    result = adapter.invoke(_case())

    assert calls == 1
    assert result.output["status"] == "executed"
    assert result.output["category"] == "bug_report"
    assert result.output["requires_human"] is False
