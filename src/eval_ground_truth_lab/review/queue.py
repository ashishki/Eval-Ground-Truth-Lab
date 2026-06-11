from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eval_ground_truth_lab.judging.runner import JudgeProviderResult


@dataclass(frozen=True)
class HumanReviewEntry:
    case_id: str
    candidate_output: Any
    rubric_version: str
    judge_explanation: str
    reviewer_status: str = "pending"


class HumanReviewQueue:
    def __init__(self) -> None:
        self._entries: list[HumanReviewEntry] = []

    def add_from_judge_result(
        self,
        *,
        case_id: str,
        candidate_output: Any,
        rubric_version: str,
        judge_result: JudgeProviderResult,
    ) -> HumanReviewEntry:
        entry = HumanReviewEntry(
            case_id=case_id,
            candidate_output=candidate_output,
            rubric_version=rubric_version,
            judge_explanation=judge_result.explanation,
        )
        self._entries.append(entry)
        return entry

    def list_entries(self) -> tuple[HumanReviewEntry, ...]:
        return tuple(self._entries)
