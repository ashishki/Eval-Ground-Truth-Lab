# gdev-agent benchmark protocol

Status: methodology for public development benchmarks and future blind holdouts

## Current evidence class

`challenge_v1` is a public, self-authored development diagnostic. It is harder
than the 55-case conformance set, but it is not blind, independently labeled, or
based on real users. The canonical local result is a verified **FAIL** and is
published with all case-level failures.

The [dataset card](../datasets/gdev_agent/challenge_v1_CARD.md) is authoritative
for provenance and limitations. The
[v0.2.0 evidence package](evidence/releases/v0.2.0/README.md) is authoritative
for the executed baseline.

## Freeze-before-run contract

For a canonical candidate run:

1. Commit the dataset, threshold policy, dataset card, and labeling protocol.
2. Record the semantic dataset hash plus raw dataset and threshold SHA-256
   values before executing the candidate.
3. Fix a full candidate commit and, when applicable, an image digest. Record
   clean/dirty worktree state without normalizing a dirty candidate into a clean
   claim.
4. Use a unique run ID. For the built-in gdev HTTP adapter, bind the deterministic
   run/candidate/component/dataset request namespace before transport.
5. Start stateful dependencies from a documented state. Record whether caches
   or dedup stores were recreated; namespacing is still required.
6. Execute the full set once for the publication decision. Operational retries
   caused by harness/setup failures are retained separately and never selected
   by score.
7. Publish the machine-readable result, generated report, sealed terminal run,
   content-addressed manifest, nonzero gate exit, failed thresholds, and known
   limits.
8. Do not change labels or thresholds to make the fixed candidate pass. Any
   legitimate correction creates a new dataset/threshold version and explains
   the old result.

`challenge_v1` and its threshold file were fixed before the 2026-07-13 run at
their recorded hashes. The later dataset card documents that pre-existing
executable policy; it is not described as a separate preregistered study.

## Hypotheses and decision authority

Each threshold is a testable hypothesis, not a target to optimize after seeing
the result. Deterministic validators and the checked-in threshold policy own the
gate. Optional model judges cannot override blocking failures. Expected harness
faults are reconciled separately from the 90 candidate-facing cases.

A passing gate means only that the fixed candidate met this fixed synthetic
policy. A failing gate is publishable evidence and must remain visible. Neither
outcome proves production quality or user value.

## Labeling and human review

For a new benchmark version, a case record should include authoring provenance,
reference category/status/guard/routing labels, risk rationale, allowed
ambiguity, and the expected failure class if applicable.

When independent reviewers are available:

1. An initial annotator labels without seeing candidate output.
2. A second reviewer labels the same frozen case independently.
3. Disagreements are appended to the review log; neither original annotation is
   overwritten.
4. An adjudicator records the accepted label, rationale, policy/rubric version,
   and timestamp.
5. The dataset card reports reviewer count, disagreement rate, unresolved
   cases, exclusions, and any conflicts of interest.

Until that process occurs, the dataset must say `independent_annotator_count=0`
and must not use “human validated” or “expert labeled.” The current
`human_review_required` field is a reference routing label, not evidence that a
reviewer evaluated each output.

## Leakage and contamination controls

- Public development cases may be used for debugging, but every tuned candidate
  must be labeled as development-set-tuned.
- Do not add exact public case phrases or IDs to candidate rules and then report
  the same-set score as generalization.
- Add counterfactual negatives for every new lexical/guard signal and paraphrase
  positives that do not reuse the trigger phrase.
- Keep future blind labels outside the candidate-development repository or
  encrypt/seal them for an independent evaluator.
- Record candidate SHA before unblinding. After unblinding, retire that set as a
  blind holdout and version the next one.
- Report all attempted canonical candidates, or explicitly mark exploratory
  runs; do not select only the best run.

## Reproduction

Use a run store outside the evidence directory because the CLI copies the final
sealed run into the evidence package:

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent-challenge \
  --dataset datasets/gdev_agent/challenge_v1.jsonl \
  --base-url http://127.0.0.1:8000 \
  --run-id <unique-run-id> \
  --run-dir /tmp/eval-lab-gdev-challenge-runs \
  --candidate-version <candidate-version> \
  --component-revision <full-component-sha> \
  --component-worktree-state clean \
  --environment-label <bounded-environment-label> \
  --evidence-dir /tmp/gdev-challenge-evidence
```

Verify the resulting `sha256-*.manifest.json` with `verify-evidence`. A gate
failure exits `1` while preserving the evidence.

## Successor benchmark acceptance checklist

A successor may be described as a harder labeled benchmark only when it has:

- a versioned dataset card and redistribution basis;
- explicit hypotheses and an unchanged executable threshold policy;
- source/case provenance and a documented label rubric;
- public-development versus blind-holdout status;
- counterfactual negative and paraphrase coverage;
- reviewer/adjudication records or an explicit zero-reviewer limitation;
- one reproducible baseline with a fixed candidate revision;
- case/slice failures, limitations, and a verified content-addressed package.

External workflow ownership, two design partners, and independent label review
remain external validation requirements; they cannot be satisfied with
synthetic fixtures or repository-author review.
