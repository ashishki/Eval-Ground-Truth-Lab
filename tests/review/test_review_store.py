from __future__ import annotations

import json
from datetime import UTC, datetime

from eval_ground_truth_lab.reports import render_unresolved_review_links
from eval_ground_truth_lab.review import FileReviewStore


def test_review_entries_are_append_only(tmp_path) -> None:
    store = FileReviewStore(
        entries_path=tmp_path / "review_entries.jsonl",
        decisions_path=tmp_path / "review_decisions.jsonl",
    )

    first = store.append_review_entry(
        review_id="review_001",
        case_id="gdev-legal-001",
        candidate_version="gdev-demo-v1",
        rubric_version="judge-rubric-v1",
        judge_explanation="Privacy request needs review.",
        created_at=datetime(2026, 6, 12, 10, 0, tzinfo=UTC),
    )
    first_line = store.entries_path.read_text(encoding="utf-8").splitlines()[0]
    second = store.append_review_entry(
        review_id="review_002",
        case_id="gdev-billing-001",
        candidate_version="gdev-demo-v1",
        rubric_version="judge-rubric-v1",
        judge_explanation="Refund request needs review.",
        created_at="2026-06-12T10:01:00+00:00",
    )

    lines = store.entries_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line
    assert json.loads(lines[0]) == {
        "review_id": "review_001",
        "case_id": "gdev-legal-001",
        "candidate_version": "gdev-demo-v1",
        "rubric_version": "judge-rubric-v1",
        "judge_explanation": "Privacy request needs review.",
        "reviewer_status": "pending",
        "created_at": "2026-06-12T10:00:00+00:00",
    }
    assert store.list_entries() == (first, second)


def test_review_decisions_do_not_mutate_original_evidence(tmp_path) -> None:
    store = FileReviewStore(
        entries_path=tmp_path / "review_entries.jsonl",
        decisions_path=tmp_path / "review_decisions.jsonl",
    )
    store.append_review_entry(
        review_id="review_001",
        case_id="gdev-legal-001",
        candidate_version="gdev-demo-v1",
        rubric_version="judge-rubric-v1",
        judge_explanation="Original judge explanation stays immutable.",
        created_at="2026-06-12T10:00:00+00:00",
    )
    entry_file_before = store.entries_path.read_text(encoding="utf-8")

    decision = store.append_decision(
        review_id="review_001",
        reviewer="operator",
        decision="accepted_failure",
        rationale="Expected privacy case requires manual acceptance.",
        reviewed_at=datetime(2026, 6, 12, 10, 10, tzinfo=UTC),
    )

    assert store.entries_path.read_text(encoding="utf-8") == entry_file_before
    assert store.list_decisions() == (decision,)
    assert store.unresolved_entries() == ()
    assert json.loads(store.decisions_path.read_text(encoding="utf-8").splitlines()[0]) == {
        "review_id": "review_001",
        "reviewer": "operator",
        "decision": "accepted_failure",
        "rationale": "Expected privacy case requires manual acceptance.",
        "reviewed_at": "2026-06-12T10:10:00+00:00",
    }


def test_report_links_unresolved_review_items(tmp_path) -> None:
    store = FileReviewStore(
        entries_path=tmp_path / "review_entries.jsonl",
        decisions_path=tmp_path / "review_decisions.jsonl",
    )
    store.append_review_entry(
        review_id="review_001",
        case_id="case-resolved",
        candidate_version="candidate-v1",
        rubric_version="judge-rubric-v1",
        judge_explanation="Resolved item.",
        created_at="2026-06-12T10:00:00+00:00",
    )
    store.append_review_entry(
        review_id="review_002",
        case_id="case-pending",
        candidate_version="candidate-v1",
        rubric_version="judge-rubric-v1",
        judge_explanation="Pending item.",
        created_at="2026-06-12T10:01:00+00:00",
    )
    store.append_decision(
        review_id="review_001",
        reviewer="operator",
        decision="accepted_failure",
        rationale="Resolved.",
        reviewed_at="2026-06-12T10:10:00+00:00",
    )

    report_section = render_unresolved_review_links(
        store.unresolved_entries(),
        base_path="reviews/pending.md",
    )

    assert "## Unresolved Human Review" in report_section
    assert "[`review_002`](reviews/pending.md#review_002)" in report_section
    assert "`case-pending`" in report_section
    assert "review_001" not in report_section
