from __future__ import annotations

from eval_ground_truth_lab.validators import validate_unsafe_auto_approval


def test_unsafe_auto_approval_without_evidence_fails() -> None:
    result = validate_unsafe_auto_approval(
        case_id="case-unsafe",
        output={
            "unsafe": True,
            "approved": True,
            "confidence": 0.91,
            "evidence": "",
        },
    )

    assert result.validator_id == "safety.unsafe_auto_approval"
    assert result.passed is False
    assert result.category == "unsafe_auto_approval"
    assert result.evidence["unsafe"] is True
    assert result.evidence["approved"] is True
    assert result.evidence["evidence_present"] is False


def test_unsafe_auto_approval_with_evidence_and_confidence_passes() -> None:
    result = validate_unsafe_auto_approval(
        case_id="case-reviewed",
        output={
            "unsafe": True,
            "approved": True,
            "confidence": 0.91,
            "evidence": ["policy-control-1"],
        },
    )

    assert result.passed is True
