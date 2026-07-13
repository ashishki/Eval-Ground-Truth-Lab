from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import math
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from eval_ground_truth_lab.execution_binding import EXECUTION_BINDING_SHA256

LOADED_EXECUTION_BINDING_SHA256 = EXECUTION_BINDING_SHA256

RUNNING = "running"
COMPLETED = "completed"
INTERRUPTED = "interrupted"


class RunStoreError(RuntimeError):
    """Base error for run storage failures."""


class RunMutationError(RunStoreError):
    """Raised when a terminal run is mutated through RunStore."""


class DuplicateCaseResultError(RunStoreError):
    """Raised when a run receives more than one result for the same case."""


class DuplicateRunError(RunStoreError):
    """Raised when a run ID would overwrite an existing run record."""


class InvalidRunIdError(RunStoreError):
    """Raised when a run ID is unsafe for use as a filesystem identifier."""


class RunIntegrityError(RunStoreError):
    """Raised when a terminal run no longer matches its recorded checksum."""


_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    output: Any
    validator_results: tuple[dict[str, Any], ...] = ()
    cost_usd: float = 0.0
    latency_ms: float = 0.0

    def to_mapping(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "output": self.output,
            "validator_results": list(self.validator_results),
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> CaseResult:
        return cls(
            case_id=str(raw["case_id"]),
            output=raw.get("output"),
            validator_results=tuple(raw.get("validator_results", ())),
            cost_usd=float(raw.get("cost_usd", 0.0)),
            latency_ms=float(raw.get("latency_ms", 0.0)),
        )


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    run_type: str
    dataset_hash: str
    candidate_version: str
    validator_version: str
    threshold_config_version: str
    status: str
    started_at: str
    completed_at: str | None = None
    interrupted_at: str | None = None
    cost_total_usd: float = 0.0
    cost_per_case_usd: float = 0.0
    latency_ms_p50: float = 0.0
    latency_ms_p95: float = 0.0
    max_candidate_retries: int = 1
    case_results: tuple[CaseResult, ...] = field(default_factory=tuple)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "dataset_hash": self.dataset_hash,
            "candidate_version": self.candidate_version,
            "validator_version": self.validator_version,
            "threshold_config_version": self.threshold_config_version,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "interrupted_at": self.interrupted_at,
            "cost_total_usd": self.cost_total_usd,
            "cost_per_case_usd": self.cost_per_case_usd,
            "latency_ms_p50": self.latency_ms_p50,
            "latency_ms_p95": self.latency_ms_p95,
            "max_candidate_retries": self.max_candidate_retries,
            "case_results": [case_result.to_mapping() for case_result in self.case_results],
        }

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> RunRecord:
        return cls(
            run_id=str(raw["run_id"]),
            run_type=str(raw["run_type"]),
            dataset_hash=str(raw["dataset_hash"]),
            candidate_version=str(raw["candidate_version"]),
            validator_version=str(raw["validator_version"]),
            threshold_config_version=str(raw["threshold_config_version"]),
            status=str(raw["status"]),
            started_at=str(raw["started_at"]),
            completed_at=raw.get("completed_at"),
            interrupted_at=raw.get("interrupted_at"),
            cost_total_usd=float(raw.get("cost_total_usd", 0.0)),
            cost_per_case_usd=float(raw.get("cost_per_case_usd", 0.0)),
            latency_ms_p50=float(raw.get("latency_ms_p50", 0.0)),
            latency_ms_p95=float(raw.get("latency_ms_p95", 0.0)),
            max_candidate_retries=int(raw.get("max_candidate_retries", 1)),
            case_results=tuple(
                CaseResult.from_mapping(case_result) for case_result in raw.get("case_results", ())
            ),
        )


@dataclass(frozen=True)
class TerminalRunSnapshot:
    """Exact terminal bytes published by RunStore while holding the run lock."""

    record_bytes: bytes
    seal_bytes: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_bytes", bytes(self.record_bytes))
        object.__setattr__(self, "seal_bytes", bytes(self.seal_bytes))

    @property
    def record(self) -> RunRecord:
        raw = json.loads(self.record_bytes)
        if not isinstance(raw, dict):
            raise RunIntegrityError("Terminal run snapshot must contain a JSON object")
        return RunRecord.from_mapping(raw)


class RunStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_run(
        self,
        *,
        run_type: str,
        dataset_hash: str,
        candidate_version: str,
        validator_version: str,
        threshold_config_version: str,
        run_id: str | None = None,
        max_candidate_retries: int = 1,
    ) -> RunRecord:
        if max_candidate_retries < 0:
            raise ValueError("max_candidate_retries must be non-negative")

        new_run_id = run_id or str(uuid4())
        self._validate_run_id(new_run_id)
        with self._lock(new_run_id):
            record = RunRecord(
                run_id=new_run_id,
                run_type=run_type,
                dataset_hash=dataset_hash,
                candidate_version=candidate_version,
                validator_version=validator_version,
                threshold_config_version=threshold_config_version,
                status=RUNNING,
                started_at=_now_iso(),
                max_candidate_retries=max_candidate_retries,
            )
            self._write_exclusive(record)
        return record

    def get_run(self, run_id: str) -> RunRecord:
        self._validate_run_id(run_id)
        with self._lock(run_id):
            return self._read(run_id)

    def _read(self, run_id: str) -> RunRecord:
        path = self._path_for(run_id)
        with path.open(encoding="utf-8") as run_file:
            record = RunRecord.from_mapping(json.load(run_file))
        if record.run_id != run_id:
            raise RunIntegrityError(
                f"Run record ID {record.run_id!r} does not match requested ID {run_id!r}"
            )
        if record.status in {COMPLETED, INTERRUPTED}:
            self._verify_terminal_seal(record)
        return record

    def add_case_result(self, run_id: str, case_result: CaseResult) -> RunRecord:
        self._validate_run_id(run_id)
        with self._lock(run_id):
            record = self._read(run_id)
            self._ensure_mutable(record)

            if any(existing.case_id == case_result.case_id for existing in record.case_results):
                raise DuplicateCaseResultError(
                    f"Run {run_id} already has a result for case {case_result.case_id}"
                )

            updated_results = (*record.case_results, case_result)
            updated = _replace_metrics(record, case_results=updated_results)
            self._write_atomic(updated)
        return updated

    def complete_run(self, run_id: str) -> RunRecord:
        return self.complete_run_snapshot(run_id).record

    def complete_run_snapshot(self, run_id: str) -> TerminalRunSnapshot:
        self._validate_run_id(run_id)
        with self._lock(run_id):
            record = self._read(run_id)
            self._ensure_mutable(record)
            raw = record.to_mapping()
            raw.update({"status": COMPLETED, "completed_at": _now_iso()})
            updated = RunRecord.from_mapping(raw)
            snapshot = self._write_terminal(updated)
        return snapshot

    def interrupt_run(self, run_id: str) -> RunRecord:
        self._validate_run_id(run_id)
        with self._lock(run_id):
            record = self._read(run_id)
            self._ensure_mutable(record)
            raw = record.to_mapping()
            raw.update({"status": INTERRUPTED, "interrupted_at": _now_iso()})
            updated = RunRecord.from_mapping(raw)
            snapshot = self._write_terminal(updated)
        return snapshot.record

    def _ensure_mutable(self, record: RunRecord) -> None:
        if record.status in {COMPLETED, INTERRUPTED}:
            raise RunMutationError(f"Run {record.run_id} is terminal with status {record.status}")

    def _write_exclusive(self, record: RunRecord) -> None:
        path = self._path_for(record.run_id)
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise DuplicateRunError(f"Run {record.run_id} already exists") from exc
        os.close(descriptor)
        try:
            self._write_atomic(record)
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def _write_terminal(self, record: RunRecord) -> TerminalRunSnapshot:
        payload = _record_bytes(record)
        digest = hashlib.sha256(payload).hexdigest()
        seal = f"sha256:{digest}  {record.run_id}.json\n".encode()
        # Publish the seal first. Readers serialize on the lock, so they can
        # never observe a terminal record without its matching seal.
        self._write_bytes_atomic(self._seal_path_for(record.run_id), seal)
        self._write_bytes_atomic(self._path_for(record.run_id), payload)
        return TerminalRunSnapshot(record_bytes=payload, seal_bytes=seal)

    def _write_atomic(self, record: RunRecord) -> None:
        self._write_bytes_atomic(self._path_for(record.run_id), _record_bytes(record))

    def _write_bytes_atomic(self, path: Path, payload: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.root,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, path)
            _fsync_directory(self.root)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _verify_terminal_seal(self, record: RunRecord) -> None:
        seal_path = self._seal_path_for(record.run_id)
        try:
            seal = seal_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise RunIntegrityError(f"Terminal run {record.run_id} has no checksum seal") from exc
        expected = (
            f"sha256:{hashlib.sha256(_record_bytes(record)).hexdigest()}  {record.run_id}.json"
        )
        if not hmac.compare_digest(seal, expected):
            raise RunIntegrityError(f"Terminal run {record.run_id} failed checksum verification")

    @contextmanager
    def _lock(self, run_id: str) -> Iterator[None]:
        lock_root = self.root / ".locks"
        lock_root.mkdir(exist_ok=True)
        lock_path = lock_root / f"{run_id}.lock"
        with lock_path.open("a+b") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _validate_run_id(self, run_id: str) -> None:
        if not _RUN_ID_PATTERN.fullmatch(run_id) or run_id in {".", ".."}:
            raise InvalidRunIdError(
                "run_id must be 1-128 characters, start with an alphanumeric "
                "character, and contain only alphanumerics, '.', '_' or '-'"
            )

    def _path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"

    def _seal_path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.sha256"


def _replace_metrics(record: RunRecord, *, case_results: tuple[CaseResult, ...]) -> RunRecord:
    total_cost = sum(result.cost_usd for result in case_results)
    case_count = len(case_results)
    latencies = [result.latency_ms for result in case_results]
    raw = record.to_mapping()
    raw.update(
        {
            "cost_total_usd": total_cost,
            "cost_per_case_usd": total_cost / case_count if case_count else 0.0,
            "latency_ms_p50": _percentile(latencies, 0.50),
            "latency_ms_p95": _percentile(latencies, 0.95),
            "case_results": [case_result.to_mapping() for case_result in case_results],
        }
    )
    return RunRecord.from_mapping(raw)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _record_bytes(record: RunRecord) -> bytes:
    return (json.dumps(record.to_mapping(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
