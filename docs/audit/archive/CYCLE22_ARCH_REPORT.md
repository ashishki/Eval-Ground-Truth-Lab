# ARCH_REPORT - Cycle 22

Date: 2026-06-12

## Component Verdicts

| Component | Verdict | Note |
|-----------|---------|------|
| gdev transport adapter | PASS | Transport disconnects, URL errors, timeouts, HTTP client errors, and OS network errors normalize to HTTP `599` adapter-error outputs. |
| gdev normalizer boundary | PASS | HTTP status `599` follows existing HTTP-error normalization and becomes `adapter_error`. |
| gdev validators | PASS | Adapter errors remain deterministic blocking failures through `gdev.adapter_error`. |
| CLI failure behavior | PASS | Live probe no longer tracebacked after adapter hardening; it exits non-zero from deterministic failures. |
| live gdev-agent dependency | BLOCKED_EXTERNAL | Current upstream `gdev-agent` `/webhook` path returns runtime 500s after health/auth pass. |
| artifact hygiene | PASS | Transient live probe outputs under `runs/` and `reports/gdev-agent/live_probe_report.md` are ignored. |
| known limits | PASS | Live probe blocker is documented without claiming a passing live baseline. |
| Tests | PASS | Adapter and validator regression tests cover the new failure mode and blocking behavior. |
| Audit continuity | PASS | Cycle 21 review artifacts are archived before active review artifacts are overwritten for Cycle 22. |

## Contract Compliance

| Rule | Verdict | Note |
|------|---------|------|
| SQL safety | n/a | Eval Lab added no SQL or database calls. |
| Credentials and secrets | PASS | Runtime probe used existing synthetic local tenant IDs/secrets only; no real secrets added. |
| CI gate | PASS | Local equivalent gate passed: ruff check, ruff format check, and pytest. |
| No self-review | PASS | Review artifacts record scoped review evidence; no Eval Lab P1/P2 finding is self-closed because none exist. |
| Repository authority | PASS | Evidence index, known limits, task ledger, and journal were updated. |
| Deterministic gates own blocking decisions | PASS | Adapter errors are validator failures; no judge or candidate self-report can override them. |
| Dataset and run identity are immutable | PASS | No committed dataset or canonical baseline run was mutated. |
| Synthetic data only in v1 | PASS | Live probe used synthetic local cases and synthetic local tenant fixtures. |
| Explicit candidate adapter boundary | PASS | Network destination still comes from adapter config, not eval case input. |
| Optional judge is budgeted and non-authoritative | PASS | T25 added no judge/provider calls. |

## ADR Compliance

| ADR | Verdict | Note |
|-----|---------|------|
| none | n/a | No ADRs exist in `docs/adr/`. |

## Architecture Findings

| ID | Sev | Description | Status |
|----|-----|-------------|--------|
| EXT-GDEV-001 | External | Current `gdev-agent` local `/webhook` path returns runtime 500s after health/auth pass: first observed RLS/tenant-context issue in `webhook_secrets`, then async-loop mismatch in budget checking. | Documented in `docs/KNOWN_LIMITS.md`; fix belongs upstream in `gdev-agent`. |

## Right-Sizing / Runtime Checks

| Check | Verdict | Note |
|-------|---------|------|
| Solution shape still appropriate | PASS | T25 hardens the existing adapter instead of adding a new integration layer. |
| Deterministic-owned areas remain deterministic | PASS | Failures are represented as structured adapter outputs and validator results. |
| Runtime tier unchanged / justified | PASS | No new runtime, dependency, service, model SDK/API, or hosted path was added. |
| Human approval boundaries still valid | PASS | No threshold, judge authority, cost policy, or safety acceptance changes. |
| Minimum viable control surface still proportionate | PASS | The change is limited to network error handling and evidence docs. |

## Doc Patches Needed

| File | Section | Change |
|------|---------|--------|
| none | n/a | Required T25 docs patches are included. |
