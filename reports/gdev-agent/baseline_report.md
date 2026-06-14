# gdev-agent Baseline Report

## Summary

This report is the committed live local baseline evidence for the first
`gdev-agent` integration path. It is a synthetic/local deterministic artifact
generated from the canonical run record at
`reports/gdev-agent/baseline_run.json`.

- Source dataset: `datasets/gdev_agent/triage_v1.jsonl`
- Source dataset case count: `55`
- Committed run artifact case count: `55`
- Baseline/candidate version: `gdev-agent-demo-live-local-v2`
- Live local result: `55` cases, `0` adapter errors, `0` validator failures
- Scope: local deterministic integration evidence, not production quality and
  not a production eval platform claim.

## Dataset Hash

`ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb`

## Environment

| Field | Value |
|-------|-------|
| Execution mode | `live local deterministic` |
| gdev-agent LLM mode | `demo` |
| Dataset label | `synthetic` |
| Adapter target | configured local `http://localhost:8000/webhook` |
| Canonical run artifact | `reports/gdev-agent/baseline_run.json` |
| CLI run artifact | `runs/gdev-baseline-v1.json` |
| Threshold config | `datasets/gdev_agent/thresholds.json` |

## Candidate Version

| Field | Value |
|-------|-------|
| Run ID | `gdev-baseline-v1` |
| Run type | `candidate` |
| Baseline/candidate version | `gdev-agent-demo-live-local-v2` |
| Validator version | `gdev-validators-v1` |
| Threshold config version | `gdev-triage-thresholds-v1` |

## Metrics

| Metric | Value |
|--------|-------|
| `classification_accuracy` | `1.000` |
| `risk_routing_recall` | `1.000` |
| `human_escalation_recall` | `1.000` |
| `unsafe_auto_approval_rate` | `0.000` |
| `invalid_structured_output_rate` | `0.000` |
| `guard_block_rate` | `0.364` |
| `cost_per_case_usd` | `0.0000` |
| `latency_p50_ms` | `202` |
| `latency_p95_ms` | `239` |
| `adapter_error_rate` | `0.000` |

## Threshold Summary

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| `classification_accuracy` | `>= 0.86` | `1.000` | `pass` |
| `risk_routing_recall` | `>= 0.95` | `1.000` | `pass` |
| `human_escalation_recall` | `>= 0.95` | `1.000` | `pass` |
| `unsafe_auto_approval_rate` | `<= 0.0` | `0.000` | `pass` |
| `invalid_structured_output_rate` | `<= 0.0` | `0.000` | `pass` |
| `guard_behavior` | per-case expected behavior | `55/55` | `pass` |
| `cost_per_case_usd` | `<= 0.01` | `0.0000` | `pass` |
| `latency_p95_ms` | `<= 1500` | `239` | `pass` |

## Failure Taxonomy

No failures.

## Case-Level Failures

No case-level failures.

## Known Limits

- This report uses synthetic/local deterministic evidence against a local
  `gdev-agent` demo-mode stack. It is not a production quality score.
- The source dataset contains 55 synthetic cases and all 55 are present in the
  canonical committed run artifact.
- This is a curated integration/conformance baseline. It is not a hard
  challenge set and does not replace broader gdev-agent internal smoke evals.
- Cost telemetry is present on every normalized response. Demo-mode local
  execution reports deterministic `0.0000` cost per case, not billing
  reconciliation.
- `guard_block_rate` is a descriptive aggregate for this dataset. The live
  acceptance gate is the per-case `gdev.guard_behavior` validator.
- Optional judge output is not part of this report and cannot override
  deterministic validators.

## Reproduction Command

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker-compose up --build -d postgres redis migrate agent
make demo
```

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --candidate-version gdev-agent-demo-live-local-v2 \
  --report reports/gdev-agent/baseline_report.md
```
