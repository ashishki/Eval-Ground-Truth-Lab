# gdev-agent Eval Dataset

Status: planned integration dataset
Version: `gdev-triage-v1`

## Purpose

`datasets/gdev_agent/triage_v1.jsonl` is the first dataset for evaluating a
locally running gdev-agent triage workflow. It is synthetic data only and is
designed to exercise routing, guard behavior, human escalation, structured
output validity, cost, and latency.

## Case Shape

Each case contains:

- `id`: stable case identifier.
- `input.tenant_slug`: synthetic test tenant.
- `input.message_id`: synthetic message ID.
- `input.user_id`: synthetic user ID.
- `input.text`: synthetic user message.
- `expected.category`: expected triage category.
- `expected.requires_human`: whether the case must route to human review.
- `expected.expected_status`: expected workflow status.
- `expected.guard_behavior`: `allow_input` or `block_input`.
- `expected.unsafe_auto_approval_allowed`: always `false` for high-risk slices.
- `metadata.slice`: coverage slice.
- `metadata.risk`: concise risk label.
- `metadata.synthetic`: always `true`.

## Required Slice Coverage

- `billing_refund`
- `account_access`
- `bug_report`
- `moderation_report`
- `legal_gdpr`
- `low_confidence`
- `prompt_injection`
- `unsafe_url`
- `secret_leak_attempt`
- `duplicate_webhook`
- `cross_tenant_boundary`

## Boundaries

The dataset must not contain real user data, secrets, tokens, credential paths,
network destinations, shell commands, or package installation instructions.
Adapter configuration owns any gdev-agent URL or webhook secret used during live
local integration.
