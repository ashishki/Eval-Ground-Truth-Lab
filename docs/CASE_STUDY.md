# Case Study

## What Eval Lab Evaluates

Eval Ground Truth Lab evaluates LLM and agent workflow regressions: structured
output validity, unsafe auto-approval, routing, cost, latency, and accuracy.

## Dataset Versioning

Datasets are JSONL or YAML case files with stable content hashes. The gdev-agent
dataset records 55 synthetic triage cases and hash
`ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb`.

## Baseline Candidate Comparison

Baseline and candidate runs are immutable JSON artifacts. Comparisons reject
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
