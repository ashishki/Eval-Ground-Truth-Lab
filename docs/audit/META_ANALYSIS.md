# META_ANALYSIS - Cycle 18

Date: 2026-06-12
Type: targeted

## Project State

Phase 6 is in progress. T21 Cost Rollup and Budget Check is implemented
locally. Next: T22 - Optional Real Judge Provider.

Baseline: 79 pass, 0 skip.

## Open Findings

| ID | Sev | Description | Files | Status |
|----|-----|-------------|-------|--------|
| none | n/a | No open findings in `docs/CODEX_PROMPT.md`; Cycle 17 review had no P0/P1/P2 findings. | n/a | n/a |

## PROMPT_1 Scope (architecture)

- Cost rollup: new `src/eval_ground_truth_lab/cost/rollup.py` reads
  provider-agnostic JSONL telemetry and aggregates total cost, tokens, cost by
  model/workflow/case, p95 latency, retry count, judge call count, and quality
  outcome distribution.
- Budget policy: new `src/eval_ground_truth_lab/cost/policy.py` checks
  per-run budget, monthly project budget, cost-per-case ceiling, and judge call
  count ceiling.
- CLI surface: `cost-rollup` writes rollup JSON; `budget-check` prints check
  result JSON and exits `1` on overrun.
- Fixture safety: tests use `JsonlTelemetrySink` and fixture telemetry only; no
  live model calls, provider SDKs, or judge execution are introduced.
- Docs: `docs/COST_BUDGET.md` and `docs/CLI.md` document commands and state that
  live judge cost gates require telemetry rollup artifacts and an approved
  policy before enforcement.
- Acceptance tests: `tests/cost/test_rollup.py`,
  `tests/cost/test_budget_check.py`, and updated `tests/test_cli.py` cover T21.
- Audit continuity: Cycle 17 review artifacts archived under
  `docs/audit/archive/`.

## PROMPT_2 Scope (code/docs priority order)

1. `src/eval_ground_truth_lab/cost/rollup.py` (new)
2. `src/eval_ground_truth_lab/cost/policy.py` (new)
3. `src/eval_ground_truth_lab/cost/__init__.py` (new)
4. `src/eval_ground_truth_lab/cli.py` (changed)
5. `tests/cost/test_rollup.py` (new)
6. `tests/cost/test_budget_check.py` (new)
7. `tests/test_cli.py` (changed)
8. `docs/COST_BUDGET.md` (changed)
9. `docs/CLI.md` (changed)
10. `README.md` (changed)
11. `docs/README.md` (changed)
12. `docs/CODEX_PROMPT.md` (changed)
13. `docs/EVIDENCE_INDEX.md` (changed)
14. `docs/IMPLEMENTATION_JOURNAL.md` (changed)
15. `docs/audit/` review artifacts (changed/new)

## Cycle Type

Targeted - Phase 6 task review for T21 cost rollup and budget check.

## Notes for PROMPT_3

Focus on telemetry parsing, deterministic rollup math, budget overrun exit
codes, fixture-only CI safety, docs for live judge cost-gate approval, and T22
provider work remaining disabled without credentials/budget.
