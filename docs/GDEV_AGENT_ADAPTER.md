# gdev-agent Adapter

Eval Ground Truth Lab evaluates gdev-agent through a narrow adapter boundary. The
boundary converts candidate responses into canonical eval output before
validators, comparison, or reports inspect the result.

## Current Status

Implemented in this phase:

- deterministic gdev-agent response normalizer
- fail-closed handling for malformed structured output
- HTTP error normalization into eval failures
- cost and latency preservation when the response provides them

The live HTTP adapter is a following task. This document names that boundary so
the normalizer contract is clear before network integration is added.

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

## Live Adapter Boundary

The future live adapter will call only configured gdev-agent destinations. Eval
cases must not control the base URL, host, endpoint, webhook secret, auth token,
or command. That preserves the same safety boundary used by the generic HTTP and
CLI adapters.
