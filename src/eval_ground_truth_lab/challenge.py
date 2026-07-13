from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from eval_ground_truth_lab.adapters.base import AdapterResult
from eval_ground_truth_lab.datasets import Dataset
from eval_ground_truth_lab.runs import RunRecord

CHALLENGE_SCHEMA_VERSION = "gdev-agent-challenge-run-v1"
PROVIDER_ERROR_SLICE = "provider_error_simulation"
BLOCKING_CATEGORIES = frozenset(
    {
        "adapter_error",
        "guard_expected_but_not_triggered",
        "invalid_structured_output",
        "missing_required_field",
        "unsafe_auto_approval",
    }
)


class ChallengeConfigurationError(ValueError):
    """Raised when challenge data or threshold configuration is incomplete."""


class CandidateAdapter(Protocol):
    def invoke(self, case: Mapping[str, Any]) -> AdapterResult: ...


@dataclass(frozen=True)
class ChallengeThresholds:
    version: str
    blocking_failure_count_max: int
    classification_accuracy_min: float
    expected_failure_matched_min: float
    human_review_required_count_min: int
    human_escalation_recall_min: float
    judge_optional_cases_max: int
    max_cost_per_case_usd: float
    max_invalid_structured_output_rate: float
    max_latency_p95_ms: float
    max_unsafe_auto_approval_rate: float
    unexpected_fail_count_max: int
    unexpected_pass_count_max: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ChallengeThresholds:
        expected = set(cls.__dataclass_fields__)
        missing = sorted(expected - set(raw))
        unknown = sorted(set(raw) - expected)
        if missing or unknown:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unknown:
                details.append("unknown: " + ", ".join(unknown))
            raise ChallengeConfigurationError(
                "Invalid challenge thresholds (" + "; ".join(details) + ")"
            )
        return cls(
            version=_required_string(raw["version"], "version"),
            blocking_failure_count_max=_non_negative_int(
                raw["blocking_failure_count_max"], "blocking_failure_count_max"
            ),
            classification_accuracy_min=_rate(
                raw["classification_accuracy_min"], "classification_accuracy_min"
            ),
            expected_failure_matched_min=_rate(
                raw["expected_failure_matched_min"], "expected_failure_matched_min"
            ),
            human_review_required_count_min=_non_negative_int(
                raw["human_review_required_count_min"], "human_review_required_count_min"
            ),
            human_escalation_recall_min=_rate(
                raw["human_escalation_recall_min"], "human_escalation_recall_min"
            ),
            judge_optional_cases_max=_non_negative_int(
                raw["judge_optional_cases_max"], "judge_optional_cases_max"
            ),
            max_cost_per_case_usd=_non_negative_float(
                raw["max_cost_per_case_usd"], "max_cost_per_case_usd"
            ),
            max_invalid_structured_output_rate=_rate(
                raw["max_invalid_structured_output_rate"],
                "max_invalid_structured_output_rate",
            ),
            max_latency_p95_ms=_non_negative_float(raw["max_latency_p95_ms"], "max_latency_p95_ms"),
            max_unsafe_auto_approval_rate=_rate(
                raw["max_unsafe_auto_approval_rate"], "max_unsafe_auto_approval_rate"
            ),
            unexpected_fail_count_max=_non_negative_int(
                raw["unexpected_fail_count_max"], "unexpected_fail_count_max"
            ),
            unexpected_pass_count_max=_non_negative_int(
                raw["unexpected_pass_count_max"], "unexpected_pass_count_max"
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


class FaultInjectingAdapter:
    """Inject only declared provider-failure cases; delegate every other case."""

    def __init__(
        self,
        delegate: CandidateAdapter,
        *,
        fault_cost_usd: float,
        fault_latency_ms: float,
    ) -> None:
        self._delegate = delegate
        self._fault_cost_usd = fault_cost_usd
        self._fault_latency_ms = fault_latency_ms

    def invoke(self, case: Mapping[str, Any]) -> AdapterResult:
        metadata = _mapping(case.get("metadata"), "metadata")
        if metadata.get("slice") != PROVIDER_ERROR_SLICE:
            result = self._delegate.invoke(case)
            output = dict(result.output) if isinstance(result.output, Mapping) else result.output
            if isinstance(output, dict):
                output.setdefault("execution_mode", "candidate_http")
            return AdapterResult(
                output=output,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                latency_ms=result.latency_ms,
                status_code=result.status_code,
                trace_id=result.trace_id,
                operation_name=result.operation_name,
            )

        expected_failure_class = _required_string(
            metadata.get("expected_failure_class"),
            f"{case.get('id')}.metadata.expected_failure_class",
        )
        output = _fault_output(
            case,
            expected_failure_class=expected_failure_class,
            fault_cost_usd=self._fault_cost_usd,
            fault_latency_ms=self._fault_latency_ms,
        )
        return AdapterResult(
            output=output,
            exit_code=1,
            latency_ms=float(output.get("latency_ms") or 0.0),
            status_code=599 if expected_failure_class == "adapter_error" else 200,
            trace_id=f"deterministic-fault-{case['id']}",
            operation_name="candidate.gdev_agent.deterministic_fault",
        )


def build_challenge_result(
    *,
    dataset: Dataset,
    run: RunRecord,
    thresholds: ChallengeThresholds,
    provenance: Mapping[str, Any],
    dataset_raw_sha256: str,
    threshold_config_sha256: str,
) -> dict[str, Any]:
    if len(run.case_results) != len(dataset.cases):
        raise ChallengeConfigurationError("Run and challenge dataset case counts differ")
    results_by_id = {result.case_id: result for result in run.case_results}
    if len(results_by_id) != len(run.case_results):
        raise ChallengeConfigurationError("Challenge run contains duplicate case IDs")

    case_outcomes: list[dict[str, Any]] = []
    for case in dataset.cases:
        if case.id not in results_by_id:
            raise ChallengeConfigurationError(f"Challenge run is missing case {case.id}")
        result = results_by_id[case.id]
        expected = _mapping(case.expected, f"{case.id}.expected")
        actual = _mapping(result.output, f"{case.id}.output")
        failed_categories = sorted(
            {
                str(validator.get("category"))
                for validator in result.validator_results
                if validator.get("passed") is False and validator.get("category") != "none"
            }
        )
        expected_failure = case.metadata.get("expected_failure") is True
        expected_class = (
            _required_string(
                case.metadata.get("expected_failure_class"),
                f"{case.id}.metadata.expected_failure_class",
            )
            if expected_failure
            else None
        )
        expected_matched = bool(expected_failure and expected_class in failed_categories)
        unexpected_pass = bool(expected_failure and not failed_categories)
        unexpected_fail = bool(
            (not expected_failure and failed_categories)
            or (expected_failure and failed_categories and not expected_matched)
        )
        blocking_failure = bool(
            set(failed_categories) & BLOCKING_CATEGORIES and not expected_matched
        )
        reconciled_pass = bool(expected_matched or (not expected_failure and not failed_categories))
        if expected_matched:
            outcome = "expected_failure_matched"
        elif blocking_failure:
            outcome = "blocking_failure"
        elif unexpected_pass:
            outcome = "unexpected_pass"
        elif failed_categories:
            outcome = "diagnostic_failure"
        else:
            outcome = "pass"
        case_outcomes.append(
            {
                "blocking_failure": blocking_failure,
                "case_id": case.id,
                "classification_correct": actual.get("category") == expected.get("category"),
                "execution_mode": actual.get("execution_mode", "candidate_http"),
                "expected_failure": expected_failure,
                "expected_failure_class": expected_class,
                "expected_failure_matched": expected_matched,
                "failed_categories": failed_categories,
                "human_review_required": case.metadata.get("human_review_required") is True,
                "judge_optional": case.metadata.get("judge_optional") is True,
                "observed_requires_human": actual.get("requires_human") is True,
                "outcome": outcome,
                "reconciled_pass": reconciled_pass,
                "slice": _required_string(case.metadata.get("slice"), f"{case.id}.metadata.slice"),
                "unexpected_fail": unexpected_fail,
                "unexpected_pass": unexpected_pass,
            }
        )

    metrics = _aggregate_metrics(case_outcomes, dataset=dataset, run=run)
    threshold_results = evaluate_thresholds(metrics, thresholds)
    gate_failures = [name for name, value in threshold_results.items() if not value["passed"]]
    return {
        "cases": case_outcomes,
        "dataset": {
            "case_count": dataset.metadata.case_count,
            "dataset_hash": dataset.metadata.dataset_hash,
            "dataset_id": dataset.metadata.dataset_id,
            "raw_sha256": dataset_raw_sha256,
            "schema_version": dataset.metadata.schema_version,
        },
        "gate": {
            "failed_thresholds": gate_failures,
            "passed": not gate_failures,
        },
        "metrics": metrics,
        "provenance": dict(provenance),
        "run": {
            "candidate_version": run.candidate_version,
            "completed_at": run.completed_at,
            "run_id": run.run_id,
            "started_at": run.started_at,
            "validator_version": run.validator_version,
        },
        "schema_version": CHALLENGE_SCHEMA_VERSION,
        "slices": _slice_metrics(case_outcomes),
        "threshold_config": {
            "raw_sha256": threshold_config_sha256,
            "values": thresholds.to_mapping(),
        },
        "threshold_results": threshold_results,
    }


def evaluate_thresholds(
    metrics: Mapping[str, int | float], thresholds: ChallengeThresholds
) -> dict[str, dict[str, Any]]:
    specs = {
        "blocking_failure_count_max": (
            "blocking_failure_count",
            "<=",
            thresholds.blocking_failure_count_max,
        ),
        "classification_accuracy_min": (
            "classification_accuracy",
            ">=",
            thresholds.classification_accuracy_min,
        ),
        "expected_failure_matched_min": (
            "expected_failure_matched",
            ">=",
            thresholds.expected_failure_matched_min,
        ),
        "human_review_required_count_min": (
            "human_review_required_count",
            ">=",
            thresholds.human_review_required_count_min,
        ),
        "human_escalation_recall_min": (
            "human_escalation_recall",
            ">=",
            thresholds.human_escalation_recall_min,
        ),
        "judge_optional_cases_max": (
            "judge_optional_cases",
            "<=",
            thresholds.judge_optional_cases_max,
        ),
        "max_cost_per_case_usd": ("cost_per_case_usd", "<=", thresholds.max_cost_per_case_usd),
        "max_invalid_structured_output_rate": (
            "invalid_structured_output_rate",
            "<=",
            thresholds.max_invalid_structured_output_rate,
        ),
        "max_latency_p95_ms": ("latency_p95_ms", "<=", thresholds.max_latency_p95_ms),
        "max_unsafe_auto_approval_rate": (
            "unsafe_auto_approval_rate",
            "<=",
            thresholds.max_unsafe_auto_approval_rate,
        ),
        "unexpected_fail_count_max": (
            "unexpected_fail_count",
            "<=",
            thresholds.unexpected_fail_count_max,
        ),
        "unexpected_pass_count_max": (
            "unexpected_pass_count",
            "<=",
            thresholds.unexpected_pass_count_max,
        ),
    }
    results: dict[str, dict[str, Any]] = {}
    for threshold_name, (metric_name, operator, limit) in specs.items():
        observed = metrics[metric_name]
        passed = observed <= limit if operator == "<=" else observed >= limit
        results[threshold_name] = {
            "limit": limit,
            "metric": metric_name,
            "observed": observed,
            "operator": operator,
            "passed": passed,
        }
    return results


def render_challenge_markdown(result: Mapping[str, Any]) -> str:
    gate = _mapping(result.get("gate"), "gate")
    metrics = _mapping(result.get("metrics"), "metrics")
    run = _mapping(result.get("run"), "run")
    provenance = _mapping(result.get("provenance"), "provenance")
    runtime = _mapping(provenance.get("runtime"), "provenance.runtime")
    request_namespace = _mapping(
        provenance.get("request_namespace"),
        "provenance.request_namespace",
    )
    dataset = _mapping(result.get("dataset"), "dataset")
    lines = [
        "# gdev-agent Challenge Run",
        "",
        f"Gate: **{'PASS' if gate.get('passed') else 'FAIL'}**",
        "",
        "This report is generated from the adjacent machine-readable JSON artifact. ",
        "Deterministic provider faults are harness evidence, not observed candidate outages.",
        "",
        "## Provenance",
        "",
        f"- Run ID: `{run.get('run_id')}`",
        f"- Candidate: `{run.get('candidate_version')}`",
        f"- Component revision: `{provenance.get('component_revision')}`",
        f"- Component worktree: `{provenance.get('component_worktree_state')}`",
        f"- Component image digest: `{provenance.get('component_image_digest') or 'not supplied'}`",
        f"- Environment: `{provenance.get('environment_label')}`",
        f"- Fixture: `{provenance.get('fixture')}`",
        f"- Harness: `{provenance.get('harness_version')}`",
        f"- Request namespace: `{request_namespace.get('identifier')}`",
        f"- Request namespace adapter mode: `{request_namespace.get('adapter_mode')}`",
        f"- Request namespace applied: `{request_namespace.get('applied')}`",
        f"- Python: `{runtime.get('python')}`",
        f"- Dataset: `{dataset.get('dataset_id')}` / `{dataset.get('dataset_hash')}`",
        "",
        "## Metrics",
        "",
        "| Metric | Observed |",
        "|---|---:|",
    ]
    for name in sorted(metrics):
        lines.append(f"| `{name}` | `{_display(metrics[name])}` |")

    lines.extend(["", "## Threshold Gate", "", "| Threshold | Check | Status |", "|---|---|---|"])
    threshold_results = _mapping(result.get("threshold_results"), "threshold_results")
    for name in sorted(threshold_results):
        raw = threshold_results[name]
        value = _mapping(raw, f"threshold_results.{name}")
        lines.append(
            f"| `{name}` | `{_display(value.get('observed'))} {value.get('operator')} "
            f"{_display(value.get('limit'))}` | `{'pass' if value.get('passed') else 'fail'}` |"
        )

    lines.extend(
        [
            "",
            "## Per-slice Results",
            "",
            "| Slice | Cases | Reconciled pass rate | Expected failures "
            "matched | Unexpected failures |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    slices = _mapping(result.get("slices"), "slices")
    for name, raw in slices.items():
        value = _mapping(raw, f"slices.{name}")
        lines.append(
            f"| `{name}` | {value['case_count']} | {_display(value['reconciled_pass_rate'])} | "
            f"{value['expected_failure_matched_count']} | {value['unexpected_fail_count']} |"
        )

    raw_cases = result.get("cases")
    if not isinstance(raw_cases, list):
        raise ChallengeConfigurationError("cases must be a list")
    visible_cases = []
    for raw_case in raw_cases:
        case = _mapping(raw_case, "cases[]")
        if case.get("outcome") != "pass":
            visible_cases.append(case)
    lines.extend(
        [
            "",
            "## Reconciled case outcomes",
            "",
            "| Case | Slice | Outcome | Failed categories | Execution mode |",
            "|---|---|---|---|---|",
        ]
    )
    if visible_cases:
        for case in visible_cases:
            categories = ", ".join(str(value) for value in case.get("failed_categories", []))
            lines.append(
                f"| `{case.get('case_id')}` | `{case.get('slice')}` | `{case.get('outcome')}` | "
                f"`{categories or 'none'}` | `{case.get('execution_mode')}` |"
            )
    else:
        lines.append("| none | - | - | - | - |")

    failed_thresholds = gate.get("failed_thresholds") or []
    lines.extend(
        [
            "",
            "## Gate Outcome",
            "",
            (
                "All declared thresholds passed."
                if not failed_thresholds
                else "Failed thresholds: "
                + ", ".join(f"`{name}`" for name in failed_thresholds)
                + "."
            ),
            "",
            "## Interpretation Boundary",
            "",
            "This synthetic/local diagnostic run does not establish production quality, real-user "
            "performance, adoption, or tenant-isolation enforcement. `input.tenant_slug` is "
            "dataset context; the configured adapter identity controls the signed request.",
            "",
        ]
    )
    return "\n".join(lines)


def _aggregate_metrics(
    outcomes: list[dict[str, Any]], *, dataset: Dataset, run: RunRecord
) -> dict[str, int | float]:
    candidate_outcomes = [outcome for outcome in outcomes if not outcome["expected_failure"]]
    candidate_ids = {outcome["case_id"] for outcome in candidate_outcomes}
    candidate_results = [result for result in run.case_results if result.case_id in candidate_ids]
    expected = [outcome for outcome in outcomes if outcome["expected_failure"]]
    review_required = [outcome for outcome in outcomes if outcome["human_review_required"]]
    costs = [result.cost_usd for result in candidate_results]
    latencies = [result.latency_ms for result in candidate_results]
    invalid_count = sum(
        bool(_mapping(result.output, f"{result.case_id}.output").get("invalid_structured_output"))
        for result in candidate_results
    )
    unsafe_count = sum(
        bool(_mapping(result.output, f"{result.case_id}.output").get("unsafe_auto_approval"))
        for result in candidate_results
    )
    return {
        "blocking_failure_count": sum(outcome["blocking_failure"] for outcome in outcomes),
        "candidate_scope_case_count": len(candidate_outcomes),
        "classification_accuracy": _ratio(
            sum(outcome["classification_correct"] for outcome in candidate_outcomes),
            len(candidate_outcomes),
        ),
        "cost_per_case_usd": sum(costs) / len(costs) if costs else 0.0,
        "diagnostic_failure_count": sum(
            outcome["outcome"] == "diagnostic_failure" for outcome in outcomes
        ),
        "expected_failure_case_count": len(expected),
        "expected_failure_matched": _ratio(
            sum(outcome["expected_failure_matched"] for outcome in expected), len(expected)
        ),
        "expected_failure_matched_count": sum(
            outcome["expected_failure_matched"] for outcome in expected
        ),
        "human_escalation_recall": _ratio(
            sum(outcome["observed_requires_human"] for outcome in review_required),
            len(review_required),
        ),
        "human_review_required_count": sum(
            outcome["observed_requires_human"] for outcome in outcomes
        ),
        "invalid_structured_output_rate": _ratio(invalid_count, len(candidate_results)),
        "judge_optional_cases": sum(outcome["judge_optional"] for outcome in outcomes),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "reconciled_pass_rate": _ratio(
            sum(outcome["reconciled_pass"] for outcome in outcomes), len(outcomes)
        ),
        "total_case_count": dataset.metadata.case_count,
        "unexpected_fail_count": sum(outcome["unexpected_fail"] for outcome in outcomes),
        "unexpected_pass_count": sum(outcome["unexpected_pass"] for outcome in outcomes),
        "unsafe_auto_approval_rate": _ratio(unsafe_count, len(candidate_results)),
    }


def _slice_metrics(outcomes: list[dict[str, Any]]) -> dict[str, dict[str, int | float]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for outcome in outcomes:
        grouped[outcome["slice"]].append(outcome)
    result: dict[str, dict[str, int | float]] = {}
    for slice_name in sorted(grouped):
        values = grouped[slice_name]
        result[slice_name] = {
            "blocking_failure_count": sum(value["blocking_failure"] for value in values),
            "case_count": len(values),
            "expected_failure_matched_count": sum(
                value["expected_failure_matched"] for value in values
            ),
            "reconciled_pass_rate": _ratio(
                sum(value["reconciled_pass"] for value in values), len(values)
            ),
            "unexpected_fail_count": sum(value["unexpected_fail"] for value in values),
            "unexpected_pass_count": sum(value["unexpected_pass"] for value in values),
        }
    return result


def _fault_output(
    case: Mapping[str, Any],
    *,
    expected_failure_class: str,
    fault_cost_usd: float,
    fault_latency_ms: float,
) -> dict[str, Any]:
    expected = _mapping(case.get("expected"), "expected")
    output: dict[str, Any] = {
        "adapter_error": False,
        "case_id": str(case["id"]),
        "category": expected.get("category"),
        "confidence": 0.99,
        "cost_usd": 0.0,
        "execution_mode": "deterministic_fault_injection",
        "guard_blocked": expected.get("guard_behavior") == "block_input",
        "invalid_structured_output": False,
        "latency_ms": 1.0,
        "requires_human": expected.get("requires_human"),
        "risk_reason": f"deterministic harness fault: {expected_failure_class}",
        "status": expected.get("expected_status"),
        "unsafe_auto_approval": False,
    }
    if expected_failure_class == "adapter_error":
        output.update({"adapter_error": True, "category": "adapter_error", "status": "error"})
    elif expected_failure_class == "invalid_structured_output":
        output.update(
            {
                "category": "invalid_structured_output",
                "invalid_structured_output": True,
                "status": "error",
            }
        )
    elif expected_failure_class == "unsafe_auto_approval":
        output.update({"requires_human": False, "status": "executed", "unsafe_auto_approval": True})
    elif expected_failure_class == "missing_required_field":
        output.pop("adapter_error")
        output.pop("guard_blocked")
    elif expected_failure_class == "latency_regression":
        output["latency_ms"] = fault_latency_ms
    elif expected_failure_class == "cost_regression":
        output["cost_usd"] = fault_cost_usd
    else:
        raise ChallengeConfigurationError(
            f"Unsupported deterministic failure class: {expected_failure_class}"
        )
    return output


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ChallengeConfigurationError(f"{field} must be an object")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ChallengeConfigurationError(f"{field} must be a non-empty string")
    return value


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ChallengeConfigurationError(f"{field} must be a non-negative integer")
    return value


def _non_negative_float(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise ChallengeConfigurationError(f"{field} must be a non-negative number")
    return float(value)


def _rate(value: Any, field: str) -> float:
    rate = _non_negative_float(value, field)
    if rate > 1:
        raise ChallengeConfigurationError(f"{field} must be between 0 and 1")
    return rate


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def _display(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
