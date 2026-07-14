from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

from eval_ground_truth_lab.runs import RunRecord

MAX_DECISION_NUMBER = (2**53) - 1

_STANDARD_THRESHOLD_FIELD_ORDER = (
    "max_accuracy_drop",
    "max_invalid_output_rate_increase",
    "max_unsafe_auto_approval_rate_increase",
    "max_latency_p95_delta_ms",
    "max_cost_per_case_delta_usd",
)
_STANDARD_THRESHOLD_FIELDS = frozenset(_STANDARD_THRESHOLD_FIELD_ORDER)
_GDEV_THRESHOLD_FIELDS = frozenset(
    {
        "classification_accuracy_min",
        "max_invalid_structured_output_rate",
        "max_unsafe_auto_approval_rate",
        "max_latency_p95_ms",
        "max_cost_per_case_usd",
    }
)
_GDEV_OPTIONAL_THRESHOLD_FIELDS = frozenset(
    {
        "confidence_floor",
        "guard_block_rate_max",
        "human_escalation_recall_min",
        "risk_routing_recall_min",
    }
)
_RATE_THRESHOLD_FIELDS = frozenset(
    {
        "max_accuracy_drop",
        "max_invalid_output_rate_increase",
        "max_unsafe_auto_approval_rate_increase",
        "classification_accuracy_min",
        "max_invalid_structured_output_rate",
        "max_unsafe_auto_approval_rate",
        *_GDEV_OPTIONAL_THRESHOLD_FIELDS,
    }
)
_RUN_REQUIRED_FIELDS = frozenset(
    {
        "run_id",
        "run_type",
        "dataset_hash",
        "candidate_version",
        "validator_version",
        "threshold_config_version",
        "status",
        "started_at",
        "completed_at",
        "cost_total_usd",
        "cost_per_case_usd",
        "latency_ms_p50",
        "latency_ms_p95",
        "max_candidate_retries",
        "case_results",
    }
)
_RUN_ALLOWED_FIELDS = _RUN_REQUIRED_FIELDS | {"interrupted_at"}
_CASE_FIELDS = frozenset({"case_id", "output", "validator_results", "cost_usd", "latency_ms"})
_VALIDATOR_REQUIRED_FIELDS = frozenset({"validator_id", "passed", "category"})
_VALIDATOR_ALLOWED_FIELDS = _VALIDATOR_REQUIRED_FIELDS | {
    "case_id",
    "message",
    "evidence",
}
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_MARKDOWN_STRUCTURAL_CHARACTERS = frozenset(
    {"\x00", "\r", "\n", "\v", "\f", "\x85", "\u2028", "\u2029", "`", "|"}
)


class ComparisonError(RuntimeError):
    """Base error for baseline/candidate comparison failures."""


class ComparisonInputError(ComparisonError, ValueError):
    """Raised when a comparison input cannot support a trustworthy decision."""


class DatasetHashMismatchError(ComparisonError):
    """Raised when baseline and candidate runs do not evaluate the same dataset."""


@dataclass(frozen=True)
class ThresholdConfig:
    max_accuracy_drop: float = 0.0
    max_invalid_output_rate_increase: float = 0.0
    max_unsafe_auto_approval_rate_increase: float = 0.0
    max_latency_p95_delta_ms: float = 0.0
    max_cost_per_case_delta_usd: float = 0.0
    version: str | None = None
    exact_threshold_values: tuple[tuple[str, str], ...] = ()

    def exact_value(self, field: str) -> str:
        exact = dict(self.exact_threshold_values)
        if field in exact:
            return exact[field]
        if field not in _STANDARD_THRESHOLD_FIELDS:
            raise KeyError(field)
        return _canonical_decimal_text(_decision_decimal(getattr(self, field), field=field))


def read_run_artifact(path: str | Path) -> RunRecord:
    """Load one run without allowing JSON coercion to hide invalid decision data."""

    raw = read_json_object(path, label="run artifact")
    _validate_run_mapping(raw)
    return RunRecord.from_mapping(raw)


def read_threshold_config(path: str | Path) -> ThresholdConfig:
    """Load the native or legacy comparison policy with one strict schema."""

    raw = read_json_object(path, label="threshold config")
    keys = set(raw)
    if keys & _STANDARD_THRESHOLD_FIELDS:
        allowed = _STANDARD_THRESHOLD_FIELDS | {"version"}
        _require_fields(raw, allowed, label="threshold config")
        _reject_unknown_fields(raw, allowed, label="threshold config")
        config = ThresholdConfig(
            max_accuracy_drop=_threshold_number(raw, "max_accuracy_drop"),
            max_invalid_output_rate_increase=_threshold_number(
                raw, "max_invalid_output_rate_increase"
            ),
            max_unsafe_auto_approval_rate_increase=_threshold_number(
                raw, "max_unsafe_auto_approval_rate_increase"
            ),
            max_latency_p95_delta_ms=_threshold_number(raw, "max_latency_p95_delta_ms"),
            max_cost_per_case_delta_usd=_threshold_number(raw, "max_cost_per_case_delta_usd"),
            version=_require_report_safe_string(raw["version"], field="threshold config.version"),
            exact_threshold_values=tuple(
                (
                    field,
                    _canonical_decimal_text(_decision_decimal(raw[field], field=field)),
                )
                for field in _STANDARD_THRESHOLD_FIELD_ORDER
            ),
        )
        validate_threshold_config(config)
        return config

    if keys & _GDEV_THRESHOLD_FIELDS:
        required = _GDEV_THRESHOLD_FIELDS | {"version"}
        allowed = required | _GDEV_OPTIONAL_THRESHOLD_FIELDS
        _require_fields(raw, required, label="threshold config")
        _reject_unknown_fields(raw, allowed, label="threshold config")
        for optional_field in _GDEV_OPTIONAL_THRESHOLD_FIELDS & keys:
            _threshold_number(raw, optional_field)
        _threshold_number(raw, "classification_accuracy_min")
        accuracy_drop_text = _fraction_decimal_text(
            Fraction(1)
            - Fraction(
                _decision_decimal(
                    raw["classification_accuracy_min"],
                    field="classification_accuracy_min",
                )
            )
        )
        accuracy_drop = Decimal(accuracy_drop_text)
        legacy_exact_values = {
            "max_accuracy_drop": accuracy_drop_text,
            "max_invalid_output_rate_increase": _canonical_decimal_text(
                _decision_decimal(
                    raw["max_invalid_structured_output_rate"],
                    field="max_invalid_structured_output_rate",
                )
            ),
            "max_unsafe_auto_approval_rate_increase": _canonical_decimal_text(
                _decision_decimal(
                    raw["max_unsafe_auto_approval_rate"],
                    field="max_unsafe_auto_approval_rate",
                )
            ),
            "max_latency_p95_delta_ms": _canonical_decimal_text(
                _decision_decimal(raw["max_latency_p95_ms"], field="max_latency_p95_ms")
            ),
            "max_cost_per_case_delta_usd": _canonical_decimal_text(
                _decision_decimal(raw["max_cost_per_case_usd"], field="max_cost_per_case_usd")
            ),
        }
        config = ThresholdConfig(
            max_accuracy_drop=float(accuracy_drop),
            max_invalid_output_rate_increase=_threshold_number(
                raw, "max_invalid_structured_output_rate"
            ),
            max_unsafe_auto_approval_rate_increase=_threshold_number(
                raw, "max_unsafe_auto_approval_rate"
            ),
            max_latency_p95_delta_ms=_threshold_number(raw, "max_latency_p95_ms"),
            max_cost_per_case_delta_usd=_threshold_number(raw, "max_cost_per_case_usd"),
            version=_require_report_safe_string(raw["version"], field="threshold config.version"),
            exact_threshold_values=tuple(
                (field, legacy_exact_values[field]) for field in _STANDARD_THRESHOLD_FIELD_ORDER
            ),
        )
        validate_threshold_config(config)
        return config

    raise ComparisonInputError("threshold config does not match a supported comparison schema")


def read_json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    """Read strict JSON, rejecting duplicate keys at every nesting level."""

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ComparisonInputError(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    def reject_nonstandard_constant(value: str) -> None:
        raise ComparisonInputError(f"{label} contains non-standard numeric constant {value}")

    try:
        with Path(path).open(encoding="utf-8") as input_file:
            raw = json.load(
                input_file,
                object_pairs_hook=reject_duplicate_keys,
                parse_constant=reject_nonstandard_constant,
                parse_float=Decimal,
            )
    except json.JSONDecodeError as exc:
        raise ComparisonInputError(f"{label} is not valid JSON: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise ComparisonInputError(f"{label} must be a JSON object")
    return raw


def validate_comparison_inputs(
    baseline: RunRecord,
    candidate: RunRecord,
    thresholds: ThresholdConfig,
) -> None:
    """Validate the complete decision contract shared by CLI and Action callers."""

    validate_run_record(baseline, label="baseline run")
    validate_run_record(candidate, label="candidate run")
    validate_threshold_config(thresholds)

    if baseline.dataset_hash != candidate.dataset_hash:
        raise DatasetHashMismatchError(
            f"Baseline run {baseline.run_id} dataset hash {baseline.dataset_hash} "
            f"does not match candidate run {candidate.run_id} dataset hash "
            f"{candidate.dataset_hash}"
        )
    if baseline.run_type != candidate.run_type:
        raise ComparisonInputError("baseline and candidate must use the same run type")
    if baseline.validator_version != candidate.validator_version:
        raise ComparisonInputError("baseline and candidate must use the same validator version")
    if baseline.threshold_config_version != candidate.threshold_config_version:
        raise ComparisonInputError(
            "baseline and candidate must use the same threshold config version"
        )
    if thresholds.version != baseline.threshold_config_version:
        raise ComparisonInputError(
            "threshold config version must match both run artifacts' threshold config version"
        )

    baseline_ids = [case.case_id for case in baseline.case_results]
    candidate_ids = [case.case_id for case in candidate.case_results]
    if set(baseline_ids) != set(candidate_ids):
        raise ComparisonInputError(
            "baseline and candidate run artifacts must contain the same case IDs"
        )

    baseline_validators = _validator_ids_by_case(baseline)
    candidate_validators = _validator_ids_by_case(candidate)
    for case_id in baseline_ids:
        if baseline_validators[case_id] != candidate_validators[case_id]:
            raise ComparisonInputError(
                f"baseline and candidate validator-ID sets differ for case {case_id!r}"
            )


def validate_run_record(run: RunRecord, *, label: str = "run artifact") -> None:
    _validate_run_mapping(run.to_mapping(), label=label)


def validate_threshold_config(thresholds: ThresholdConfig) -> None:
    _require_report_safe_string(thresholds.version, field="threshold config.version")
    exact_pairs = thresholds.exact_threshold_values
    if not isinstance(exact_pairs, tuple) or any(
        not isinstance(pair, tuple) or len(pair) != 2 for pair in exact_pairs
    ):
        raise ComparisonInputError("exact threshold values must be field/value string pairs")
    exact_values = dict(exact_pairs)
    if len(exact_values) != len(exact_pairs):
        raise ComparisonInputError("exact threshold values contain duplicate fields")
    if exact_values and set(exact_values) != _STANDARD_THRESHOLD_FIELDS:
        raise ComparisonInputError("exact threshold values must cover exactly the five gates")

    for field in _STANDARD_THRESHOLD_FIELD_ORDER:
        value = _decision_number(getattr(thresholds, field), field=field)
        if field in _RATE_THRESHOLD_FIELDS and value > 1.0:
            raise ComparisonInputError(f"{field} must be between 0 and 1")
        if field in exact_values:
            exact_raw = exact_values[field]
            if not isinstance(exact_raw, str) or not exact_raw:
                raise ComparisonInputError(f"exact threshold value for {field} must be a string")
            try:
                exact = Decimal(exact_raw)
            except Exception as exc:
                raise ComparisonInputError(
                    f"exact threshold value for {field} must be decimal"
                ) from exc
            if not exact.is_finite():
                raise ComparisonInputError(f"exact threshold value for {field} must be finite")
            if exact < 0:
                raise ComparisonInputError(
                    f"exact threshold value for {field} must be non-negative"
                )
            if exact > MAX_DECISION_NUMBER:
                raise ComparisonInputError(
                    f"exact threshold value for {field} exceeds the supported maximum"
                )
            if float(exact) != value:
                raise ComparisonInputError(
                    f"exact threshold value for {field} must refine its float-facing value"
                )
            if field in _RATE_THRESHOLD_FIELDS and exact > 1:
                raise ComparisonInputError(f"exact threshold value for {field} must be at most 1")


def _validate_run_mapping(raw: Mapping[str, Any], *, label: str = "run artifact") -> None:
    _require_fields(raw, _RUN_REQUIRED_FIELDS, label=label)
    _reject_unknown_fields(raw, _RUN_ALLOWED_FIELDS, label=label)
    _require_canonical_run_id(raw["run_id"], field=f"{label}.run_id")
    _require_nonempty_string(raw["run_type"], field=f"{label}.run_type")
    _require_nonempty_string(raw["started_at"], field=f"{label}.started_at")
    _require_nonempty_string(raw["completed_at"], field=f"{label}.completed_at")
    for field in (
        "dataset_hash",
        "candidate_version",
        "validator_version",
        "threshold_config_version",
    ):
        _require_report_safe_string(raw[field], field=f"{label}.{field}")
    if raw["status"] != "completed":
        raise ComparisonInputError(f"{label} status must be exactly 'completed'")
    if raw.get("interrupted_at") is not None:
        raise ComparisonInputError(f"{label}.interrupted_at must be null for a completed run")

    retries = raw["max_candidate_retries"]
    if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
        raise ComparisonInputError(f"{label}.max_candidate_retries must be a non-negative integer")

    cases = raw["case_results"]
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ComparisonInputError(f"{label} must contain at least one completed case result")
    case_ids: set[str] = set()
    for case_index, case in enumerate(cases):
        case_label = f"{label}.case_results[{case_index}]"
        if not isinstance(case, Mapping):
            raise ComparisonInputError(f"{case_label} must be a JSON object")
        _require_fields(case, _CASE_FIELDS, label=case_label)
        _reject_unknown_fields(case, _CASE_FIELDS, label=case_label)
        case_id = _require_report_safe_string(case["case_id"], field=f"{case_label}.case_id")
        if case_id in case_ids:
            raise ComparisonInputError(f"{label} contains duplicate case ID {case_id!r}")
        case_ids.add(case_id)

        output = case["output"]
        if (
            isinstance(output, Mapping)
            and "correct" in output
            and not isinstance(output["correct"], bool)
        ):
            raise ComparisonInputError(
                f"{case_label}.output.correct must be a boolean when present"
            )

        receipts = case["validator_results"]
        if not isinstance(receipts, (list, tuple)) or not receipts:
            raise ComparisonInputError(
                f"{case_label}.validator_results must contain at least one receipt"
            )
        validator_ids: set[str] = set()
        for receipt_index, receipt in enumerate(receipts):
            receipt_label = f"{case_label}.validator_results[{receipt_index}]"
            if not isinstance(receipt, Mapping):
                raise ComparisonInputError(f"{receipt_label} must be a JSON object")
            _require_fields(receipt, _VALIDATOR_REQUIRED_FIELDS, label=receipt_label)
            _reject_unknown_fields(receipt, _VALIDATOR_ALLOWED_FIELDS, label=receipt_label)
            validator_id = _require_report_safe_string(
                receipt["validator_id"], field=f"{receipt_label}.validator_id"
            )
            if validator_id in validator_ids:
                raise ComparisonInputError(
                    f"{case_label} contains duplicate validator ID {validator_id!r}"
                )
            validator_ids.add(validator_id)
            category = _require_report_safe_string(
                receipt["category"], field=f"{receipt_label}.category"
            )
            passed = receipt["passed"]
            if not isinstance(passed, bool):
                raise ComparisonInputError(f"{receipt_label}.passed must be a boolean")
            if (passed and category != "none") or (not passed and category == "none"):
                raise ComparisonInputError(
                    f"{receipt_label}.category must be 'none' exactly when passed is true"
                )
            if "case_id" in receipt and receipt["case_id"] != case_id:
                raise ComparisonInputError(f"{receipt_label}.case_id must match its outer case")
            if "message" in receipt:
                _require_report_safe_string(
                    receipt["message"],
                    field=f"{receipt_label}.message",
                    allow_empty=True,
                    reject_html=True,
                )
            if "evidence" in receipt and not isinstance(receipt["evidence"], Mapping):
                raise ComparisonInputError(f"{receipt_label}.evidence must be a JSON object")

        _decision_number(case["cost_usd"], field=f"{case_label}.cost_usd")
        _decision_number(case["latency_ms"], field=f"{case_label}.latency_ms")

    for field in (
        "cost_total_usd",
        "cost_per_case_usd",
        "latency_ms_p50",
        "latency_ms_p95",
    ):
        _decision_number(raw[field], field=f"{label}.{field}")
    _validate_aggregate_metrics(raw, label=label)


def _validate_aggregate_metrics(raw: Mapping[str, Any], *, label: str) -> None:
    cases = raw["case_results"]
    costs = [
        _decision_number(case["cost_usd"], field=f"{label}.case_results.cost_usd") for case in cases
    ]
    latencies = sorted(
        _decision_number(
            case["latency_ms"],
            field=f"{label}.case_results.latency_ms",
        )
        for case in cases
    )
    expected_total = sum(costs)
    expected_per_case = expected_total / len(costs)
    expected_p50 = _percentile(latencies, 0.50)
    expected_p95 = _percentile(latencies, 0.95)
    for field, expected in (
        ("cost_total_usd", expected_total),
        ("cost_per_case_usd", expected_per_case),
        ("latency_ms_p50", expected_p50),
        ("latency_ms_p95", expected_p95),
    ):
        actual = _decision_number(raw[field], field=f"{label}.{field}")
        if actual != expected:
            raise ComparisonInputError(
                f"{label}.{field} does not match the complete case-result aggregate"
            )


def _validator_ids_by_case(run: RunRecord) -> dict[str, frozenset[str]]:
    return {
        case.case_id: frozenset(str(receipt["validator_id"]) for receipt in case.validator_results)
        for case in run.case_results
    }


def _threshold_number(raw: Mapping[str, Any], field: str) -> float:
    value = _decision_number(raw[field], field=field)
    if field in _RATE_THRESHOLD_FIELDS and value > 1.0:
        raise ComparisonInputError(f"{field} must be between 0 and 1")
    return value


def _decision_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ComparisonInputError(f"{field} must be a JSON number")
    if isinstance(value, int):
        if value < 0:
            raise ComparisonInputError(f"{field} must be non-negative")
        if value > MAX_DECISION_NUMBER:
            raise ComparisonInputError(
                f"{field} exceeds the supported maximum {MAX_DECISION_NUMBER}"
            )
        if int(float(value)) != value:
            raise ComparisonInputError(
                f"{field} integer must be exactly representable in the supported numeric domain"
            )
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ComparisonInputError(f"{field} must be finite")
        if value < 0:
            raise ComparisonInputError(f"{field} must be non-negative")
        if value > MAX_DECISION_NUMBER:
            raise ComparisonInputError(
                f"{field} exceeds the supported maximum {MAX_DECISION_NUMBER}"
            )
        numeric = float(value)
        if math.isfinite(numeric) and Decimal(str(numeric)) != value:
            raise ComparisonInputError(
                f"{field} must use a lossless shortest-round-trip decimal value"
            )
    else:
        numeric = float(value)
    if not math.isfinite(numeric):
        raise ComparisonInputError(f"{field} must be finite")
    if numeric < 0.0:
        raise ComparisonInputError(f"{field} must be non-negative")
    if numeric > MAX_DECISION_NUMBER:
        raise ComparisonInputError(f"{field} exceeds the supported maximum {MAX_DECISION_NUMBER}")
    return numeric


def _decision_decimal(value: Any, *, field: str) -> Decimal:
    _decision_number(value, field=field)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _canonical_decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _fraction_decimal_text(value: Fraction) -> str:
    denominator = value.denominator
    twos = 0
    fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        raise ComparisonInputError("legacy accuracy complement must be a finite decimal")
    scale = max(twos, fives)
    scaled = abs(value.numerator) * (10**scale // value.denominator)
    digits = str(scaled).rjust(scale + 1, "0")
    rendered = f"{digits[:-scale]}.{digits[-scale:]}" if scale else digits
    rendered = rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
    if not rendered:
        rendered = "0"
    return f"-{rendered}" if value < 0 else rendered


def _require_fields(
    raw: Mapping[str, Any],
    required: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    missing = sorted(required - set(raw))
    if missing:
        raise ComparisonInputError(f"{label} is missing required fields: {', '.join(missing)}")


def _reject_unknown_fields(
    raw: Mapping[str, Any],
    allowed: set[str] | frozenset[str],
    *,
    label: str,
) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ComparisonInputError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _require_nonempty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonInputError(f"{field} must be a non-empty string")
    return value


def _require_report_safe_string(
    value: Any,
    *,
    field: str,
    allow_empty: bool = False,
    reject_html: bool = False,
) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        raise ComparisonInputError(f"{field} must be {qualifier}")
    if any(character in value for character in _MARKDOWN_STRUCTURAL_CHARACTERS):
        raise ComparisonInputError(
            f"{field} contains characters unsafe for Markdown report publication"
        )
    if reject_html and ("<" in value or ">" in value):
        raise ComparisonInputError(f"{field} contains HTML delimiters unsafe for publication")
    return value


def _require_canonical_run_id(value: Any, *, field: str) -> str:
    run_id = _require_report_safe_string(value, field=field)
    if not _RUN_ID_PATTERN.fullmatch(run_id) or run_id in {".", ".."}:
        raise ComparisonInputError(
            f"{field} must be RunStore-safe: 1-128 characters, start with an alphanumeric "
            "character, and contain only alphanumerics, '.', '_' or '-'"
        )
    return run_id


def _percentile(ordered_values: list[Any], percentile: float) -> Any:
    index = max(0, math.ceil(percentile * len(ordered_values)) - 1)
    return ordered_values[index]
