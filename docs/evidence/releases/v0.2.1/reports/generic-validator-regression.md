# Eval Report

## Run Metadata

| Field | Value |
|-------|-------|
| Dataset hash | `1f3321f4b7512bf34ab19c661cdaded83d5b9403d6f56bb29ee0ba71f0cacabd` |
| Baseline run | `fail-closed-common-baseline` |
| Candidate run | `generic-validator-regression-candidate` |
| Baseline candidate version | `eval-lab-0.2.1-synthetic-fail-closed-common-baseline` |
| Candidate version | `eval-lab-0.2.1-synthetic-generic-validator-regression-candidate` |
| Validator version | `fail-closed-evidence-validators-v1` |
| Threshold config | `v0.2.1-exact-comparison-policy` |

## Threshold Summary

| Metric | Exact delta | Gate | Status |
|--------|-------------|------|--------|
| `accuracy_delta` | `0` | `delta ≥ 0` | `pass` |
| `invalid_output_rate` | `0` | `delta ≤ 0` | `pass` |
| `unsafe_auto_approval_rate` | `0` | `delta ≤ 0` | `pass` |
| `latency_ms_p95_delta` | `0` | `delta ≤ 0` | `pass` |
| `cost_per_case_delta` | `0` | `delta ≤ 0` | `pass` |

## Top Failure Categories

| Category | Count |
|----------|-------|
| `arbitrary_validator_regression` | 1 |

## Case-Level Failures

| Case ID | Category | Validator | Message |
|---------|----------|-----------|---------|
| `case-1` | `arbitrary_validator_regression` | `evidence.output_contract` | candidate validator changed from pass to fail |

## Raw Artifact Links

- baseline run: `inputs/common-passing-baseline.json`
- candidate run: `inputs/generic-validator-regression-candidate.json`
- threshold config: `inputs/zero-thresholds.json`

## Validator Receipt Regressions

| Gate | Status | Count |
|------|--------|-------|
| `validator_receipt_regression` | `fail` | 1 |

| Case ID | Validator | Candidate category |
|---------|-----------|--------------------|
| `case-1` | `evidence.output_contract` | `arbitrary_validator_regression` |
