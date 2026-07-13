from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_ground_truth_lab import cli
from eval_ground_truth_lab.evidence import verify_evidence_manifest
from eval_ground_truth_lab.trader_replay import run_trader_risk_audit_replay

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
    assert manifest["metadata"]["gate_passed"] is True
    assert manifest["metadata"]["fixture"] is True
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
    assert exit_code == 1
    assert result["gate"] == {"failed_validator_count": 1, "passed": False}
    assert result["cases"][0]["failed_validators"] == ["trader_risk_audit.synthetic_metrics"]
    verify_evidence_manifest(next(pack.glob("sha256-*.manifest.json")))


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
