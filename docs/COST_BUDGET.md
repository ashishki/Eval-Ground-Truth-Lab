# Cost Budget

Mode: Standard
Owner: human operator
Last updated: 2026-06-12

## Budget Scope

| Scope | Limit | Window | Enforcement |
|-------|-------|--------|-------------|
| Deterministic eval run | 0 USD model spend | per run | block model calls unless judge mode is configured |
| Judge-enabled benchmark run | 2.00 USD recommended cap | per run | block before overrun through judge budget precheck; manual approval for scheduled runs or escalation |
| Operator | 10.00 USD | per day | approval before additional judge runs |
| Project | 25.00 USD provisional cap | per month | approval before exceeding cap |
| Agent / workflow | 300 judge calls, 1 retry per failed call | per run | approval before fan-out or retry expansion |

## Attribution Tags

Every LLM call or judge run must be attributable to:

- project
- task or workflow
- agent/role
- model
- user/operator or service account
- feature/workload
- environment

## Model Routing Budget

| Workload | Default model/class | Escalation allowed when | Cheaper fallback | Verification metric |
|----------|---------------------|--------------------------|------------------|---------------------|
| Deterministic validators | No model | Never | N/A | Validator tests and regression metrics |
| Optional rubric judge | Cheap structured-output judge | Human approves after sampled ambiguity or calibration gap | Disable judge and route to human review | Agreement with human review and no deterministic gate override |
| Failure summarization | Cheap summarizer | Human approves for report-quality gap | Deterministic template from failure table | Report review finds required categories and evidence |
| Suggested taxonomy labels | Cheap classifier or deterministic keyword baseline | Human approves for taxonomy coverage gap | Human review only | Human-reviewed label precision on sampled failures |

## Guardrails

- Max model calls per run: 300.
- Max tool calls per run: not applicable; Tool-Use Profile is OFF.
- Max retries per failing judge call: 1.
- Max parallel agents: 1 in product runtime; development review fan-out follows
  playbook phase gates and human approval.
- Stop condition for repeated equivalent failures: 2 equivalent failed
  correction turns or one projected budget overrun.
- Human approval threshold: any model escalation, retry expansion, fan-out
  increase, scheduled judge run, judge authority increase, or budget overrun.

## Required Measurements

Judge-capable code paths must measure:

- input tokens
- output tokens
- total tokens
- estimated cost
- latency
- retry count
- tool call count where applicable, otherwise `n/a`
- result quality or eval outcome where available

## Telemetry

- Telemetry file: `docs/ai_cost_telemetry.jsonl` by convention; runtime sinks are
  configurable per run.
- Telemetry status: provider-agnostic JSONL telemetry sink implemented in T09.
- Rollup command status: implemented as `python -m eval_ground_truth_lab.cli cost-rollup`.
- Budget check status: implemented as `python -m eval_ground_truth_lab.cli budget-check`.
- CI threshold status: fixture telemetry can be checked in CI. Live judge cost
  gates require telemetry rollup artifacts and an approved budget policy before
  enforcement.

T09 provides budget-capped optional judge execution through an injected provider
boundary. It does not store credentials, call a model provider directly, or allow
judge scores to override deterministic blocking validator failures.

## Rollup Commands

```bash
python -m eval_ground_truth_lab.cli cost-rollup \
  --telemetry docs/ai_cost_telemetry.jsonl \
  --out reports/cost/latest.json
```

```bash
python -m eval_ground_truth_lab.cli budget-check \
  --rollup reports/cost/latest.json \
  --policy docs/cost_policy.json
```

The rollup includes total cost, total tokens, cost by model, cost by workflow,
cost by case, latency p95, retry count, judge call count, and quality outcome
distribution. The budget check exits `1` on per-run, monthly-project,
cost-per-case, or judge-call-count overruns.

Live judge cost gates require telemetry rollup output and an explicitly approved
policy file before enforcement. Fixture telemetry can be used in CI without live
model calls.

## Approval Triggers

Approval is required before:

- changing the default model class
- enabling judge mode in CI
- increasing max judge calls
- increasing retry limits
- adding parallel judge workers
- exceeding per-run, per-day, or monthly budget limits
- allowing judge output to block or pass a candidate

## Review Rule

A cost-saving change is acceptable only when quality and latency stay within the
declared thresholds. A cheaper route that causes retries, rework, or lower pass
rate is not a real saving.
