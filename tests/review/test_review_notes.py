from __future__ import annotations

import json
from datetime import UTC, datetime

from eval_ground_truth_lab.review import append_review_decision


def test_review_decision_note_contains_required_fields(tmp_path) -> None:
    notes_path = tmp_path / "review_decisions.jsonl"

    append_review_decision(
        notes_path,
        reviewer="ashish",
        case_id="case-001",
        decision="approve",
        rationale="Expected output is sufficiently supported.",
        timestamp=datetime(2026, 6, 11, 12, 0, tzinfo=UTC),
    )
    append_review_decision(
        notes_path,
        reviewer="ashish",
        case_id="case-002",
        decision="reject",
        rationale="Evidence is missing.",
        timestamp="2026-06-11T12:01:00+00:00",
    )

    lines = notes_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[0])
    assert entry == {
        "reviewer": "ashish",
        "timestamp": "2026-06-11T12:00:00+00:00",
        "case_id": "case-001",
        "decision": "approve",
        "rationale": "Expected output is sufficiently supported.",
    }
