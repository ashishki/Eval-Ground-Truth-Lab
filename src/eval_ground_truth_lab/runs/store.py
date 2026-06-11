from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

RUNNING = "running"
COMPLETED = "completed"
INTERRUPTED = "interrupted"


class RunStoreError(RuntimeError):
    """Base error for run storage failures."""


class RunMutationError(RunStoreError):
    """Raised when an immutable or terminal run is mutated."""


class DuplicateCaseResultError(RunStoreError):
    """Raised when a run receives more than one result for the same case."""


class DuplicateRunError(RunStoreError):
    """Raised when a run ID would overwrite an existing run record."""


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
        if self._path_for(new_run_id).exists():
            raise DuplicateRunError(f"Run {new_run_id} already exists")

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
        self._write(record)
        return record

    def get_run(self, run_id: str) -> RunRecord:
        path = self._path_for(run_id)
        with path.open(encoding="utf-8") as run_file:
            return RunRecord.from_mapping(json.load(run_file))

    def add_case_result(self, run_id: str, case_result: CaseResult) -> RunRecord:
        record = self.get_run(run_id)
        self._ensure_mutable(record)

        if any(existing.case_id == case_result.case_id for existing in record.case_results):
            raise DuplicateCaseResultError(
                f"Run {run_id} already has a result for case {case_result.case_id}"
            )

        updated_results = (*record.case_results, case_result)
        updated = _replace_metrics(record, case_results=updated_results)
        self._write(updated)
        return updated

    def complete_run(self, run_id: str) -> RunRecord:
        record = self.get_run(run_id)
        self._ensure_mutable(record)
        raw = record.to_mapping()
        raw.update({"status": COMPLETED, "completed_at": _now_iso()})
        updated = RunRecord.from_mapping(raw)
        self._write(updated)
        return updated

    def interrupt_run(self, run_id: str) -> RunRecord:
        record = self.get_run(run_id)
        self._ensure_mutable(record)
        raw = record.to_mapping()
        raw.update({"status": INTERRUPTED, "interrupted_at": _now_iso()})
        updated = RunRecord.from_mapping(raw)
        self._write(updated)
        return updated

    def _ensure_mutable(self, record: RunRecord) -> None:
        if record.status in {COMPLETED, INTERRUPTED}:
            raise RunMutationError(f"Run {record.run_id} is immutable with status {record.status}")

    def _write(self, record: RunRecord) -> None:
        path = self._path_for(record.run_id)
        with path.open("w", encoding="utf-8") as run_file:
            json.dump(record.to_mapping(), run_file, indent=2, sort_keys=True)
            run_file.write("\n")

    def _path_for(self, run_id: str) -> Path:
        return self.root / f"{run_id}.json"


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
