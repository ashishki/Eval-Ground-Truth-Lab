from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BudgetCheckFailure:
    gate: str
    observed: float
    limit: float
    message: str

    def to_mapping(self) -> dict[str, float | str]:
        return {
            "gate": self.gate,
            "observed": self.observed,
            "limit": self.limit,
            "message": self.message,
        }


@dataclass(frozen=True)
class BudgetCheckResult:
    passed: bool
    failures: tuple[BudgetCheckFailure, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failures": [failure.to_mapping() for failure in self.failures],
        }


def load_budget_policy(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as policy_file:
        raw = json.load(policy_file)
    if not isinstance(raw, dict):
        raise ValueError("Budget policy must be a JSON object")
    return raw


def check_budget(rollup: dict[str, Any], policy: dict[str, Any]) -> BudgetCheckResult:
    failures = [
        *_check_maximum(
            gate="per_run_budget_usd",
            observed=_number(rollup, "total_cost_usd"),
            limit=_optional_number(policy, "per_run_budget_usd"),
            message="Total run cost exceeded per-run budget",
        ),
        *_check_maximum(
            gate="monthly_project_budget_usd",
            observed=_number(rollup, "total_cost_usd"),
            limit=_optional_number(policy, "monthly_project_budget_usd"),
            message="Rollup cost exceeded monthly project budget",
        ),
        *_check_maximum(
            gate="cost_per_case_ceiling",
            observed=_max_cost_by_case(rollup),
            limit=_optional_number(policy, "cost_per_case_ceiling"),
            message="At least one case exceeded cost-per-case ceiling",
        ),
        *_check_maximum(
            gate="judge_call_count_ceiling",
            observed=_number(rollup, "judge_call_count"),
            limit=_optional_number(policy, "judge_call_count_ceiling"),
            message="Judge call count exceeded ceiling",
        ),
    ]
    return BudgetCheckResult(passed=not failures, failures=tuple(failures))


def _check_maximum(
    *,
    gate: str,
    observed: float,
    limit: float | None,
    message: str,
) -> tuple[BudgetCheckFailure, ...]:
    if limit is None or observed <= limit:
        return ()
    return (
        BudgetCheckFailure(
            gate=gate,
            observed=observed,
            limit=limit,
            message=message,
        ),
    )


def _max_cost_by_case(rollup: dict[str, Any]) -> float:
    cost_by_case = rollup.get("cost_by_case", {})
    if not isinstance(cost_by_case, dict):
        raise ValueError("Rollup field 'cost_by_case' must be an object")
    if not cost_by_case:
        return 0.0
    values = []
    for case_id, value in cost_by_case.items():
        if not isinstance(case_id, str):
            raise ValueError("Rollup cost_by_case keys must be strings")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"Rollup cost for case {case_id!r} must be numeric")
        values.append(float(value))
    return max(values)


def _number(mapping: dict[str, Any], field: str) -> float:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Field {field!r} must be numeric")
    return float(value)


def _optional_number(mapping: dict[str, Any], field: str) -> float | None:
    value = mapping.get(field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Budget policy field {field!r} must be numeric when set")
    return float(value)
