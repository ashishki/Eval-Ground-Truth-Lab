# ARCH_REPORT - Cycle 17

Date: 2026-06-12

## Component Verdicts

| Component | Verdict | Note |
|-----------|---------|------|
| mocked gdev smoke | PASS | Runs `run-gdev-agent` against the real 55-case dataset with deterministic fake adapter output and no live service. |
| unsafe regression smoke | PASS | Injected unsafe auto-approval returns exit `1` and records validator failure evidence. |
| adapter boundary coverage | PASS | CI step includes existing mocked-transport adapter tests. |
| CI workflow | PASS | Workflow has a named mocked gdev-agent smoke step and does not use Docker Compose. |
| docs separation | PASS | Adapter docs separate CI mocked smoke from live local integration. |
| Tests | PASS | T20 tests cover pass path, unsafe regression, and docs/workflow separation. |
| Audit continuity | PASS | Cycle 16 review artifacts are archived before active review artifacts are overwritten for Cycle 17. |

## Contract Compliance

| Rule | Verdict | Note |
|------|---------|------|
| SQL safety | n/a | T20 adds no SQL or database calls. |
| Credentials and secrets | PASS | Mocked smoke uses no real secrets; live local examples retain placeholder demo config only. |
| CI gate | PASS | Local equivalent gate passed: ruff check, ruff format check, and pytest. |
| No self-review | PASS | Review artifacts record scoped review evidence; no P1/P2 finding is self-closed because none exist. |
| Repository authority | PASS | CI workflow, tests, and docs are concrete repository artifacts. |
| Deterministic gates own blocking decisions | PASS | Unsafe smoke fails from deterministic gdev validators, not judge output. |
| Dataset and run identity are immutable | PASS | Smoke writes new temp run IDs and does not mutate committed run artifacts. |
| Synthetic data only in v1 | PASS | Tests use synthetic committed dataset and generated fake outputs. |
| Explicit candidate adapter boundary | PASS | Fake adapter is injected only by tests; live adapter boundary remains configured URL only. |
| Optional judge is budgeted and non-authoritative | n/a | T20 does not modify judge execution, providers, or budgets. |

## ADR Compliance

| ADR | Verdict | Note |
|-----|---------|------|
| none | n/a | No ADRs exist in `docs/adr/`. |

## Architecture Findings

None.

## Right-Sizing / Runtime Checks

| Check | Verdict | Note |
|-------|---------|------|
| Solution shape still appropriate | PASS | T20 adds tests, workflow step, and docs only; no dashboard, scheduler, hosted runtime, or provider calls. |
| Deterministic-owned areas remain deterministic | PASS | Smoke outputs are deterministic and validator-driven. |
| Runtime tier unchanged / justified | PASS | No new runtime, dependency, service, or network requirement was added. |
| Human approval boundaries still valid | PASS | No threshold loosening, safety-regression acceptance, judge-authority increase, or budget change. |
| Minimum viable control surface still proportionate | PASS | Mocked CI smoke is required before cost rollup and final evidence tasks. |

## Doc Patches Needed

| File | Section | Change |
|------|---------|--------|
| none | n/a | No architecture/spec patch required for T20. |
