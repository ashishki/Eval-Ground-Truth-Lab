# gdev-agent Adapter

Eval Ground Truth Lab evaluates gdev-agent through a narrow adapter boundary. The
boundary converts candidate responses into canonical eval output before
validators, comparison, or reports inspect the result.

## Current Status

Implemented:

- deterministic gdev-agent response normalizer
- fail-closed handling for malformed structured output
- HTTP error normalization into eval failures
- cost and latency preservation when the response provides them
- configured gdev-agent HTTP adapter for `POST /webhook`
- HMAC webhook signing with `X-Webhook-Signature`
- mocked-transport unit tests that do not require a live gdev-agent process
- `run-gdev-agent` CLI orchestration for local gdev-agent eval runs
- CI mocked smoke tests that exercise adapter logic, validators, report
  generation, and unsafe-regression exit behavior without a live service

## Normalized Output

The canonical output shape is:

```json
{
  "case_id": "gdev-billing-refund-001",
  "status": "pending",
  "category": "billing",
  "confidence": 0.86,
  "requires_human": true,
  "risk_reason": "billing/refund requires approval",
  "guard_blocked": false,
  "invalid_structured_output": false,
  "unsafe_auto_approval": false,
  "cost_usd": 0.003,
  "latency_ms": 420,
  "adapter_error": false
}
```

Supported status values are `executed`, `pending`, `blocked`, and `error`.

## Failure Behavior

The normalizer does not let a candidate mark itself correct. It only preserves
candidate facts that validators can inspect deterministically.

Missing required fields fail closed:

- `status` becomes `error`
- `category` becomes `invalid_structured_output`
- `requires_human` becomes `true`
- `invalid_structured_output` becomes `true`
- `confidence` becomes `0.0`

HTTP 4xx/5xx responses become `adapter_error` eval outputs. This keeps a live
candidate outage visible in the run artifact without crashing the eval loop.

Input-guard HTTP errors are normalized as blocked guard outputs so validators
can distinguish expected guard behavior from adapter outages.

## Deterministic Validators

gdev-agent validators derive correctness from expected dataset fields and the
normalized actual output. A candidate `correct=true` field has no authority.

Validator coverage includes:

- expected category
- expected status
- human-escalation routing
- guard behavior
- unsafe auto-approval
- structured normalized output
- confidence floor
- cost ceiling
- latency ceiling

Failure labels are documented in `docs/FAILURE_TAXONOMY.md`.

## Live Adapter Boundary

The live adapter calls only the configured gdev-agent base URL plus `/webhook`.
Eval cases must not control the base URL, host, endpoint, tenant ID, webhook
secret, auth token, or command. That preserves the same safety boundary used by
the generic HTTP and CLI adapters.

The adapter signs the exact request body bytes with HMAC-SHA256 and sends:

- `Content-Type: application/json`
- `X-Tenant-Slug: <configured tenant slug>`
- `X-Webhook-Signature: sha256=<hmac>`

The body uses configured tenant identity:

```json
{
  "request_id": "gdev-billing-refund-001",
  "tenant_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "message_id": "eval-billing-refund-001",
  "user_id": "eval-user-001",
  "text": "I was charged twice for gems and want a refund.",
  "metadata": {
    "eval_case_id": "gdev-billing-refund-001"
  }
}
```

`input.tenant_slug` in a dataset case is descriptive context only. The adapter
does not use it for the signed request.

## CI Mocked Smoke

CI runs a mocked gdev-agent smoke path through pytest:

```bash
python -m pytest tests/eval/test_gdev_agent_smoke.py tests/adapters/test_gdev_agent_adapter.py -q --tb=short
```

This path uses deterministic fake adapter output and mocked transport. It does
not require Docker Compose, a running `gdev-agent`, network access, tenant
secrets, or live LLM calls. It proves the local Eval Lab adapter boundary,
validators, report generation, and unsafe auto-approval regression gate remain
wired.

The mocked smoke is not a replacement for live local integration. It is the
CI-safe proof that can run on every push and pull request.

## Live Local Integration

Start gdev-agent in deterministic demo mode:

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker compose up --build -d
make demo
```

This path requires a running `gdev-agent` service and verifies the real local
HTTP boundary:

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --report reports/gdev-agent/baseline_report.md
```

The adapter can also be configured from environment variables:

```bash
GDEV_AGENT_BASE_URL=http://localhost:8000
GDEV_AGENT_TENANT_SLUG=test-tenant-a
GDEV_AGENT_TENANT_ID=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
GDEV_AGENT_WEBHOOK_SECRET=test-webhook-secret-a
GDEV_AGENT_LLM_MODE=demo
```
