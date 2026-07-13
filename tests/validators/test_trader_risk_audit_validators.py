from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from eval_ground_truth_lab.adapters import TraderRiskAuditEvidenceAdapter
from eval_ground_truth_lab.datasets import load_dataset
from eval_ground_truth_lab.validators import validate_trader_risk_audit_case

ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = ROOT / "datasets/trader_risk_audit"


def test_exact_synthetic_expectations_pass_all_validators() -> None:
    case, output = _case_and_output()

    results = validate_trader_risk_audit_case(
        case_id=case.id,
        expected=case.expected,
        actual=output,
    )

    assert len(results) == 7
    assert all(result.passed for result in results)
    assert {result.category for result in results} == {"none"}


def test_source_revision_mismatch_is_a_blocking_provenance_failure() -> None:
    case, output = _case_and_output()
    changed = deepcopy(output)
    changed["source"]["git_commit"] = "0" * 40

    results = validate_trader_risk_audit_case(
        case_id=case.id,
        expected=case.expected,
        actual=changed,
    )

    failed = [result for result in results if not result.passed]
    assert [result.validator_id for result in failed] == ["trader_risk_audit.source_provenance"]
    assert failed[0].category == "provenance_mismatch"


def test_unknown_adapter_output_field_fails_structured_output() -> None:
    case, output = _case_and_output()
    output["raw_trades"] = []

    results = validate_trader_risk_audit_case(
        case_id=case.id,
        expected=case.expected,
        actual=output,
    )

    assert len(results) == 1
    assert results[0].passed is False
    assert results[0].category == "invalid_structured_output"


def _case_and_output():  # noqa: ANN202
    dataset = load_dataset(DATASET_ROOT / "synthetic_quickstart_v1.jsonl")
    case = dataset.cases[0]
    adapter = TraderRiskAuditEvidenceAdapter(
        evidence_path=(DATASET_ROOT / "fixtures/synthetic_quickstart_v1/eval-evidence.json"),
        provenance_path=DATASET_ROOT / "synthetic_quickstart_v1.provenance.json",
    )
    output = adapter.invoke(case.to_canonical_mapping()).output
    assert isinstance(output, dict)
    return case, output
