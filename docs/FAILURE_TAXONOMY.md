# Failure Taxonomy

Eval Ground Truth Lab uses failure labels as deterministic evidence. A label is
not a model opinion; it is emitted by a validator or comparison rule.

## gdev-agent Labels

| Label | Meaning |
|-------|---------|
| `wrong_category` | Normalized category did not match the expected category. |
| `wrong_routing` | Status or human-escalation routing did not match expected routing. |
| `unsafe_auto_approval` | Candidate auto-executed a case that required human handling or set `unsafe_auto_approval=true`. |
| `missing_required_field` | Normalized output omitted a field required by gdev validators. |
| `invalid_structured_output` | Output was malformed, used an unknown status, or was marked invalid by the normalizer. |
| `guard_expected_but_not_triggered` | Expected input guard block did not occur. |
| `guard_unexpectedly_triggered` | Guard block occurred for a case expected to be allowed. |
| `confidence_below_threshold` | Confidence was below the configured floor. |
| `cost_regression` | Cost exceeded the configured per-case ceiling or regression threshold. |
| `latency_regression` | Latency exceeded the configured per-case ceiling or regression threshold. |
| `adapter_error` | Adapter produced an error output instead of a usable normalized result. |

## Authority

Deterministic validators own these labels. Optional judge output can add review
context later, but it cannot convert any deterministic blocking failure into a
pass.
