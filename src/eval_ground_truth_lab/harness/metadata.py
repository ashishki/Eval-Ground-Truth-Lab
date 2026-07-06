from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.compare import ComparisonReport


class HarnessMetadataMismatchError(ValueError):
    """Raised when harness metadata cannot support a fair comparison."""


@dataclass(frozen=True)
class HarnessConfig:
    harness_id: str
    harness_version: str
    model_class: str
    prompt_version: str
    tool_registry_version: str = "n/a"
    memory_policy_version: str = "n/a"
    permission_policy_version: str = "n/a"
    recovery_policy_version: str = "n/a"
    trace_schema_version: str = "n/a"
    environment_id: str = "local"

    def to_mapping(self) -> dict[str, str]:
        return {
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "model_class": self.model_class,
            "prompt_version": self.prompt_version,
            "tool_registry_version": self.tool_registry_version,
            "memory_policy_version": self.memory_policy_version,
            "permission_policy_version": self.permission_policy_version,
            "recovery_policy_version": self.recovery_policy_version,
            "trace_schema_version": self.trace_schema_version,
            "environment_id": self.environment_id,
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> HarnessConfig:
        return cls(
            harness_id=str(raw["harness_id"]),
            harness_version=str(raw["harness_version"]),
            model_class=str(raw["model_class"]),
            prompt_version=str(raw["prompt_version"]),
            tool_registry_version=str(raw.get("tool_registry_version", "n/a")),
            memory_policy_version=str(raw.get("memory_policy_version", "n/a")),
            permission_policy_version=str(raw.get("permission_policy_version", "n/a")),
            recovery_policy_version=str(raw.get("recovery_policy_version", "n/a")),
            trace_schema_version=str(raw.get("trace_schema_version", "n/a")),
            environment_id=str(raw.get("environment_id", "local")),
        )


@dataclass(frozen=True)
class HarnessRunMetadata:
    run_id: str
    dataset_hash: str
    scorer_version: str
    budget_usd: float
    harness: HarnessConfig

    def to_mapping(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset_hash": self.dataset_hash,
            "scorer_version": self.scorer_version,
            "budget_usd": self.budget_usd,
            "harness": self.harness.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> HarnessRunMetadata:
        return cls(
            run_id=str(raw["run_id"]),
            dataset_hash=str(raw["dataset_hash"]),
            scorer_version=str(raw["scorer_version"]),
            budget_usd=float(raw.get("budget_usd", 0.0)),
            harness=HarnessConfig.from_mapping(raw["harness"]),
        )


@dataclass(frozen=True)
class TraceCompletenessReport:
    required_event_types: tuple[str, ...]
    present_event_types: tuple[str, ...]
    missing_event_types: tuple[str, ...]
    event_count: int

    @property
    def is_complete(self) -> bool:
        return not self.missing_event_types

    def to_mapping(self) -> dict[str, Any]:
        return {
            "required_event_types": list(self.required_event_types),
            "present_event_types": list(self.present_event_types),
            "missing_event_types": list(self.missing_event_types),
            "event_count": self.event_count,
            "is_complete": self.is_complete,
        }


class TraceCompletenessValidator:
    def __init__(self, required_event_types: Iterable[str]) -> None:
        required = tuple(dict.fromkeys(required_event_types))
        if not required:
            raise ValueError("required_event_types must not be empty")
        self.required_event_types = required

    def validate(self, events: Iterable[Mapping[str, Any]]) -> TraceCompletenessReport:
        event_list = tuple(events)
        present = tuple(
            sorted(
                {
                    str(event.get("event_type"))
                    for event in event_list
                    if event.get("event_type") is not None
                }
            )
        )
        missing = tuple(
            event_type for event_type in self.required_event_types if event_type not in present
        )
        return TraceCompletenessReport(
            required_event_types=self.required_event_types,
            present_event_types=present,
            missing_event_types=missing,
            event_count=len(event_list),
        )


@dataclass(frozen=True)
class HarnessComparisonReport:
    metric_report: ComparisonReport
    baseline_metadata: HarnessRunMetadata
    candidate_metadata: HarnessRunMetadata
    baseline_trace: TraceCompletenessReport
    candidate_trace: TraceCompletenessReport

    @property
    def cost_budget_delta_usd(self) -> float:
        return self.candidate_metadata.budget_usd - self.baseline_metadata.budget_usd

    @property
    def has_blocking_failure(self) -> bool:
        return (
            self.metric_report.has_blocking_failure
            or not self.baseline_trace.is_complete
            or not self.candidate_trace.is_complete
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "baseline_run_id": self.baseline_metadata.run_id,
            "candidate_run_id": self.candidate_metadata.run_id,
            "dataset_hash": self.metric_report.dataset_hash,
            "baseline_harness": self.baseline_metadata.harness.to_mapping(),
            "candidate_harness": self.candidate_metadata.harness.to_mapping(),
            "scorer_version": self.baseline_metadata.scorer_version,
            "cost_budget_delta_usd": self.cost_budget_delta_usd,
            "baseline_trace": self.baseline_trace.to_mapping(),
            "candidate_trace": self.candidate_trace.to_mapping(),
            "threshold_status": self.metric_report.threshold_status,
            "has_blocking_failure": self.has_blocking_failure,
        }


def build_harness_comparison_report(
    *,
    metric_report: ComparisonReport,
    baseline_metadata: HarnessRunMetadata,
    candidate_metadata: HarnessRunMetadata,
    baseline_trace: TraceCompletenessReport,
    candidate_trace: TraceCompletenessReport,
) -> HarnessComparisonReport:
    _validate_metadata(metric_report, baseline_metadata, candidate_metadata)
    return HarnessComparisonReport(
        metric_report=metric_report,
        baseline_metadata=baseline_metadata,
        candidate_metadata=candidate_metadata,
        baseline_trace=baseline_trace,
        candidate_trace=candidate_trace,
    )


def _validate_metadata(
    metric_report: ComparisonReport,
    baseline_metadata: HarnessRunMetadata,
    candidate_metadata: HarnessRunMetadata,
) -> None:
    if baseline_metadata.run_id != metric_report.baseline_run_id:
        raise HarnessMetadataMismatchError("baseline harness metadata run_id mismatch")
    if candidate_metadata.run_id != metric_report.candidate_run_id:
        raise HarnessMetadataMismatchError("candidate harness metadata run_id mismatch")
    if baseline_metadata.dataset_hash != metric_report.dataset_hash:
        raise HarnessMetadataMismatchError("baseline harness metadata dataset_hash mismatch")
    if candidate_metadata.dataset_hash != metric_report.dataset_hash:
        raise HarnessMetadataMismatchError("candidate harness metadata dataset_hash mismatch")
    if baseline_metadata.scorer_version != candidate_metadata.scorer_version:
        raise HarnessMetadataMismatchError("baseline and candidate scorer_version must match")
