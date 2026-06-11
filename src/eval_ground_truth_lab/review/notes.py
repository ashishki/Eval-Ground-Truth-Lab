from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ALLOWED_REVIEW_DECISIONS = frozenset({"approve", "reject", "needs_changes"})


@dataclass(frozen=True)
class ReviewDecisionNote:
    reviewer: str
    timestamp: str
    case_id: str
    decision: str
    rationale: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "reviewer": self.reviewer,
            "timestamp": self.timestamp,
            "case_id": self.case_id,
            "decision": self.decision,
            "rationale": self.rationale,
        }


def append_review_decision(
    path: str | Path,
    *,
    reviewer: str,
    case_id: str,
    decision: str,
    rationale: str,
    timestamp: datetime | str | None = None,
) -> ReviewDecisionNote:
    if decision not in ALLOWED_REVIEW_DECISIONS:
        raise ValueError(f"decision must be one of {sorted(ALLOWED_REVIEW_DECISIONS)}")
    if not reviewer.strip() or not case_id.strip() or not rationale.strip():
        raise ValueError("reviewer, case_id, and rationale are required")

    note = ReviewDecisionNote(
        reviewer=reviewer,
        timestamp=_timestamp_to_string(timestamp),
        case_id=case_id,
        decision=decision,
        rationale=rationale,
    )
    notes_path = Path(path)
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    with notes_path.open("a", encoding="utf-8") as notes_file:
        notes_file.write(json.dumps(note.to_mapping(), sort_keys=True))
        notes_file.write("\n")
    return note


def _timestamp_to_string(timestamp: datetime | str | None) -> str:
    if timestamp is None:
        return datetime.now(UTC).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    if not timestamp.strip():
        raise ValueError("timestamp cannot be blank")
    return timestamp
