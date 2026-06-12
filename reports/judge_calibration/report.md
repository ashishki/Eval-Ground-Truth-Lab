# Judge Calibration Report

## Summary

This report records the first optional judge provider contract evidence. It uses
synthetic calibration fixtures and fake transport tests only. No live provider
calls were made.

## Evidence

| Artifact | Purpose |
|----------|---------|
| `tests/judging/test_provider_contract.py` | Provider disabled state, structured output contract, budget precheck, telemetry, and human review routing. |
| `datasets/judge_calibration/ambiguous_cases.jsonl` | Synthetic ambiguous cases for calibration documentation. |
| `docs/JUDGE_CALIBRATION.md` | Provider boundary and non-authoritative judge rules. |

## Boundaries

- The provider is disabled without a key and a positive budget.
- Budget precheck happens before provider call.
- Telemetry records token, cost, latency, retry, model, and quality outcome
  fields.
- Ambiguous judge output routes to human review.
- Deterministic failures remain blocking and cannot be overridden by judge
  output.
