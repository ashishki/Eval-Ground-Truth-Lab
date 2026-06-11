from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from eval_ground_truth_lab.validators.result import ValidationResult


@dataclass(frozen=True)
class StructuredOutputSchema:
    required_fields: tuple[str, ...]
    allowed_enums: dict[str, set[Any]] = field(default_factory=dict)
    forbidden_fields: tuple[str, ...] = ()


def validate_structured_output(
    *,
    case_id: str,
    output: str | Mapping[str, Any],
    schema: StructuredOutputSchema,
) -> ValidationResult:
    parsed = _parse_output(case_id=case_id, output=output)
    if isinstance(parsed, ValidationResult):
        return parsed

    missing_fields = [
        field_name for field_name in schema.required_fields if field_name not in parsed
    ]
    if missing_fields:
        return ValidationResult(
            case_id=case_id,
            validator_id="structured_output.required_fields",
            passed=False,
            category="invalid_structured_output",
            message=f"Missing required fields: {', '.join(missing_fields)}",
            evidence={"missing_fields": missing_fields},
        )

    forbidden_present = [
        field_name for field_name in schema.forbidden_fields if field_name in parsed
    ]
    if forbidden_present:
        return ValidationResult(
            case_id=case_id,
            validator_id="structured_output.forbidden_fields",
            passed=False,
            category="invalid_structured_output",
            message=f"Forbidden fields present: {', '.join(forbidden_present)}",
            evidence={"forbidden_fields": forbidden_present},
        )

    for field_name, allowed_values in schema.allowed_enums.items():
        if field_name in parsed and parsed[field_name] not in allowed_values:
            ordered_allowed_values = sorted(allowed_values, key=repr)
            return ValidationResult(
                case_id=case_id,
                validator_id="structured_output.allowed_enum",
                passed=False,
                category="invalid_structured_output",
                message=(
                    f"Field '{field_name}' has value {parsed[field_name]!r}; "
                    f"allowed values are {ordered_allowed_values!r}"
                ),
                evidence={
                    "field": field_name,
                    "actual": parsed[field_name],
                    "allowed": ordered_allowed_values,
                },
            )

    return ValidationResult(
        case_id=case_id,
        validator_id="structured_output",
        passed=True,
        category="none",
        message="Structured output passed",
        evidence={"checked_fields": sorted(parsed.keys())},
    )


def _parse_output(
    *,
    case_id: str,
    output: str | Mapping[str, Any],
) -> dict[str, Any] | ValidationResult:
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            return ValidationResult(
                case_id=case_id,
                validator_id="structured_output.json",
                passed=False,
                category="invalid_structured_output",
                message=f"Output is not valid JSON: {exc.msg}",
                evidence={"json_error": exc.msg},
            )
    else:
        parsed = dict(output)

    if not isinstance(parsed, dict):
        return ValidationResult(
            case_id=case_id,
            validator_id="structured_output.object",
            passed=False,
            category="invalid_structured_output",
            message="Structured output must be a JSON object",
            evidence={"actual_type": type(parsed).__name__},
        )
    return parsed
