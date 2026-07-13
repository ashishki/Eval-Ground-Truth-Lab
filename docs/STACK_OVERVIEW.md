# AI Systems Reliability Stack

Eval Ground Truth Lab is the quality and regression layer in a three-project
local evidence stack for reliable AI/agent systems.

## System Map

| Layer | Repository | Role | Current evidence |
| --- | --- | --- | --- |
| Governed workflow | `gdev-agent` | Local support-triage workload with webhook intake, guardrails, approval, audit, cost, and database-enforced tenant controls. | Green P0 repository/Compose proof, 180-case internal smoke with weak quality metrics, and an external 100-case Eval Lab gate that fails. |
| Quality layer | `Eval-Ground-Truth-Lab` | Deterministic release-decision tool for structured output, routing, unsafe auto-approval, cost, latency, and adapter behavior. | 55-case local conformance pass, canonical 100-case hard-challenge FAIL, seeded regression smoke, sealed runs, and content-addressed evidence. |
| Runtime layer | `Agent-Runtime-Grid` | Queue-backed runtime for running many AI/agent jobs with retries, timeouts, idempotent finalization, artifacts, metrics, and cost controls. | Tagged `v0.1.0` with a verified 20-job local stub run plus separate larger/local failure-injection paths. |

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

Eval Lab also publishes a harder 100-case gdev-agent challenge run. That public
development dataset covers ambiguous, policy-stress, guard-stress,
tenant-boundary, malformed-input, and expected-failure cases. The exact
candidate records a canonical gate FAIL; the passing 55-case conformance scope
does not override it.

The case counts are separate scopes, not a combined score: gdev-agent's 180
internal smoke cases exercise that repository; Eval Lab's 55 external cases are
integration/conformance evidence; Eval Lab's 100 challenge cases are a harder
diagnostic contract with ten harness-injected provider failures.

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

Trader Risk Audit is an additional applied workload, not a fourth stack layer.
Its separate publication candidate exports sanitized deterministic observations;
Eval Lab verifies one pinned fully synthetic export and applies exact versioned
expectations. That path is contract-compatibility evidence only. It does not
run the Trader engine, inspect raw trades, establish financial quality, or count
as an external adapter/user case study.

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
