# META_ANALYSIS - Cycle 17

Date: 2026-06-12
Type: targeted

## Project State

Phase 5 gdev-agent proof path is implemented through T20. T20 CI Smoke for gdev
Adapter Without Live gdev is implemented locally. Next: T21 - Cost Rollup and
Budget Check.

Baseline: 76 pass, 0 skip.

## Open Findings

| ID | Sev | Description | Files | Status |
|----|-----|-------------|-------|--------|
| none | n/a | No open findings in `docs/CODEX_PROMPT.md`; Cycle 16 review had no P0/P1/P2 findings. | n/a | n/a |

## PROMPT_1 Scope (architecture)

- CI workflow: `.github/workflows/ci.yml` now has an explicit mocked
  gdev-agent smoke step that runs `tests/eval/test_gdev_agent_smoke.py` and
  `tests/adapters/test_gdev_agent_adapter.py`.
- Mocked eval smoke: new test file runs the real `run-gdev-agent` CLI command
  against the 55-case gdev dataset with a deterministic fake adapter, writes run
  artifacts and report, and expects exit `0`.
- Unsafe regression gate: smoke test injects an unsafe auto-approval output and
  asserts `run-gdev-agent` exits `1` and records `unsafe_auto_approval`.
- Docs separation: `docs/GDEV_AGENT_ADAPTER.md` now separates CI mocked smoke
  from live local integration and explicitly states the mocked path does not
  need Docker Compose, live gdev-agent, network access, tenant secrets, or live
  LLM calls.
- Acceptance tests: T20 coverage is in
  `tests/eval/test_gdev_agent_smoke.py`; adapter boundary tests remain in
  `tests/adapters/test_gdev_agent_adapter.py`.
- Audit continuity: Cycle 16 review artifacts archived under
  `docs/audit/archive/`.

## PROMPT_2 Scope (code/docs priority order)

1. `tests/eval/test_gdev_agent_smoke.py` (new)
2. `.github/workflows/ci.yml` (changed)
3. `docs/GDEV_AGENT_ADAPTER.md` (changed)
4. `README.md` (changed)
5. `docs/README.md` (changed)
6. `docs/CODEX_PROMPT.md` (changed)
7. `docs/EVIDENCE_INDEX.md` (changed)
8. `docs/IMPLEMENTATION_JOURNAL.md` (changed)
9. `docs/audit/` review artifacts (changed/new)

## Cycle Type

Targeted - Phase 5 task review for T20 mocked gdev CI smoke.

## Notes for PROMPT_3

Focus on CI-safe behavior, no Docker/live gdev requirement, adapter boundary
coverage, deterministic validator authority, unsafe auto-approval regression
exit code, and readiness for T21 cost rollup.
