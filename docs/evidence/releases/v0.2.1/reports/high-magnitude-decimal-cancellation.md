# Eval Report

## Run Metadata

| Field | Value |
|-------|-------|
| Dataset hash | `1f3321f4b7512bf34ab19c661cdaded83d5b9403d6f56bb29ee0ba71f0cacabd` |
| Baseline run | `high-magnitude-decimal-baseline` |
| Candidate run | `high-magnitude-decimal-candidate` |
| Baseline candidate version | `eval-lab-0.2.1-synthetic-high-magnitude-decimal-baseline` |
| Candidate version | `eval-lab-0.2.1-synthetic-high-magnitude-decimal-candidate` |
| Validator version | `fail-closed-evidence-validators-v1` |
| Threshold config | `v0.2.1-exact-comparison-policy` |

## Threshold Summary

| Metric | Exact delta | Gate | Status |
|--------|-------------|------|--------|
| `accuracy_delta` | `0` | `delta ≥ 0` | `pass` |
| `invalid_output_rate` | `0` | `delta ≤ 0` | `pass` |
| `unsafe_auto_approval_rate` | `0` | `delta ≤ 0` | `pass` |
| `latency_ms_p95_delta` | `0` | `delta ≤ 0` | `pass` |
| `cost_per_case_delta` | `0.1` | `delta ≤ 0.09999` | `fail` |

## Top Failure Categories

| Category | Count |
|----------|-------|
| `cost_regression` | 1 |

## Case-Level Failures

No case-level failures.

## Raw Artifact Links

- baseline run: `inputs/high-magnitude-decimal-baseline.json`
- candidate run: `inputs/high-magnitude-decimal-candidate.json`
- threshold config: `inputs/high-magnitude-decimal-thresholds.json`
