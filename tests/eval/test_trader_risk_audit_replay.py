from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from eval_ground_truth_lab import cli
from eval_ground_truth_lab.adapters import AdapterResult, TraderRiskAuditEvidenceAdapter
from eval_ground_truth_lab.datasets import DatasetValidationError
from eval_ground_truth_lab.evidence import verify_evidence_manifest
from eval_ground_truth_lab.runs import RunStore
from eval_ground_truth_lab.trader_replay import (
    TraderRiskAuditReplayConfigurationError,
    run_trader_risk_audit_replay,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = ROOT / "datasets/trader_risk_audit"
DATASET = DATASET_ROOT / "synthetic_quickstart_v1.jsonl"
EVIDENCE = DATASET_ROOT / "fixtures/synthetic_quickstart_v1/eval-evidence.json"
PROVENANCE = DATASET_ROOT / "synthetic_quickstart_v1.provenance.json"


def test_cli_replays_trader_export_and_writes_verified_evidence_pack(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pack = tmp_path / "pack"
    runs = tmp_path / "runs"

    exit_code = cli.main(
        [
            "run-trader-risk-audit-replay",
            "--dataset",
            str(DATASET),
            "--evidence",
            str(EVIDENCE),
            "--provenance",
            str(PROVENANCE),
            "--evidence-dir",
            str(pack),
            "--run-dir",
            str(runs),
            "--run-id",
            "trader-synthetic-quickstart-v1",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    manifest_path = Path(output["manifest"])
    verification = verify_evidence_manifest(manifest_path)
    result = _json(pack / "replay-result.json")
    manifest = _json(manifest_path)
    report = (pack / "replay-report.md").read_text(encoding="utf-8")

    assert exit_code == 0
    assert output["gate_passed"] is True
    assert verification.artifact_count == 7
    assert verification.content_address == output["content_address"]
    assert result["gate"] == {"failed_validator_count": 0, "passed": True}
    assert result["scope"] == {
        "applies_financial_advice": False,
        "evaluates_raw_trades": False,
        "external_user_case_study": False,
        "production_evidence": False,
        "replay_type": "pinned_synthetic_sanitized_export",
    }
    assert result["source_provenance"]["source_git_commit"] == (
        "bf755a24450ff7c17328fa6d447f36bea8ea0fe5"
    )
    implementation = result["provenance"]["implementation"]
    assert set(implementation["components_sha256"]) == {
        "adapter",
        "dataset_parser",
        "evidence_manifest",
        "run_store",
        "runner",
        "validators",
    }
    assert implementation["package_payload"]["file_count"] > 6
    assert implementation["source"]["kind"] == "git_worktree"
    assert manifest["metadata"]["gate_passed"] is True
    assert manifest["metadata"]["implementation"] == implementation
    assert manifest["metadata"]["fixture"] is True
    run_artifact = _json(pack / "run/trader-synthetic-quickstart-v1.json")
    run_identity = {
        field: run_artifact[field]
        for field in ("candidate_version", "dataset_hash", "run_id", "status", "validator_version")
    }
    assert run_identity == {field: manifest["metadata"]["run"][field] for field in run_identity}
    assert run_identity == {field: result["run"][field] for field in run_identity}
    assert (
        manifest["metadata"]["run"]["record_sha256"]
        == hashlib.sha256(
            (pack / "run/trader-synthetic-quickstart-v1.json").read_bytes()
        ).hexdigest()
    )
    assert (
        manifest["metadata"]["run"]["seal_sha256"]
        == hashlib.sha256(
            (pack / "run/trader-synthetic-quickstart-v1.sha256").read_bytes()
        ).hexdigest()
    )
    assert run_artifact["status"] == "completed"
    assert (pack / "inputs/eval-evidence.json").read_bytes() == EVIDENCE.read_bytes()
    assert "not a financial-performance evaluation" in report
    assert "external-user case study" in report


def test_changed_ground_truth_returns_failing_gate_with_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    case = json.loads(DATASET.read_text(encoding="utf-8"))
    case["expected"]["evidence"]["metrics"]["violation_count"] = 8
    changed_dataset = tmp_path / "changed.jsonl"
    changed_dataset.write_text(json.dumps(case, sort_keys=True) + "\n", encoding="utf-8")
    pack = tmp_path / "pack"

    exit_code = run_trader_risk_audit_replay(
        dataset_path=changed_dataset,
        evidence_path=EVIDENCE,
        provenance_path=PROVENANCE,
        evidence_dir=pack,
        run_dir=tmp_path / "runs",
        run_id="trader-changed-expectation",
    )
    capsys.readouterr()

    result = _json(pack / "replay-result.json")
    manifest = _json(next(pack.glob("sha256-*.manifest.json")))
    report = (pack / "replay-report.md").read_text(encoding="utf-8")
    assert exit_code == 1
    assert result["gate"] == {"failed_validator_count": 1, "passed": False}
    assert result["cases"][0]["failed_validators"] == ["trader_risk_audit.synthetic_metrics"]
    assert result["provenance"]["fixture"] is False
    assert result["provenance"]["privacy_classification"] == (
        "caller-supplied-dataset-not-privacy-reviewed"
    )
    assert manifest["metadata"]["fixture"] is False
    assert "makes no fixture or privacy claim" in report
    verify_evidence_manifest(next(pack.glob("sha256-*.manifest.json")))


def test_default_packaged_inputs_replay_from_unrelated_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unrelated = tmp_path / "unrelated-working-directory"
    unrelated.mkdir()
    pack = tmp_path / "pack"
    monkeypatch.chdir(unrelated)

    exit_code = cli.main(
        [
            "run-trader-risk-audit-replay",
            "--evidence-dir",
            str(pack),
            "--run-dir",
            str(tmp_path / "runs"),
            "--run-id",
            "trader-packaged-defaults",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["gate_passed"] is True
    assert (pack / "inputs/dataset.jsonl").read_bytes() == DATASET.read_bytes()
    assert (pack / "inputs/eval-evidence.json").read_bytes() == EVIDENCE.read_bytes()
    assert (pack / "inputs/source-provenance.json").read_bytes() == PROVENANCE.read_bytes()
    verify_evidence_manifest(Path(output["manifest"]))


def test_packaged_defaults_are_byte_identical_to_repository_fixtures() -> None:
    resource_root = (
        resources.files("eval_ground_truth_lab").joinpath("resources").joinpath("trader_risk_audit")
    )

    assert (
        resource_root.joinpath("synthetic_quickstart_v1.jsonl").read_bytes() == DATASET.read_bytes()
    )
    assert resource_root.joinpath("eval-evidence.json").read_bytes() == EVIDENCE.read_bytes()
    assert (
        resource_root.joinpath("synthetic_quickstart_v1.provenance.json").read_bytes()
        == PROVENANCE.read_bytes()
    )


@pytest.mark.parametrize("case_count", [0, 2])
def test_v1_replay_rejects_non_singleton_dataset_without_creating_a_pack(
    tmp_path: Path,
    case_count: int,
) -> None:
    dataset = tmp_path / "invalid-coverage.jsonl"
    dataset.write_bytes(DATASET.read_bytes() * case_count)
    pack = tmp_path / "pack"
    runs = tmp_path / "runs"

    with pytest.raises(TraderRiskAuditReplayConfigurationError, match="exactly one"):
        run_trader_risk_audit_replay(
            dataset_path=dataset,
            evidence_path=EVIDENCE,
            provenance_path=PROVENANCE,
            evidence_dir=pack,
            run_dir=runs,
            run_id=f"invalid-{case_count}-case-coverage",
        )

    assert not pack.exists()
    assert not runs.exists()


def test_replay_packages_the_exact_validated_snapshots_when_paths_mutate_during_invoke(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dataset = tmp_path / "dataset.jsonl"
    evidence = tmp_path / "eval-evidence.json"
    provenance = tmp_path / "provenance.json"
    originals = {
        dataset: DATASET.read_bytes(),
        evidence: EVIDENCE.read_bytes(),
        provenance: PROVENANCE.read_bytes(),
    }
    for path, payload in originals.items():
        path.write_bytes(payload)

    class MutatingAdapter(TraderRiskAuditEvidenceAdapter):
        def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
            dataset.write_bytes(b"mutated after snapshot\n")
            evidence.write_bytes(b"{}\n")
            provenance.write_bytes(b"{}\n")
            return super().invoke(case)

    adapter = MutatingAdapter(evidence_path=evidence, provenance_path=provenance)
    pack = tmp_path / "pack"
    exit_code = run_trader_risk_audit_replay(
        dataset_path=dataset,
        evidence_path=evidence,
        provenance_path=provenance,
        evidence_dir=pack,
        run_dir=tmp_path / "runs",
        run_id="mutation-between-validation-and-packaging",
        adapter=adapter,
    )
    capsys.readouterr()

    assert exit_code == 0
    assert (pack / "inputs/dataset.jsonl").read_bytes() == originals[dataset]
    assert (pack / "inputs/eval-evidence.json").read_bytes() == originals[evidence]
    assert (pack / "inputs/source-provenance.json").read_bytes() == originals[provenance]
    verify_evidence_manifest(next(pack.glob("sha256-*.manifest.json")))


def test_replay_packages_the_locked_terminal_snapshot_when_run_paths_mutate_after_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, bytes] = {}
    original_complete = RunStore.complete_run_snapshot

    def complete_then_mutate(store: RunStore, run_id: str):  # noqa: ANN202
        snapshot = original_complete(store, run_id)
        captured["record"] = snapshot.record_bytes
        captured["seal"] = snapshot.seal_bytes
        (store.root / f"{run_id}.json").write_text('{"tampered":true}\n', encoding="utf-8")
        (store.root / f"{run_id}.sha256").write_text("tampered\n", encoding="utf-8")
        return snapshot

    monkeypatch.setattr(RunStore, "complete_run_snapshot", complete_then_mutate)
    pack = tmp_path / "pack"
    exit_code = run_trader_risk_audit_replay(
        dataset_path=DATASET,
        evidence_path=EVIDENCE,
        provenance_path=PROVENANCE,
        evidence_dir=pack,
        run_dir=tmp_path / "runs",
        run_id="terminal-output-mutation",
    )
    capsys.readouterr()

    packaged_run = pack / "run/terminal-output-mutation.json"
    packaged_seal = pack / "run/terminal-output-mutation.sha256"
    assert exit_code == 0
    assert packaged_run.read_bytes() == captured["record"]
    assert packaged_seal.read_bytes() == captured["seal"]
    run = _json(packaged_run)
    result = _json(pack / "replay-result.json")
    manifest = _json(next(pack.glob("sha256-*.manifest.json")))
    identity_fields = ("candidate_version", "dataset_hash", "run_id", "status", "validator_version")
    identity = {field: run[field] for field in identity_fields}
    assert identity == {field: manifest["metadata"]["run"][field] for field in identity_fields}
    assert identity == {field: result["run"][field] for field in identity_fields}
    assert (
        manifest["metadata"]["run"]["record_sha256"]
        == hashlib.sha256(captured["record"]).hexdigest()
    )
    assert (
        manifest["metadata"]["run"]["seal_sha256"] == hashlib.sha256(captured["seal"]).hexdigest()
    )
    verify_evidence_manifest(next(pack.glob("sha256-*.manifest.json")))


@pytest.mark.parametrize("payload_kind", ["raw_trades", "secret_metadata", "nested_expected"])
def test_unallowlisted_dataset_payload_is_rejected_before_output_directories(
    tmp_path: Path,
    payload_kind: str,
) -> None:
    case = json.loads(DATASET.read_text(encoding="utf-8"))
    if payload_kind == "raw_trades":
        case["raw_trades"] = [{"account_id": "secret"}]
    elif payload_kind == "secret_metadata":
        case["metadata"]["secret"] = "do-not-package"
    else:
        case["expected"]["evidence"]["metrics"]["secret"] = "do-not-package"
    dataset = tmp_path / "untrusted.jsonl"
    dataset.write_text(json.dumps(case, sort_keys=True) + "\n", encoding="utf-8")
    pack = tmp_path / "pack"
    runs = tmp_path / "runs"

    with pytest.raises((DatasetValidationError, TraderRiskAuditReplayConfigurationError)):
        run_trader_risk_audit_replay(
            dataset_path=dataset,
            evidence_path=EVIDENCE,
            provenance_path=PROVENANCE,
            evidence_dir=pack,
            run_dir=runs,
            run_id=f"untrusted-{payload_kind}",
        )

    assert not pack.exists()
    assert not runs.exists()


@pytest.mark.parametrize(
    ("suffix", "payload"),
    [
        (
            ".jsonl",
            '{"id":"synthetic-quickstart-v1","input":{"evidence_case_id":"first",'
            '"evidence_case_id":"second"},"expected":{},"metadata":{}}\n',
        ),
        (
            ".yaml",
            """
cases:
  - id: synthetic-quickstart-v1
    input:
      evidence_case_id: first
      evidence_case_id: second
    expected: {}
    metadata: {}
""",
        ),
    ],
)
def test_duplicate_dataset_keys_fail_before_output_directories(
    tmp_path: Path,
    suffix: str,
    payload: str,
) -> None:
    dataset = tmp_path / f"duplicate{suffix}"
    dataset.write_text(payload, encoding="utf-8")
    pack = tmp_path / "pack"
    runs = tmp_path / "runs"

    with pytest.raises(DatasetValidationError, match="duplicate key"):
        run_trader_risk_audit_replay(
            dataset_path=dataset,
            evidence_path=EVIDENCE,
            provenance_path=PROVENANCE,
            evidence_dir=pack,
            run_dir=runs,
            run_id=f"duplicate-{suffix[1:]}",
        )

    assert not pack.exists()
    assert not runs.exists()


def test_safe_but_false_provenance_source_path_cannot_pass(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    changed = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    changed["source"]["source_path"] = "examples/synthetic_quickstart/other.json"
    provenance = tmp_path / "changed-provenance.json"
    provenance.write_text(json.dumps(changed, sort_keys=True) + "\n", encoding="utf-8")
    pack = tmp_path / "pack"

    exit_code = run_trader_risk_audit_replay(
        dataset_path=DATASET,
        evidence_path=EVIDENCE,
        provenance_path=provenance,
        evidence_dir=pack,
        run_dir=tmp_path / "runs",
        run_id="false-source-path",
    )
    capsys.readouterr()
    result = _json(pack / "replay-result.json")

    assert exit_code == 1
    assert result["gate"]["passed"] is False
    assert result["cases"][0]["failed_validators"] == [
        "trader_risk_audit.source_provenance",
        "trader_risk_audit.evidence_identity",
    ]


def test_run_directory_cannot_be_nested_in_evidence_pack(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_dir"):
        run_trader_risk_audit_replay(
            dataset_path=DATASET,
            evidence_path=EVIDENCE,
            provenance_path=PROVENANCE,
            evidence_dir=tmp_path / "pack",
            run_dir=tmp_path / "pack/runs",
            run_id="invalid-layout",
        )


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)
