from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ALLOWED_FILE_REVIEW_DECISIONS = frozenset({"accepted_failure", "rejected_failure", "needs_changes"})


@dataclass(frozen=True)
class ReviewEntry:
    review_id: str
    case_id: str
    candidate_version: str
    rubric_version: str
    judge_explanation: str
    reviewer_status: str
    created_at: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "case_id": self.case_id,
            "candidate_version": self.candidate_version,
            "rubric_version": self.rubric_version,
            "judge_explanation": self.judge_explanation,
            "reviewer_status": self.reviewer_status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, raw: dict[str, object]) -> ReviewEntry:
        return cls(
            review_id=_required_string(raw, "review_id"),
            case_id=_required_string(raw, "case_id"),
            candidate_version=_required_string(raw, "candidate_version"),
            rubric_version=_required_string(raw, "rubric_version"),
            judge_explanation=_required_string(raw, "judge_explanation"),
            reviewer_status=_required_string(raw, "reviewer_status"),
            created_at=_required_string(raw, "created_at"),
        )


@dataclass(frozen=True)
class ReviewDecision:
    review_id: str
    reviewer: str
    decision: str
    rationale: str
    reviewed_at: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "reviewer": self.reviewer,
            "decision": self.decision,
            "rationale": self.rationale,
            "reviewed_at": self.reviewed_at,
        }

    @classmethod
    def from_mapping(cls, raw: dict[str, object]) -> ReviewDecision:
        return cls(
            review_id=_required_string(raw, "review_id"),
            reviewer=_required_string(raw, "reviewer"),
            decision=_required_string(raw, "decision"),
            rationale=_required_string(raw, "rationale"),
            reviewed_at=_required_string(raw, "reviewed_at"),
        )


class FileReviewStore:
    def __init__(self, *, entries_path: str | Path, decisions_path: str | Path) -> None:
        self.entries_path = Path(entries_path)
        self.decisions_path = Path(decisions_path)

    def append_review_entry(
        self,
        *,
        case_id: str,
        candidate_version: str,
        rubric_version: str,
        judge_explanation: str,
        review_id: str | None = None,
        reviewer_status: str = "pending",
        created_at: datetime | str | None = None,
    ) -> ReviewEntry:
        entry = ReviewEntry(
            review_id=review_id or f"review_{uuid4().hex}",
            case_id=_non_blank(case_id, "case_id"),
            candidate_version=_non_blank(candidate_version, "candidate_version"),
            rubric_version=_non_blank(rubric_version, "rubric_version"),
            judge_explanation=_non_blank(judge_explanation, "judge_explanation"),
            reviewer_status=_non_blank(reviewer_status, "reviewer_status"),
            created_at=_timestamp_to_string(created_at),
        )
        _append_jsonl(self.entries_path, entry.to_mapping())
        return entry

    def append_decision(
        self,
        *,
        review_id: str,
        reviewer: str,
        decision: str,
        rationale: str,
        reviewed_at: datetime | str | None = None,
    ) -> ReviewDecision:
        if decision not in ALLOWED_FILE_REVIEW_DECISIONS:
            raise ValueError(f"decision must be one of {sorted(ALLOWED_FILE_REVIEW_DECISIONS)}")
        note = ReviewDecision(
            review_id=_non_blank(review_id, "review_id"),
            reviewer=_non_blank(reviewer, "reviewer"),
            decision=decision,
            rationale=_non_blank(rationale, "rationale"),
            reviewed_at=_timestamp_to_string(reviewed_at),
        )
        _append_jsonl(self.decisions_path, note.to_mapping())
        return note

    def list_entries(self) -> tuple[ReviewEntry, ...]:
        return tuple(ReviewEntry.from_mapping(raw) for raw in _read_jsonl(self.entries_path))

    def list_decisions(self) -> tuple[ReviewDecision, ...]:
        return tuple(ReviewDecision.from_mapping(raw) for raw in _read_jsonl(self.decisions_path))

    def unresolved_entries(self) -> tuple[ReviewEntry, ...]:
        decided_ids = {decision.review_id for decision in self.list_decisions()}
        return tuple(entry for entry in self.list_entries() if entry.review_id not in decided_ids)


def _append_jsonl(path: Path, raw: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(raw, sort_keys=True))
        file.write("\n")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            if not isinstance(raw, dict):
                raise ValueError(f"Review store line {line_number} must be a JSON object")
            rows.append(raw)
    return rows


def _required_string(raw: dict[str, object], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Review field {field!r} must be a non-empty string")
    return value


def _non_blank(value: str, field: str) -> str:
    if not value.strip():
        raise ValueError(f"{field} cannot be blank")
    return value


def _timestamp_to_string(timestamp: datetime | str | None) -> str:
    if timestamp is None:
        return datetime.now(UTC).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    return _non_blank(timestamp, "timestamp")
