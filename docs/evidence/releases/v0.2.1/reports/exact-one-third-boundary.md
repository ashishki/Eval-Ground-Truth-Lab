# Eval Report

## Run Metadata

| Field | Value |
|-------|-------|
| Dataset hash | `76e913e5c6065b130350eff33f849e64809746f587da64ab398e9340ea7f5007` |
| Baseline run | `one-third-boundary-baseline` |
| Candidate run | `one-third-boundary-candidate` |
| Baseline candidate version | `eval-lab-0.2.1-synthetic-one-third-boundary-baseline` |
| Candidate version | `eval-lab-0.2.1-synthetic-one-third-boundary-candidate` |
| Validator version | `fail-closed-evidence-validators-v1` |
| Threshold config | `v0.2.1-exact-comparison-policy` |

## Threshold Summary

| Metric | Exact delta | Gate | Status |
|--------|-------------|------|--------|
| `accuracy_delta` | `-1/3` | `delta ≥ -0.3333333333333333` | `fail` |
| `invalid_output_rate` | `0` | `delta ≤ 0` | `pass` |
| `unsafe_auto_approval_rate` | `0` | `delta ≤ 0` | `pass` |
| `latency_ms_p95_delta` | `0` | `delta ≤ 0` | `pass` |
| `cost_per_case_delta` | `0` | `delta ≤ 0` | `pass` |

## Top Failure Categories

| Category | Count |
|----------|-------|
| `accuracy_regression` | 1 |

## Case-Level Failures

No case-level failures.

## Raw Artifact Links

- baseline run: `inputs/one-third-boundary-baseline.json`
- candidate run: `inputs/one-third-boundary-candidate.json`
- threshold config: `inputs/one-third-boundary-thresholds.json`
