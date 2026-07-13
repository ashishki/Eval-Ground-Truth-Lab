from __future__ import annotations

import json

import pytest

from eval_ground_truth_lab.cli import main
from eval_ground_truth_lab.evidence import (
    EvidenceError,
    EvidenceVerificationError,
    verify_evidence_manifest,
    write_evidence_manifest,
)


def test_content_addressed_manifest_verifies_and_cli_reports_it(tmp_path, capsys) -> None:
    manifest = _pack(tmp_path)

    result = verify_evidence_manifest(manifest)
    exit_code = main(["verify-evidence", "--manifest", str(manifest)])
    cli_result = json.loads(capsys.readouterr().out)

    assert result.artifact_count == 2
    assert manifest.name == result.content_address.replace(":", "-") + ".manifest.json"
    assert exit_code == 0
    assert cli_result["verified"] is True
    assert cli_result["content_address"] == result.content_address


def test_manifest_detects_modified_artifact(tmp_path) -> None:
    manifest = _pack(tmp_path)
    (tmp_path / "result.json").write_text('{"changed":true}\n', encoding="utf-8")

    with pytest.raises(EvidenceVerificationError, match="changed"):
        verify_evidence_manifest(manifest)


def test_manifest_detects_deleted_artifact(tmp_path) -> None:
    manifest = _pack(tmp_path)
    (tmp_path / "report.md").unlink()

    with pytest.raises(EvidenceVerificationError, match="missing"):
        verify_evidence_manifest(manifest)


def test_manifest_detects_undeclared_addition(tmp_path) -> None:
    manifest = _pack(tmp_path)
    (tmp_path / "undeclared.txt").write_text("not declared", encoding="utf-8")

    with pytest.raises(EvidenceVerificationError, match="undeclared"):
        verify_evidence_manifest(manifest)


def test_manifest_rejects_unsafe_artifact_path(tmp_path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(EvidenceError, match="safe relative"):
        write_evidence_manifest(tmp_path, ["../outside.txt"], metadata={"kind": "test"})


def _pack(root):  # noqa: ANN001, ANN201
    (root / "result.json").write_text('{"gate":"pass"}\n', encoding="utf-8")
    (root / "report.md").write_text("# report\n", encoding="utf-8")
    return write_evidence_manifest(
        root,
        ["result.json", "report.md"],
        metadata={"fixture": True},
    )
