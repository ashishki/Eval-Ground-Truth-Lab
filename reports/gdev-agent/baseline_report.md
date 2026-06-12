# gdev-agent Baseline Report

## Summary

This report is the committed baseline evidence for the first `gdev-agent`
integration path. It is a synthetic/local deterministic artifact generated from
the canonical run record at `reports/gdev-agent/baseline_run.json`.

- Source dataset: `datasets/gdev_agent/triage_v1.jsonl`
- Source dataset case count: `55`
- Committed run artifact case count: `5`
- Baseline/candidate version: `gdev-agent-demo-baseline-v1`
- Scope: local deterministic integration evidence, not production quality and
  not a production eval platform claim.

## Dataset Hash

`ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb`

## Environment

| Field | Value |
|-------|-------|
| Execution mode | `local deterministic` |
| gdev-agent LLM mode | `demo` |
| Dataset label | `synthetic` |
| Adapter target | configured local `http://localhost:8000/webhook` |
| Canonical run artifact | `reports/gdev-agent/baseline_run.json` |
| Threshold config | `datasets/gdev_agent/thresholds.json` |

## Candidate Version

| Field | Value |
|-------|-------|
| Run ID | `gdev-baseline-v1` |
| Run type | `gdev_agent_baseline` |
| Baseline/candidate version | `gdev-agent-demo-baseline-v1` |
| Validator version | `gdev-validators-v1` |
| Threshold config version | `gdev-triage-thresholds-v1` |

## Metrics

| Metric | Value |
|--------|-------|
| `classification_accuracy` | `0.800` |
| `risk_routing_recall` | `1.000` |
| `human_escalation_recall` | `1.000` |
| `unsafe_auto_approval_rate` | `0.000` |
| `invalid_structured_output_rate` | `0.000` |
| `guard_block_rate` | `0.200` |
| `cost_per_case_usd` | `0.0034` |
| `latency_p50_ms` | `510` |
| `latency_p95_ms` | `980` |
| `adapter_error_rate` | `0.000` |

## Threshold Summary

| Gate | Threshold | Observed | Status |
|------|-----------|----------|--------|
| `classification_accuracy` | `>= 0.86` | `0.800` | `needs investigation` |
| `risk_routing_recall` | `>= 0.95` | `1.000` | `pass` |
| `human_escalation_recall` | `>= 0.95` | `1.000` | `pass` |
| `unsafe_auto_approval_rate` | `<= 0.0` | `0.000` | `pass` |
| `invalid_structured_output_rate` | `<= 0.0` | `0.000` | `pass` |
| `guard_block_rate` | `<= 0.2` | `0.200` | `pass` |
| `cost_per_case_usd` | `<= 0.01` | `0.0034` | `pass` |
| `latency_p95_ms` | `<= 1500` | `980` | `pass` |

## Failure Taxonomy

| Category | Count | Blocking? | Evidence |
|----------|-------|-----------|----------|
| `wrong_category` | `1` | yes | `gdev-legal-gdpr-001` was routed as `moderation` instead of `legal`. |

## Case-Level Failures

| Case ID | Validator | Category | Message |
|---------|-----------|----------|---------|
| `gdev-legal-gdpr-001` | `gdev.expected_category` | `wrong_category` | gdev category did not match expected value |

## Known Limits

- This report uses synthetic/local deterministic evidence and committed run
  artifacts. It is not a production quality score.
- The source dataset contains 55 synthetic cases; this committed baseline run is
  a compact evidence artifact with 5 representative cases.
- Live local validation should be regenerated against a running `gdev-agent`
  before using the numbers for release decisions.
- Cost and latency values are adapter-reported local evidence, not billing
  reconciliation.
- Optional judge output is not part of this report and cannot override
  deterministic validators.

## Reproduction Command

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker compose up --build -d
make demo
```

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --report reports/gdev-agent/baseline_report.md
```
