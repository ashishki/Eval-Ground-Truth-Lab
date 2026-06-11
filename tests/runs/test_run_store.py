from __future__ import annotations

import pytest

from eval_ground_truth_lab.runs import (
    CaseResult,
    DuplicateCaseResultError,
    DuplicateRunError,
    RunMutationError,
    RunStore,
)


def test_run_record_persists_required_metadata(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = store.create_run(
        run_id="run-001",
        run_type="candidate",
        dataset_hash="abc123",
        candidate_version="candidate-v1",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
    )
    updated = store.add_case_result(
        record.run_id,
        CaseResult(
            case_id="case-001",
            output={"category": "billing"},
            cost_usd=0.25,
            latency_ms=120.0,
        ),
    )

    reloaded = RunStore(tmp_path).get_run(updated.run_id)

    assert reloaded.run_id == "run-001"
    assert reloaded.run_type == "candidate"
    assert reloaded.dataset_hash == "abc123"
    assert reloaded.candidate_version == "candidate-v1"
    assert reloaded.validator_version == "validators-v1"
    assert reloaded.threshold_config_version == "thresholds-v1"
    assert reloaded.status == "running"
    assert reloaded.started_at
    assert reloaded.completed_at is None
    assert reloaded.cost_total_usd == 0.25
    assert reloaded.cost_per_case_usd == 0.25
    assert reloaded.latency_ms_p50 == 120.0
    assert reloaded.latency_ms_p95 == 120.0
    assert reloaded.max_candidate_retries == 1


def test_completed_run_is_immutable(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = store.create_run(
        run_id="run-002",
        run_type="baseline",
        dataset_hash="def456",
        candidate_version="baseline-v1",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
    )
    completed = store.complete_run(record.run_id)

    with pytest.raises(RunMutationError):
        store.add_case_result(
            completed.run_id,
            CaseResult(case_id="case-001", output={"category": "account_access"}),
        )


def test_duplicate_case_result_rejected(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = store.create_run(
        run_id="run-003",
        run_type="candidate",
        dataset_hash="ghi789",
        candidate_version="candidate-v2",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
    )
    store.add_case_result(
        record.run_id,
        CaseResult(case_id="case-001", output={"category": "billing"}),
    )

    with pytest.raises(DuplicateCaseResultError):
        store.add_case_result(
            record.run_id,
            CaseResult(case_id="case-001", output={"category": "billing"}),
        )


def test_interrupted_run_preserves_results_and_is_immutable(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = store.create_run(
        run_id="run-004",
        run_type="candidate",
        dataset_hash="jkl012",
        candidate_version="candidate-v3",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
    )
    store.add_case_result(
        record.run_id,
        CaseResult(case_id="case-001", output={"category": "support"}),
    )

    interrupted = store.interrupt_run(record.run_id)
    reloaded = RunStore(tmp_path).get_run(record.run_id)

    assert interrupted.status == "interrupted"
    assert interrupted.interrupted_at
    assert reloaded.case_results[0].case_id == "case-001"
    with pytest.raises(RunMutationError):
        store.add_case_result(
            record.run_id,
            CaseResult(case_id="case-002", output={"category": "billing"}),
        )


def test_existing_run_id_cannot_be_overwritten(tmp_path) -> None:
    store = RunStore(tmp_path)
    store.create_run(
        run_id="run-005",
        run_type="candidate",
        dataset_hash="mno345",
        candidate_version="candidate-v4",
        validator_version="validators-v1",
        threshold_config_version="thresholds-v1",
    )

    with pytest.raises(DuplicateRunError):
        store.create_run(
            run_id="run-005",
            run_type="candidate",
            dataset_hash="changed",
            candidate_version="candidate-v5",
            validator_version="validators-v1",
            threshold_config_version="thresholds-v1",
        )
