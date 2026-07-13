# Human review protocol

Human-review evidence is append-only and file-backed. Review labels do not
become true merely because a dataset field says review is required.

## Current challenge status

The `challenge_v1` cases are self-authored synthetic fixtures.
They have no independent annotator. There is no external workflow-owner review
or measured agreement.
`human_review_required=true` is a reference routing hypothesis; it does not mean
that a human reviewed the candidate output. The
[dataset card](../datasets/gdev_agent/challenge_v1_CARD.md) records this boundary.

## Files

- Review entries: `review_entries.jsonl`
- Review decisions: `review_decisions.jsonl`

Review entries preserve the original candidate/judge evidence. This example is
illustrative synthetic data, not a completed review from the published
challenge:

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

Review decisions append separately. This example is also illustrative:

```json
{
  "review_id": "review_001",
  "reviewer": "operator",
  "decision": "candidate_failure_confirmed",
  "rationale": "Frozen privacy rubric requires manual routing.",
  "reviewed_at": "2026-06-12T10:10:00+00:00"
}
```

Appending a decision does not mutate the original review entry. Reports can link
unresolved review items by `review_id`.

## Label-review procedure for a new dataset version

1. Freeze case text, authoring provenance, rubric version, and initial labels
   before a candidate run.
2. Have an initial annotator label category, status, guard behavior, human
   routing, unsafe-auto-approval policy, risk rationale, and allowed ambiguity
   without seeing candidate output.
3. When a second reviewer is available, have them label independently. Store
   both annotations; do not replace the first one.
4. Append disagreements with field-level reasons. An adjudicator records the
   accepted label and policy citation in a separate decision record.
5. Report annotator count, overlap, disagreement rate, unresolved cases,
   exclusions, and conflicts of interest in the dataset card.
6. Hash and version the adjudicated dataset and threshold policy. Any later
   label correction creates a new version and preserves the prior result.

If no independent reviewer exists, the manifest must record zero and the set
must not be described as expert-labeled, human-validated, or blind.

## Decision vocabulary

- `label_confirmed`: reference label and rationale accepted.
- `label_corrected`: a new dataset version is required; the old evidence remains.
- `candidate_failure_confirmed`: candidate output violates the frozen rubric.
- `accepted_ambiguity`: multiple outputs are allowed by the frozen rubric.
- `needs_domain_review`: no benchmark decision is made until qualified review.
- `excluded_invalid_case`: case is excluded only in a new version with rationale.

Reviewers must not use `accepted_failure` to make a blocking candidate pass
without changing and versioning the governing rubric or threshold policy.

## Privacy and independence

Review artifacts must omit secrets and personal data. Real workflow examples
require consent, a redistribution basis or non-public evidence boundary, and a
sanitized case identifier. Candidate developers should not adjudicate a blind
holdout they tuned against; conflicts and prior access must be disclosed.
