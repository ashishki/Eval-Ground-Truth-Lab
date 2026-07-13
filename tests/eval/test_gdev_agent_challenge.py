from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval_ground_truth_lab.adapters import (
    GdevAgentConfig,
    GdevAgentHttpAdapter,
    GdevAgentHttpResponse,
)
from eval_ground_truth_lab.adapters.base import AdapterResult
from eval_ground_truth_lab.challenge import (
    ChallengeConfigurationError,
    ChallengeThresholds,
    evaluate_thresholds,
    render_challenge_markdown,
)
from eval_ground_truth_lab.cli import run_gdev_agent_challenge
from eval_ground_truth_lab.evidence import verify_evidence_manifest

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "datasets/gdev_agent/challenge_v1.jsonl"
THRESHOLDS = ROOT / "datasets/gdev_agent/challenge_thresholds.json"


def test_challenge_executes_90_candidate_cases_and_reconciles_10_faults(tmp_path) -> None:
    adapter = _PassingChallengeAdapter()
    evidence = tmp_path / "evidence"

    exit_code = _run(tmp_path, evidence=evidence, adapter=adapter)
    result = json.loads((evidence / "challenge-run.json").read_text(encoding="utf-8"))
    report = (evidence / "challenge-report.md").read_text(encoding="utf-8")
    manifest = next(evidence.glob("sha256-*.manifest.json"))
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert adapter.invocations == 90
    assert result["gate"] == {"failed_thresholds": [], "passed": True}
    assert result["metrics"]["candidate_scope_case_count"] == 90
    assert result["metrics"]["expected_failure_case_count"] == 10
    assert result["metrics"]["expected_failure_matched_count"] == 10
    assert result["metrics"]["expected_failure_matched"] == 1.0
    assert result["metrics"]["unexpected_fail_count"] == 0
    assert result["metrics"]["unexpected_pass_count"] == 0
    assert result["metrics"]["human_review_required_count"] == 99
    assert result["provenance"]["fixture"] is True
    request_namespace = result["provenance"]["request_namespace"]
    assert request_namespace["adapter_mode"] == "custom_adapter_passthrough"
    assert request_namespace["applied"] is False
    assert request_namespace["applied_fields"] == []
    assert request_namespace["context"] == {
        "candidate_version": "fixture-passing-candidate",
        "component_revision": "fixture:not-external-gdev",
        "dataset_hash": result["dataset"]["dataset_hash"],
        "run_id": "evidence",
        "schema_version": "gdev-agent-request-namespace-v1",
    }
    assert request_namespace["identifier"].startswith("gdev-eval-v1-")
    assert manifest_payload["metadata"]["request_namespace"] == request_namespace
    assert adapter.observed_message_ids[0] == "challenge-ambiguous-multi-intent-001"
    assert set(result["provenance"]["implementation_sha256"]) == {
        "challenge",
        "cli",
        "gdev_adapter",
        "gdev_validators",
    }
    assert result["slices"]["provider_error_simulation"]["reconciled_pass_rate"] == 1.0
    assert {
        case["execution_mode"]
        for case in result["cases"]
        if case["slice"] == "provider_error_simulation"
    } == {"deterministic_fault_injection"}
    assert {
        case["outcome"] for case in result["cases"] if case["slice"] == "provider_error_simulation"
    } == {"expected_failure_matched"}
    assert report == render_challenge_markdown(result)
    assert "fixture:not-external-gdev" in report
    assert "Deterministic provider faults" in report
    assert request_namespace["identifier"] in report
    assert "custom_adapter_passthrough" in report
    assert "gdev-challenge-provider-error-simulation-001" in report
    assert verify_evidence_manifest(manifest).artifact_count == 4


def test_challenge_returns_nonzero_and_preserves_failed_gate_evidence(tmp_path) -> None:
    evidence = tmp_path / "failed-evidence"
    adapter = _PassingChallengeAdapter(unsafe_case_id="gdev-challenge-refund-pressure-001")

    exit_code = _run(tmp_path, evidence=evidence, adapter=adapter)
    result = json.loads((evidence / "challenge-run.json").read_text(encoding="utf-8"))

    assert exit_code == 1
    assert result["gate"]["passed"] is False
    assert "blocking_failure_count_max" in result["gate"]["failed_thresholds"]
    assert "max_unsafe_auto_approval_rate" in result["gate"]["failed_thresholds"]
    assert result["metrics"]["blocking_failure_count"] == 1
    assert verify_evidence_manifest(next(evidence.glob("sha256-*.manifest.json")))


def test_challenge_binds_namespace_to_live_http_adapter_and_records_it(tmp_path) -> None:
    payloads: list[dict[str, Any]] = []

    def fake_transport(
        _url: str,
        body: bytes,
        _headers: dict[str, str],
    ) -> GdevAgentHttpResponse:
        payloads.append(json.loads(body.decode("utf-8")))
        return GdevAgentHttpResponse(status_code=200, output={})

    adapter = GdevAgentHttpAdapter(
        GdevAgentConfig(
            base_url="http://fixture.invalid",
            tenant_slug="fixture-tenant",
            tenant_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            webhook_secret="fixture-secret",
        ),
        transport=fake_transport,
    )
    evidence = tmp_path / "http-evidence"

    exit_code = run_gdev_agent_challenge(
        dataset_path=DATASET,
        base_url="http://fixture.invalid",
        evidence_dir=evidence,
        component_revision="a" * 40,
        component_worktree_state="clean",
        environment_label="local-mocked-transport",
        candidate_version="candidate-a",
        run_id="http-run-a",
        run_dir=tmp_path / "runs",
        threshold_config_path=THRESHOLDS,
        adapter=adapter,
    )

    result = json.loads((evidence / "challenge-run.json").read_text(encoding="utf-8"))
    manifest_path = next(evidence.glob("sha256-*.manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request_namespace = result["provenance"]["request_namespace"]

    assert exit_code == 1
    assert len(payloads) == 90
    assert request_namespace["adapter_mode"] == "gdev_http_namespaced"
    assert request_namespace["applied"] is True
    assert request_namespace["applied_fields"] == ["message_id", "request_id"]
    assert request_namespace["context"]["run_id"] == "http-run-a"
    assert request_namespace["context"]["candidate_version"] == "candidate-a"
    assert manifest["metadata"]["request_namespace"] == request_namespace
    assert all(
        payload["metadata"]["eval_request_namespace"] == request_namespace["identifier"]
        for payload in payloads
    )
    assert all(
        str(payload["request_id"]).startswith(request_namespace["identifier"])
        for payload in payloads
    )
    assert all(
        str(payload["message_id"]).startswith(request_namespace["identifier"])
        for payload in payloads
    )
    assert verify_evidence_manifest(manifest_path)


@pytest.mark.parametrize(
    ("threshold_name", "metric_name", "failing_value"),
    (
        ("blocking_failure_count_max", "blocking_failure_count", 1),
        ("classification_accuracy_min", "classification_accuracy", 0.69),
        ("expected_failure_matched_min", "expected_failure_matched", 0.79),
        ("human_review_required_count_min", "human_review_required_count", 79),
        ("human_escalation_recall_min", "human_escalation_recall", 0.94),
        ("judge_optional_cases_max", "judge_optional_cases", 21),
        ("max_cost_per_case_usd", "cost_per_case_usd", 0.011),
        (
            "max_invalid_structured_output_rate",
            "invalid_structured_output_rate",
            0.06,
        ),
        ("max_latency_p95_ms", "latency_p95_ms", 2501.0),
        ("max_unsafe_auto_approval_rate", "unsafe_auto_approval_rate", 0.01),
        ("unexpected_fail_count_max", "unexpected_fail_count", 21),
        ("unexpected_pass_count_max", "unexpected_pass_count", 6),
    ),
)
def test_every_declared_threshold_can_fail_gate(threshold_name, metric_name, failing_value) -> None:  # noqa: ANN001
    thresholds = _thresholds()
    metrics = _passing_metrics()
    metrics[metric_name] = failing_value

    results = evaluate_thresholds(metrics, thresholds)

    assert set(results) == set(thresholds.to_mapping()) - {"version"}
    assert results[threshold_name]["passed"] is False
    assert [name for name, result in results.items() if not result["passed"]] == [threshold_name]


def test_threshold_loader_rejects_unknown_or_missing_fields() -> None:
    raw = _thresholds().to_mapping()
    del raw["judge_optional_cases_max"]
    raw["unreviewed_threshold"] = 1

    with pytest.raises(ChallengeConfigurationError, match="missing.*unknown"):
        ChallengeThresholds.from_mapping(raw)


@pytest.mark.parametrize("revision", ("latest", "deadbee", "a" * 39, "a" * 41))
def test_challenge_rejects_unpinned_or_ambiguously_labeled_provenance(tmp_path, revision) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match="full 40- or 64-character git commit SHA"):
        run_gdev_agent_challenge(
            dataset_path=DATASET,
            base_url="http://fixture.invalid",
            evidence_dir=tmp_path / "evidence",
            component_revision=revision,
            component_worktree_state="clean",
            environment_label="local",
            candidate_version="candidate",
            run_dir=tmp_path / "runs",
            threshold_config_path=THRESHOLDS,
            adapter=_PassingChallengeAdapter(),
        )


def test_challenge_rejects_fixture_without_explicit_fixture_label(tmp_path) -> None:
    with pytest.raises(ValueError, match="environment label"):
        run_gdev_agent_challenge(
            dataset_path=DATASET,
            base_url="http://fixture.invalid",
            evidence_dir=tmp_path / "evidence",
            component_revision="fixture:test-only",
            component_worktree_state="fixture",
            environment_label="local",
            candidate_version="candidate",
            run_dir=tmp_path / "runs",
            threshold_config_path=THRESHOLDS,
            adapter=_PassingChallengeAdapter(),
        )


def _run(tmp_path, *, evidence: Path, adapter: _PassingChallengeAdapter) -> int:  # noqa: ANN001
    return run_gdev_agent_challenge(
        dataset_path=DATASET,
        base_url="http://fixture.invalid",
        evidence_dir=evidence,
        component_revision="fixture:not-external-gdev",
        component_worktree_state="fixture",
        environment_label="ci-deterministic-fixture",
        candidate_version="fixture-passing-candidate",
        run_id=evidence.name,
        run_dir=tmp_path / "runs",
        threshold_config_path=THRESHOLDS,
        adapter=adapter,
    )


class _PassingChallengeAdapter:
    def __init__(self, *, unsafe_case_id: str | None = None) -> None:
        self.invocations = 0
        self.observed_message_ids: list[str] = []
        self.unsafe_case_id = unsafe_case_id

    def invoke(self, case: dict[str, Any]) -> AdapterResult:
        self.invocations += 1
        self.observed_message_ids.append(str(case["input"]["message_id"]))
        expected = case["expected"]
        output = {
            "adapter_error": False,
            "case_id": case["id"],
            "category": expected["category"],
            "confidence": 0.99,
            "cost_usd": 0.001,
            "guard_blocked": expected["guard_behavior"] == "block_input",
            "invalid_structured_output": False,
            "latency_ms": 10.0,
            "requires_human": expected["requires_human"],
            "risk_reason": "deterministic CI fixture follows expected route",
            "status": expected["expected_status"],
            "unsafe_auto_approval": False,
        }
        if case["id"] == self.unsafe_case_id:
            output.update(
                {
                    "requires_human": False,
                    "status": "executed",
                    "unsafe_auto_approval": True,
                }
            )
        return AdapterResult(output=output, latency_ms=10.0, status_code=200)


def _thresholds() -> ChallengeThresholds:
    return ChallengeThresholds.from_mapping(json.loads(THRESHOLDS.read_text(encoding="utf-8")))


def _passing_metrics() -> dict[str, int | float]:
    return {
        "blocking_failure_count": 0,
        "classification_accuracy": 1.0,
        "cost_per_case_usd": 0.001,
        "expected_failure_matched": 1.0,
        "human_escalation_recall": 1.0,
        "human_review_required_count": 100,
        "invalid_structured_output_rate": 0.0,
        "judge_optional_cases": 0,
        "latency_p95_ms": 10.0,
        "unexpected_fail_count": 0,
        "unexpected_pass_count": 0,
        "unsafe_auto_approval_rate": 0.0,
    }
