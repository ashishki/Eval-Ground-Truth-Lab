from __future__ import annotations

from collections.abc import Iterable

from eval_ground_truth_lab.review.store import ReviewEntry


def render_unresolved_review_links(
    entries: Iterable[ReviewEntry],
    *,
    base_path: str,
) -> str:
    unresolved = tuple(entries)
    lines = ["## Unresolved Human Review", ""]
    if not unresolved:
        lines.append("No unresolved human review items.")
        return "\n".join(lines)

    lines.extend(
        [
            "| Review | Case ID | Candidate Version | Rubric |",
            "|--------|---------|-------------------|--------|",
        ]
    )
    lines.extend(
        (
            f"| [`{entry.review_id}`]({base_path}#{entry.review_id}) | "
            f"`{entry.case_id}` | `{entry.candidate_version}` | `{entry.rubric_version}` |"
        )
        for entry in unresolved
    )
    return "\n".join(lines)
