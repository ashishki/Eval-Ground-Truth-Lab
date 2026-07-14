from __future__ import annotations

import json
from pathlib import Path

from eval_ground_truth_lab import cli as cli_module
from eval_ground_truth_lab import evidence as evidence_module
from eval_ground_truth_lab import execution_binding as execution_binding_module
from eval_ground_truth_lab import implementation_provenance as provenance_module
from eval_ground_truth_lab import trader_replay as trader_replay_module
from eval_ground_truth_lab.compare import comparison as comparison_module
from eval_ground_truth_lab.compare import contracts as contracts_module
from eval_ground_truth_lab.evidence import verify_evidence_manifest
from eval_ground_truth_lab.implementation_provenance import build_implementation_provenance
from eval_ground_truth_lab.reports import markdown as markdown_module
from eval_ground_truth_lab.runs import store as run_store_module

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_COMMIT = "31120c809cc4935c9f5ffbb2cb539a3018d38d92"
IMPLEMENTATION_TREE = "8cbbff195bbae0ee5309d94c38ad27e8215c755e"
EXECUTION_BINDING = "423d9bc2bf89438b147485f88b4b251b6c872d62b00fea998c97904828da15b3"

TRADER_PACK = ROOT / "docs/evidence/integrations/trader-risk-audit-synthetic-v2"
TRADER_MANIFEST = TRADER_PACK / (
    "sha256-b8269aa9b416f78817a0c69848c6a4bd24957f7016e2d1c4951dee9cb7430496.manifest.json"
)
RELEASE_PACK = ROOT / "docs/evidence/releases/v0.2.1"
RELEASE_MANIFEST = RELEASE_PACK / (
    "sha256-c07918b3d598e30840ad14f04fe4bc434c7dd71f9e72a83fe294a7bbdf20a2c6.manifest.json"
)


def test_v021_manifests_have_the_reviewed_content_addresses() -> None:
    trader = verify_evidence_manifest(TRADER_MANIFEST)
    release = verify_evidence_manifest(RELEASE_MANIFEST)

    assert trader.artifact_count == 8
    assert trader.content_address == (
        "sha256:b8269aa9b416f78817a0c69848c6a4bd24957f7016e2d1c4951dee9cb7430496"
    )
    assert release.artifact_count == 17
    assert release.content_address == (
        "sha256:c07918b3d598e30840ad14f04fe4bc434c7dd71f9e72a83fe294a7bbdf20a2c6"
    )


def test_trader_v2_binds_implementation_commit_and_current_package_bytes() -> None:
    result = _json(TRADER_PACK / "replay-result.json")
    manifest = _json(TRADER_MANIFEST)
    recorded = result["provenance"]["implementation"]
    current = trader_replay_module._capture_and_verify_loaded_implementation()

    _assert_recorded_implementation_source(recorded)
    assert manifest["metadata"]["implementation"] == recorded
    assert current["components_sha256"] == recorded["components_sha256"]
    assert current["package_payload"] == recorded["package_payload"]
    assert current["execution_binding"] == recorded["execution_binding"]
    assert result["gate"] == {"failed_validator_count": 0, "passed": True}
    assert result["scope"] == {
        "applies_financial_advice": False,
        "evaluates_raw_trades": False,
        "external_user_case_study": False,
        "production_evidence": False,
        "replay_type": "pinned_synthetic_sanitized_export",
    }


def test_release_pack_binds_current_comparison_package_to_implementation_commit() -> None:
    receipt = _json(RELEASE_PACK / "receipts/command-results.json")
    manifest = _json(RELEASE_MANIFEST)
    recorded = receipt["implementation"]
    current = build_implementation_provenance(
        component_paths={
            "cli": Path(cli_module.__file__),
            "comparison": Path(comparison_module.__file__),
            "comparison_contracts": Path(contracts_module.__file__),
            "evidence_manifest": Path(evidence_module.__file__),
            "execution_binding": Path(execution_binding_module.__file__),
            "implementation_provenance": Path(provenance_module.__file__),
            "markdown_renderer": Path(markdown_module.__file__),
            "run_store": Path(run_store_module.__file__),
        },
        package_root=Path(cli_module.__file__).parent,
        require_execution_binding=True,
    )

    _assert_recorded_implementation_source(recorded)
    assert manifest["metadata"]["implementation"] == recorded
    assert current["components_sha256"] == recorded["components_sha256"]
    assert current["package_payload"] == recorded["package_payload"]
    assert current["execution_binding"] == recorded["execution_binding"]
    assert receipt["release"] == {
        "classification": "internal_correctness_and_security_patch",
        "external_feedback_maintenance_evidence": False,
        "version": "0.2.1",
    }


def test_release_receipt_proves_cli_statuses_exact_gates_and_stale_removal() -> None:
    receipt = _json(RELEASE_PACK / "receipts/command-results.json")
    scenarios = {scenario["name"]: scenario for scenario in receipt["scenarios"]}

    assert {scenario["exit_code"] for scenario in scenarios.values()} == {0, 1, 2}
    assert scenarios["valid_no_regression"]["exit_code"] == 0
    valid = scenarios["valid_no_regression"]["decision"]
    assert set(valid["threshold_status"].values()) == {"pass"}
    assert set(valid["exact_deltas"].values()) == {"0"}
    assert valid["validator_receipt_regressions"] == []

    generic = scenarios["generic_validator_pass_to_fail"]
    assert generic["exit_code"] == 1
    assert set(generic["decision"]["threshold_status"].values()) == {"pass"}
    assert generic["decision"]["validator_receipt_regressions"] == [
        {
            "candidate_category": "arbitrary_validator_regression",
            "case_id": "case-1",
            "validator_id": "evidence.output_contract",
        }
    ]

    decimal = scenarios["high_magnitude_decimal_cancellation"]
    assert decimal["exit_code"] == 1
    assert decimal["decision"]["exact_deltas"]["cost_per_case_delta"] == "0.1"
    assert decimal["decision"]["exact_thresholds"]["cost_per_case_delta"] == "0.09999"
    assert decimal["decision"]["threshold_status"]["cost_per_case_delta"] == "fail"

    one_third = scenarios["exact_one_third_boundary"]
    assert one_third["exit_code"] == 1
    assert one_third["decision"]["exact_deltas"]["accuracy_delta"] == "-1/3"
    assert one_third["decision"]["exact_thresholds"]["accuracy_delta"] == ("0.3333333333333333")
    assert one_third["decision"]["threshold_status"]["accuracy_delta"] == "fail"

    invalid = scenarios["invalid_input_stale_report_invalidation"]
    assert invalid["exit_code"] == 2
    assert invalid["decision"] is None
    assert invalid["stale_report_removed"] is True
    assert invalid["report_exists_after"] is False
    assert "duplicate key 'validator_id'" in invalid["stderr"]
    assert not (RELEASE_PACK / "reports/invalid-input-must-not-exist.md").exists()


def test_v021_packs_have_no_workstation_or_secret_markers() -> None:
    forbidden = (
        b"/home/",
        b"/Users/",
        b"OPENAI_API_KEY",
        b"ANTHROPIC_API_KEY",
        b"BEGIN PRIVATE KEY",
        b"account_id",
        b"api_key",
        b"private_key",
        b"trades.csv",
    )
    for pack in (TRADER_PACK, RELEASE_PACK):
        for path in pack.rglob("*"):
            if path.is_file():
                raw = path.read_bytes().lower()
                assert not any(marker.lower() in raw for marker in forbidden), path


def _assert_recorded_implementation_source(recorded: dict[str, object]) -> None:
    assert recorded["source"] == {
        "commit": IMPLEMENTATION_COMMIT,
        "kind": "git_worktree",
        "measured_package_matches_head": True,
        "tree": IMPLEMENTATION_TREE,
    }
    assert recorded["execution_binding"] == {
        "schema_version": "eval-lab-loaded-execution-binding-v1",
        "sha256": EXECUTION_BINDING,
    }


def _json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as source:
        return json.load(source)
