# ARCH_REPORT - Cycle 15

Date: 2026-06-12

## Component Verdicts

| Component | Verdict | Note |
|-----------|---------|------|
| CLI command surface | PASS | Adds `run-gdev-agent` and `compare` while preserving `seeded-smoke` and `dataset-inspect`. |
| gdev run command | PASS | Loads dataset, invokes adapter, applies deterministic validators, writes run artifact/report, and exits on validator failure. |
| compare command | PASS | Reads canonical run JSON, applies threshold config, writes markdown comparison report, and returns CI-style exit code. |
| README/CLI docs | PASS | Commands are documented in root README and new `docs/CLI.md`. |
| Tests | PASS | CLI tests cover help, dataset metadata output, gdev run artifact/report writing, compare failure exit, and README command support. |
| Audit continuity | PASS | Cycle 14 review artifacts are archived before active review artifacts are overwritten for Cycle 15. |

## Contract Compliance

| Rule | Verdict | Note |
|------|---------|------|
| SQL safety | n/a | T18 adds no SQL or database calls. |
| Credentials and secrets | PASS | CLI uses configured adapter/env boundary; eval cases still cannot provide credentials. |
| CI gate | PASS | Local equivalent gate passed: ruff check, ruff format check, and pytest. |
| No self-review | PASS | Review artifacts record findings and evidence; no P1/P2 finding is self-closed because none exist. |
| Repository authority | PASS | CLI tests, docs, and evidence index point to canonical artifacts. |
| Deterministic gates own blocking decisions | PASS | `run-gdev-agent` exits non-zero from deterministic validator failures, not judge output. |
| Dataset and run identity are immutable | PASS | Run artifacts are written through `RunStore`; completed run records are immutable by existing store contract. |
| Synthetic data only in v1 | PASS | Tests use synthetic one-case fixtures only. |
| Explicit candidate adapter boundary | PASS | CLI builds the configured gdev adapter; tests inject mocked adapter and do not require live Docker. |
| Optional judge is budgeted and non-authoritative | n/a | T18 does not modify judge execution or authority. |

## ADR Compliance

| ADR | Verdict | Note |
|-----|---------|------|
| none | n/a | No ADRs exist in `docs/adr/`. |

## Architecture Findings

None.

## Right-Sizing / Runtime Checks

| Check | Verdict | Note |
|-------|---------|------|
| Solution shape still appropriate | PASS | T18 adds local CLI orchestration and filesystem artifacts, not dashboard, scheduler, provider calls, or hosted runtime. |
| Deterministic-owned areas remain deterministic | PASS | Validator results and comparison thresholds drive exit codes. |
| Runtime tier unchanged / justified | PASS | CLI uses existing adapter and run store boundaries; no new dependency or privileged runtime path added. |
| Human approval boundaries still valid | PASS | No threshold loosening, safety-regression acceptance, judge authority increase, or budget change. |
| Minimum viable control surface still proportionate | PASS | CLI wiring is required before baseline report and CI smoke tasks. |

## Doc Patches Needed

| File | Section | Change |
|------|---------|--------|
| none | n/a | No architecture/spec patch required for T18. |
