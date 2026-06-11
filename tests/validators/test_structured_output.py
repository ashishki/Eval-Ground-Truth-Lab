from __future__ import annotations

from eval_ground_truth_lab.validators import StructuredOutputSchema, validate_structured_output


def test_structured_output_failures_include_validator_id() -> None:
    schema = StructuredOutputSchema(
        required_fields=("action", "category"),
        allowed_enums={"action": {"approve", "deny"}},
        forbidden_fields=("internal_notes",),
    )

    invalid_json = validate_structured_output(
        case_id="case-json",
        output="{not json",
        schema=schema,
    )
    missing = validate_structured_output(
        case_id="case-missing",
        output={"action": "approve"},
        schema=schema,
    )
    unknown_enum = validate_structured_output(
        case_id="case-enum",
        output={"action": "escalate", "category": "billing"},
        schema=schema,
    )
    forbidden = validate_structured_output(
        case_id="case-forbidden",
        output={"action": "deny", "category": "billing", "internal_notes": "private"},
        schema=schema,
    )

    assert invalid_json.validator_id == "structured_output.json"
    assert missing.validator_id == "structured_output.required_fields"
    assert unknown_enum.validator_id == "structured_output.allowed_enum"
    assert forbidden.validator_id == "structured_output.forbidden_fields"
    assert all(not result.passed for result in (invalid_json, missing, unknown_enum, forbidden))
    assert all(
        result.category == "invalid_structured_output"
        for result in (invalid_json, missing, unknown_enum, forbidden)
    )


def test_structured_output_valid_object_passes() -> None:
    schema = StructuredOutputSchema(
        required_fields=("action", "category"),
        allowed_enums={"action": {"approve", "deny"}},
        forbidden_fields=("internal_notes",),
    )

    result = validate_structured_output(
        case_id="case-valid",
        output={"action": "deny", "category": "billing"},
        schema=schema,
    )

    assert result.validator_id == "structured_output"
    assert result.passed is True
