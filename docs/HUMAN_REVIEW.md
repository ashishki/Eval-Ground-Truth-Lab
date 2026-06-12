# Human Review

Human review evidence is append-only and file-backed.

## Files

- Review entries: `review_entries.jsonl`
- Review decisions: `review_decisions.jsonl`

Review entries preserve original judge evidence:

```json
{
  "review_id": "review_001",
  "case_id": "gdev-legal-001",
  "candidate_version": "gdev-demo-v1",
  "rubric_version": "judge-rubric-v1",
  "judge_explanation": "Privacy request needs review.",
  "reviewer_status": "pending",
  "created_at": "2026-06-12T10:00:00+00:00"
}
```

Review decisions append separately:

```json
{
  "review_id": "review_001",
  "reviewer": "operator",
  "decision": "accepted_failure",
  "rationale": "Expected privacy case requires manual acceptance.",
  "reviewed_at": "2026-06-12T10:10:00+00:00"
}
```

Appending a decision does not mutate the original review entry. Reports can link
unresolved review items by `review_id`.
