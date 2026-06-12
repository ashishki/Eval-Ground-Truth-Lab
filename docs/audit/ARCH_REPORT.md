# ARCH_REPORT - Cycle 16

Date: 2026-06-12

## Component Verdicts

| Component | Verdict | Note |
|-----------|---------|------|
| gdev baseline run artifact | PASS | `baseline_run.json` uses the canonical `RunRecord` shape and parses through `RunRecord.from_mapping`. |
| gdev baseline report | PASS | Report includes required evidence sections and values from the run artifact. |
| Source dataset alignment | PASS | Baseline cases are checked against `datasets/gdev_agent/triage_v1.jsonl`; non-failing category outputs match expected categories. |
| README/evidence index | PASS | Root README and `docs/EVIDENCE_INDEX.md` link the baseline report and run artifact. |
| Evidence tracking | PASS | `.gitignore` allows tracked `reports/gdev-agent/**` evidence artifacts. |
| Tests | PASS | T19 tests cover report consistency, required sections, scope/overclaim labels, evidence links, and dataset-case alignment. |
| Audit continuity | PASS | Cycle 15 review artifacts are archived before active review artifacts are overwritten for Cycle 16. |

## Contract Compliance

| Rule | Verdict | Note |
|------|---------|------|
| SQL safety | n/a | T19 adds no SQL or database calls. |
| Credentials and secrets | PASS | Report commands use local demo config examples only; no secrets are committed. |
| CI gate | PASS | Local equivalent gate passed: ruff check, ruff format check, and pytest. |
| No self-review | PASS | Review artifacts record scoped review evidence; no P1/P2 finding is self-closed because none exist. |
| Repository authority | PASS | Evidence rows point to concrete report, run artifact, and tests. |
| Deterministic gates own blocking decisions | PASS | Report labels validator-derived failure taxonomy and does not introduce judge authority. |
| Dataset and run identity are immutable | PASS | Baseline report records the canonical dataset hash and the committed run artifact records run ID/version fields. |
| Synthetic data only in v1 | PASS | The report and README label the evidence as synthetic/local deterministic. |
| Explicit candidate adapter boundary | PASS | Reproduction command uses configured `--base-url`; no case-controlled destination is introduced. |
| Optional judge is budgeted and non-authoritative | n/a | T19 does not modify judge execution, providers, or budgets. |

## ADR Compliance

| ADR | Verdict | Note |
|-----|---------|------|
| none | n/a | No ADRs exist in `docs/adr/`. |

## Architecture Findings

None.

## Right-Sizing / Runtime Checks

| Check | Verdict | Note |
|-------|---------|------|
| Solution shape still appropriate | PASS | T19 adds filesystem evidence artifacts and tests, not dashboard, scheduler, hosted runtime, or provider calls. |
| Deterministic-owned areas remain deterministic | PASS | Report claims are backed by committed JSON and deterministic tests. |
| Runtime tier unchanged / justified | PASS | No new runtime or dependency was added. |
| Human approval boundaries still valid | PASS | No threshold loosening, safety-regression acceptance, judge-authority increase, or budget change. |
| Minimum viable control surface still proportionate | PASS | Baseline evidence is required before mocked CI smoke and cost rollup tasks. |

## Doc Patches Needed

| File | Section | Change |
|------|---------|--------|
| none | n/a | No architecture/spec patch required for T19. |
