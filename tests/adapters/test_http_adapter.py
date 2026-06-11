from __future__ import annotations

import pytest

from eval_ground_truth_lab.adapters import (
    HttpCandidateAdapter,
    HttpResponse,
    UnsafeAdapterInputError,
)


def test_http_adapter_rejects_case_defined_destinations() -> None:
    called_urls = []

    def fake_transport(url, payload):
        called_urls.append((url, payload))
        return HttpResponse(status_code=200, output={"category": "billing"})

    adapter = HttpCandidateAdapter(
        "https://candidate.example.test/eval",
        transport=fake_transport,
    )

    result = adapter.invoke({"id": "case-001", "input": {"ticket": "Refund"}})
    with pytest.raises(UnsafeAdapterInputError):
        adapter.invoke(
            {
                "id": "case-002",
                "input": {"ticket": "Refund"},
                "url": "https://attacker.example.test/eval",
            }
        )

    assert called_urls == [
        (
            "https://candidate.example.test/eval",
            {"case": {"id": "case-001", "input": {"ticket": "Refund"}}},
        )
    ]
    assert result.output == {"category": "billing"}
    assert result.status_code == 200
    assert result.exit_code == 0
    assert result.trace_id
    assert result.operation_name == "candidate.http"
