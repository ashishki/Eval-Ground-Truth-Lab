from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from eval_ground_truth_lab.runs import (
    CaseResult,
    DuplicateCaseResultError,
    DuplicateRunError,
    InvalidRunIdError,
    RunIntegrityError,
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


def test_completed_run_rejects_mutation(tmp_path) -> None:
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


def test_complete_run_snapshot_returns_the_exact_terminal_bytes(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = _create_run(store, "terminal-snapshot")

    snapshot = store.complete_run_snapshot(record.run_id)

    assert snapshot.record.status == "completed"
    assert snapshot.record_bytes == (tmp_path / "terminal-snapshot.json").read_bytes()
    assert snapshot.seal_bytes == (tmp_path / "terminal-snapshot.sha256").read_bytes()
    assert (
        snapshot.seal_bytes
        == (
            f"sha256:{hashlib.sha256(snapshot.record_bytes).hexdigest()}  terminal-snapshot.json\n"
        ).encode()
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


def test_interrupted_run_preserves_results_and_rejects_mutation(tmp_path) -> None:
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


@pytest.mark.parametrize(
    "run_id",
    ("../escaped", "nested/run", "/absolute", ".", "..", " space", "run id"),
)
def test_unsafe_run_id_is_rejected_without_writing_outside_root(tmp_path, run_id) -> None:
    with pytest.raises(InvalidRunIdError):
        _create_run(RunStore(tmp_path), run_id)

    assert not (tmp_path.parent / "escaped.json").exists()


def test_concurrent_create_has_exactly_one_winner(tmp_path) -> None:
    def create() -> str:
        try:
            _create_run(RunStore(tmp_path), "concurrent-run")
        except DuplicateRunError:
            return "duplicate"
        return "created"

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: create(), range(16)))

    assert outcomes.count("created") == 1
    assert outcomes.count("duplicate") == 15
    assert RunStore(tmp_path).get_run("concurrent-run").status == "running"


def test_terminal_run_detects_modified_record(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = _create_run(store, "sealed-run")
    store.complete_run(record.run_id)
    run_path = tmp_path / "sealed-run.json"
    raw = json.loads(run_path.read_text(encoding="utf-8"))
    raw["dataset_hash"] = "tampered"
    run_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(RunIntegrityError, match="checksum"):
        store.get_run(record.run_id)


def test_terminal_run_detects_deleted_seal(tmp_path) -> None:
    store = RunStore(tmp_path)
    record = _create_run(store, "missing-seal")
    store.complete_run(record.run_id)
    (tmp_path / "missing-seal.sha256").unlink()

    with pytest.raises(RunIntegrityError, match="no checksum seal"):
        store.get_run(record.run_id)


def test_failed_atomic_replace_preserves_previous_record(tmp_path, monkeypatch) -> None:
    store = RunStore(tmp_path)
    record = _create_run(store, "atomic-run")
    before = (tmp_path / "atomic-run.json").read_bytes()

    def fail_replace(_source, _destination) -> None:  # noqa: ANN001
        raise OSError("simulated replace interruption")

    monkeypatch.setattr("eval_ground_truth_lab.runs.store.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        store.add_case_result(record.run_id, CaseResult(case_id="case-1", output={}))

    assert (tmp_path / "atomic-run.json").read_bytes() == before


def _create_run(store: RunStore, run_id: str):  # noqa: ANN201
    return store.create_run(
        run_id=run_id,
        run_type="candidate",
        dataset_hash="dataset",
        candidate_version="candidate",
        validator_version="validators",
        threshold_config_version="thresholds",
    )
