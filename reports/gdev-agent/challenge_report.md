# gdev-agent Challenge Report

Status: committed diagnostic report, not a passing baseline.
Generated from: `datasets/gdev_agent/challenge_v1.jsonl`
Manifest: `datasets/gdev_agent/challenge_manifest.json`
Dataset hash:
`151e5eec83373b92cf263aa1f32edb26ed780c260ce32a9d084ba8f3f38e53b0`
Threshold policy: `datasets/gdev_agent/challenge_thresholds.json`
Last updated: 2026-06-14

## Summary

The gdev-agent challenge set contains 100 synthetic hard cases. It complements
the 55-case `triage_v1` integration/conformance baseline by adding ambiguous,
policy-stress, guard-stress, tenant-boundary, malformed-input, and
expected-failure cases.

This report is intentionally not a 100 percent pass claim. Its purpose is to
make hard cases reviewable before a live challenge run is promoted as canonical
evidence.

## Dataset Shape

| Metric | Value |
|--------|------:|
| Total cases | 100 |
| Slices | 10 |
| Cases per slice | 10 |
| Expected-failure cases | 10 |
| Human-review-required cases | 100 |
| Synthetic cases | 100 |

## Slice Inventory

| Slice | Cases | Expected Behavior |
|-------|------:|-------------------|
| `ambiguous_multi_intent` | 10 | Escalate uncertain multi-intent tickets |
| `refund_pressure` | 10 | Route billing/refund pressure to human review |
| `account_takeover` | 10 | Route account recovery pressure to human review |
| `moderation_edge` | 10 | Route context-dependent moderation to human review |
| `legal_privacy` | 10 | Route privacy/legal requests to human review |
| `obfuscated_injection` | 10 | Block policy-override and prompt-injection attempts |
| `unsafe_link_social` | 10 | Block phishing/social-engineering reports |
| `cross_tenant_escalation` | 10 | Block cross-tenant access/routing pressure |
| `malformed_user_input` | 10 | Escalate vague or underspecified inputs |
| `provider_error_simulation` | 10 | Preserve expected harness/provider failures |

## Intended Metrics

Future live challenge reports should include:

- `pass_rate_by_slice`
- `blocking_failure_count`
- `expected_failure_matched`
- `unexpected_pass_count`
- `unexpected_fail_count`
- `human_review_required_count`
- `judge_optional_cases`

## Reproduction Command

```bash
python -m eval_ground_truth_lab.cli dataset-inspect \
  --dataset datasets/gdev_agent/challenge_v1.jsonl
```

Optional diagnostic live run:

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/challenge_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-challenge-v1 \
  --candidate-version gdev-agent-demo-challenge-v1 \
  --threshold-config datasets/gdev_agent/challenge_thresholds.json \
  --report reports/gdev-agent/challenge_report.md
```

## Known Limits

- This committed report is a dataset and threshold-policy evidence snapshot,
  not a completed live challenge run.
- Expected-failure matching is not yet surfaced by the `run-gdev-agent` CLI as
  a dedicated challenge summary.
- Provider-error simulation cases require explicit adapter/harness
  fault-injection before they can be treated as fully exercised.
- The challenge set is synthetic/local evidence and does not claim production
  quality, real user adoption, or hosted operations.
