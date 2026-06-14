# gdev-agent Challenge Set

Status: committed diagnostic dataset, not a passing baseline.
Last updated: 2026-06-14

## Purpose

`datasets/gdev_agent/challenge_v1.jsonl` is a harder companion to the
55-case `triage_v1` integration baseline. Its manifest is
`datasets/gdev_agent/challenge_manifest.json`, with dataset hash
`151e5eec83373b92cf263aa1f32edb26ed780c260ce32a9d084ba8f3f38e53b0`.
It exists to show where a `gdev-agent` candidate is robust, where it needs
human review, and where the eval harness should preserve expected failures
instead of turning every run into a clean demo.

The challenge set is not a production benchmark and is not claimed as a
quality score. It is synthetic/local portfolio evidence for eval maturity.

## Scope Split

| Dataset | Cases | Purpose | Expected Shape |
|---------|------:|---------|----------------|
| `triage_v1.jsonl` | 55 | Live local integration/conformance proof | Should pass against current deterministic demo-mode `gdev-agent` |
| `challenge_v1.jsonl` | 100 | Hard-case diagnostic surface | May include failures, expected failures, and human-review-heavy cases |

## Slices

| Slice | Cases | What It Stresses |
|-------|------:|------------------|
| `ambiguous_multi_intent` | 10 | Multiple categories in one ticket; should prefer uncertainty and human review |
| `refund_pressure` | 10 | Billing requests that ask for unsafe auto-approval |
| `account_takeover` | 10 | Account recovery and ownership-transfer pressure |
| `moderation_edge` | 10 | Context-dependent moderation reports |
| `legal_privacy` | 10 | Data access, deletion, objection, and guardian requests |
| `obfuscated_injection` | 10 | Prompt-injection and policy-override attempts |
| `unsafe_link_social` | 10 | Phishing/social-engineering reports |
| `cross_tenant_escalation` | 10 | Tenant isolation and cross-tenant routing pressure |
| `malformed_user_input` | 10 | Vague, noisy, or underspecified user input |
| `provider_error_simulation` | 10 | Harness-level expected failures for adapter/provider faults |

## Metadata Contract

Every case includes the baseline gdev expected fields:

- `category`
- `requires_human`
- `expected_status`
- `guard_behavior`
- `unsafe_auto_approval_allowed`

Every case also includes challenge metadata:

- `slice`
- `risk`
- `synthetic`
- `challenge_type`
- `expected_failure`
- `human_review_required`

Expected-failure cases are intentionally marked in metadata. They are designed
for future harness support that reports:

- `expected_failure_matched`
- `unexpected_pass_count`
- `unexpected_fail_count`
- `blocking_failure_count`
- `human_review_required_count`
- `pass_rate_by_slice`

## Running

Inspect the dataset without a live `gdev-agent`:

```bash
python -m eval_ground_truth_lab.cli dataset-inspect \
  --dataset datasets/gdev_agent/challenge_v1.jsonl
```

Optional live diagnostic run:

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/challenge_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-challenge-v1 \
  --candidate-version gdev-agent-demo-challenge-v1 \
  --threshold-config datasets/gdev_agent/challenge_thresholds.json \
  --report reports/gdev-agent/challenge_report.md
```

The optional live command is expected to be diagnostic. A non-zero exit can be
useful evidence when failures are categorized and documented.

## Known Limits

- The committed report is a scope and expected-results report, not a live run
  artifact.
- Expected-failure matching is documented here but not yet a first-class CLI
  summary.
- Provider-error simulation cases need a harness/adapter fault-injection path
  to be fully exercised.
- The data is synthetic and local; it does not represent real users or
  external adoption.
