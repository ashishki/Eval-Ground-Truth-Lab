# Case Study

## What Eval Lab Evaluates

Eval Ground Truth Lab evaluates LLM and agent workflow regressions: structured
output validity, unsafe auto-approval, routing, cost, latency, and accuracy.
In the three-project stack, it is the quality layer between `gdev-agent` as the
workflow under test and Agent Runtime Grid as the batch execution layer.

## Dataset Versioning

Datasets are JSONL or YAML case files with stable content hashes. The gdev-agent
dataset records 55 synthetic triage cases and hash
`ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb`.

Eval Lab also includes `datasets/gdev_agent/challenge_v1.jsonl`, a 100-case
diagnostic challenge set for ambiguous, policy-stress, guard-stress,
tenant-boundary, malformed-input, and expected-failure cases. This challenge set
is not a passing baseline; it is the hard-case surface for future candidate
diagnostics.

## Baseline Candidate Comparison

Baseline and candidate runs are atomic, checksum-sealed JSON artifacts whose
terminal state cannot be mutated through RunStore. Comparisons reject
dataset hash mismatch and report accuracy, invalid output, unsafe
auto-approval, latency, and cost deltas against thresholds.

## Deterministic Validators

Deterministic validators own blocking decisions for structure, category, status,
human routing, guard behavior, unsafe auto-approval, confidence, cost, and
latency.

## Unsafe Auto-Approval

Unsafe auto-approval is caught by seeded smoke tests, gdev validators, and
mocked gdev CI smoke. The expected failure path exits with code `1`.

## gdev-agent Eval

The gdev-agent path evaluates a real local workflow boundary through the
configured `/webhook` adapter. CI uses mocked transport; live local integration
requires the operator to start gdev-agent in deterministic demo mode. The
current canonical live local baseline covers all 55 gdev-agent triage cases with
zero adapter errors and zero deterministic validator failures.

This 55-case result should be read as integration/conformance evidence. It does
not replace gdev-agent's broader 180-case internal smoke eval, which remains a
separate gap-discovery surface for demo-policy routing and classification
quality.

The committed challenge report
`reports/gdev-agent/challenge_report.md` documents the harder diagnostic set and
the intended metrics: `pass_rate_by_slice`, `expected_failure_matched`,
`unexpected_pass_count`, `unexpected_fail_count`, and
`human_review_required_count`.

## Stack Integration

The current stack has three concrete paths:

- Eval Lab calls live local gdev-agent over HTTP and writes deterministic quality
  reports.
- Agent Runtime Grid consumes ready Eval Lab/gdev evidence as queued artifact
  jobs and writes runtime reliability reports.
- Agent Runtime Grid can also run an optional `full-stack-live-local` proof where
  queued workers call a local gdev-agent HTTP endpoint and store sanitized
  runtime artifacts.

The Runtime Grid modes remain separate from Eval Lab's deterministic quality
authority. Artifact proof is the reproducible default; live-local proof is
operator-run local evidence, not production traffic or continuous eval. The
latest committed Runtime Grid snapshot records 20/20 queued local HTTP jobs
against local demo-mode gdev-agent on 2026-06-15.

## Synthetic vs Real Integration

Committed datasets and reports are synthetic/local deterministic evidence. The
integration boundary is real for the live local baseline, but committed
artifacts do not claim production quality or production traffic coverage.

## Cost and Latency

Run artifacts record cost and latency per case. The current gdev-agent demo-mode
baseline returns deterministic `0.0000` per-case cost telemetry. Cost telemetry
rollup aggregates JSONL entries by model, workflow, and case, and budget-check
exits `1` on overrun.

## Non-Authoritative Judge

The optional OpenAI judge provider is disabled without credentials and positive
budget. Judge output can route ambiguous cases to human review, but it cannot
override deterministic blocking failures.

## Known Limits

Known limits are tracked in `docs/KNOWN_LIMITS.md`. The project is not a
production eval platform, dashboard, hosted service, or universal safety proof.
