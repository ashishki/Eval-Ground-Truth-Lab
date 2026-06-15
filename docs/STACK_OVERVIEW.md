# AI Systems Reliability Stack

Eval Ground Truth Lab is the quality and regression layer in a three-project
local evidence stack for reliable AI/agent systems.

## System Map

| Layer | Repository | Role | Current evidence |
| --- | --- | --- | --- |
| Governed workflow | `gdev-agent` | Multi-tenant support-triage workflow with webhook intake, guardrails, approval, audit, cost, and observability controls. | Local Compose demo, 285-test repository baseline, 180-case internal smoke eval. |
| Quality layer | `Eval-Ground-Truth-Lab` | Deterministic evaluation framework for structured output, routing, unsafe auto-approval, cost, latency, and adapter behavior. | 55-case live local gdev-agent integration baseline, 100-case diagnostic challenge set, seeded regression smoke, immutable run artifacts. |
| Runtime layer | `Agent-Runtime-Grid` | Queue-backed runtime for running many AI/agent jobs with retries, timeouts, idempotent finalization, artifacts, metrics, and cost controls. | 100-job smoke, 500-job reliability proof, failure-injection reports, cross-project artifact proof, and 20-job operator-run live-local HTTP proof snapshot. |

## Current End-To-End Evidence

The strongest live local path today is:

```text
Eval Ground Truth Lab
  -> gdev-agent HTTP adapter
  -> local gdev-agent /webhook
  -> deterministic validators
  -> reports/gdev-agent/baseline_report.md
  -> reports/gdev-agent/baseline_run.json
```

That path validates 55 synthetic triage cases against a live local gdev-agent in
`LLM_MODE=demo`. It is a conformance/integration baseline, not a production
quality score and not a hard challenge benchmark.

Eval Lab also commits a harder 100-case gdev-agent challenge set. That dataset
is diagnostic evidence for ambiguous, policy-stress, guard-stress,
tenant-boundary, malformed-input, and expected-failure cases; it is not a
replacement for the canonical passing baseline.

Runtime Grid's default cross-project mode adds artifact-linked runtime proof:

```text
Agent Runtime Grid
  -> selected Eval Lab / gdev cases as queued jobs
  -> Redis Streams workers
  -> Postgres lifecycle state
  -> runtime artifacts and reliability report
  -> links back to Eval Lab quality evidence
```

That proof is intentionally named as artifact proof: it does not call live
gdev-agent over HTTP by default. Runtime Grid also has a separate optional
`full-stack-live-local` mode that runs queued workers against a local gdev-agent
HTTP endpoint and writes sanitized runtime artifacts. That mode is still
operator-run local evidence, not hosted operations or continuous eval. The
latest committed Runtime Grid snapshot records 20/20 queued local HTTP jobs
completed against a local demo-mode gdev-agent stack on 2026-06-15.

## Agent And Provider Model

In this stack an agent is a bounded job/workflow contract:

- input schema
- output schema
- allowed tools or side effects
- model/provider policy
- timeout and cost budget
- guardrail and approval rules
- eval cases and validators

Default evidence mode stays deterministic: `demo` in gdev-agent, `stub` in
Runtime Grid, and fake/budgeted providers for optional Eval Lab judge tests.

Current provider facts:

- gdev-agent implements Anthropic as its live triage provider path.
- Eval Lab has an optional OpenAI judge provider contract, but judge output is
  non-authoritative and disabled by default.
- Runtime Grid keeps general model-router live jobs future; its current
  live-local proof calls local gdev-agent HTTP instead of owning a model
  provider.

## What This Proves

- gdev-agent can be evaluated as a live local system under test.
- Eval Lab can normalize, validate, and report deterministic quality signals.
- Runtime Grid can run evidence-linked agent/eval jobs under queue-backed
  lifecycle controls, including an optional local HTTP proof path.

## What Is Not Claimed

This stack is v1 local evidence. It does not claim external adoption, real user
traffic, hosted operations, production SLOs, or universal agent safety.
