# REVIEW_REPORT - Cycle 15

Date: 2026-06-12
Scope: T18 CLI Commands for Real External Eval

## Executive Summary

- Stop-Ship: No.
- T18 adds `run-gdev-agent` and `compare` CLI commands while preserving
  `dataset-inspect` and `seeded-smoke`.
- `run-gdev-agent` writes run artifacts and reports, applies deterministic gdev
  validators, and exits non-zero on validator failures.
- `compare` reads canonical run artifacts, writes a comparison report, and exits
  `1` on blocking regression.
- README and new `docs/CLI.md` document the command path.
- Baseline is now 68 passing tests, 0 skipped.
- No P0, P1, or P2 findings were identified in the scoped files.

## P0 Issues

None.

## P1 Issues

None.

## P2 Issues

| ID | Description | Files | Status |
|----|-------------|-------|--------|
| none | No P2 findings. | n/a | n/a |

## Carry-Forward Status

| ID | Sev | Description | Status | Change |
|----|-----|-------------|--------|--------|
| none | n/a | Cycle 14 review had no P0/P1/P2 findings. | n/a | n/a |

## Stop-Ship Decision

No - scoped implementation satisfies T18 acceptance criteria, local verification
passed, and no blocking findings were identified.

## README-First Index Status

| Changed boundary | README path | Status | Notes |
|------------------|-------------|--------|-------|
| CLI commands | `docs/CLI.md` | current | New CLI doc covers help, dataset-inspect, run-gdev-agent, and compare. |
| root quickstart | `README.md` | current | README gdev quickstart uses implemented `run-gdev-agent` command with run ID. |
| audit artifacts | `docs/README.md` | current | Existing docs index links audit/evidence surfaces; cycle-specific archive does not need a separate index. |

## Cost Budget Status

| Scope | Status | Notes |
|-------|--------|-------|
| AI/model budget | within budget | T18 added no model calls, judge execution, retries, fan-out, tool calls, or recurring AI usage. |
| Telemetry rollup | unchanged | T18 records run cost fields from normalized outputs but does not add telemetry rollup or CI cost thresholds. |

## Code Review Checklist Result

| Check | Result | Note |
|-------|--------|------|
| SEC-1 SQL parameterization | n/a | No SQL introduced. |
| SEC-2 secret handling | PASS | CLI uses configured adapter boundary; test fixtures use mocked adapter and no live credentials. |
| SEC-3 auth boundary | PASS | CLI does not allow dataset cases to control adapter credentials or destination. |
| SEC-4 credentials from environment/config only | PASS | gdev adapter config remains the credential boundary. |
| QUAL-1 error handling | PASS | Validator failures map to non-zero `run-gdev-agent`; comparison blocking failures map to exit `1`. |
| QUAL-2 test coverage | PASS | T18 AC-1 through AC-5 are covered by CLI and README tests. |
| GOV-1 solution-shape drift | PASS | T18 adds CLI orchestration only, not dashboard, scheduler, or provider integrations. |
| GOV-2 deterministic ownership | PASS | Exit codes come from deterministic validators and comparison thresholds. |
| GOV-3 runtime-tier drift | PASS | No new service runtime, package, model SDK/API, or privileged execution path added. |
| GOV-4 human approval boundaries | PASS | No threshold-policy, budget-policy, judge-authority, or seeded-regression gate changes. |
| GOV-5 continuity discipline | PASS | Journal, evidence index, audit index, and handoff updated. |
| GOV-6 filesystem reality | PASS | Claimed files exist; tests and commands were run. |
| GOV-7 runtime verification | PASS | Targeted and full local gates plus direct CLI help/dataset-inspect commands were executed. |
| GOV-8 bounded correction | PASS | Import-order correction and report-link refinement after review; no test weakening. |
| GOV-9 claim evidence | PASS | Tests and evidence rows back completion claims. |
| GOV-10 README-first index | PASS | README links CLI docs and examples are mechanically checked. |
| GOV-11 cost budget | PASS | No AI/model budget change. |
| OBS-1 external call instrumentation | PASS | `run-gdev-agent` stores adapter latency/status-derived result evidence in run artifacts. |
| OBS-2 AI-path metrics | n/a | T18 adds no AI path. |
| OBS-3 health endpoint integrity | n/a | No health endpoint exists or changed. |

## Validation Evidence

- `.venv/bin/python -m pytest tests/test_cli.py tests/docs/test_readme_quickstart.py -q --tb=short`
  - pass, 8 tests
- `.venv/bin/ruff check src tests` - pass
- `.venv/bin/ruff format --check src tests` - pass
- `.venv/bin/python -m pytest tests -q --tb=short` - pass, 68 tests
- `.venv/bin/python -m eval_ground_truth_lab.cli --help` - pass, lists
  `seeded-smoke`, `dataset-inspect`, `run-gdev-agent`, and `compare`
- `.venv/bin/python -m eval_ground_truth_lab.cli dataset-inspect --dataset datasets/gdev_agent/triage_v1.jsonl`
  - pass, reports 55 cases and canonical dataset hash
- Scoped runtime/security scan - no shell/subprocess/eval/exec path introduced;
  CLI uses configured adapter boundary
- Requested wording scan - no disallowed audience-positioning wording found in
  scoped repository docs/source/tests/reports

## Next

Proceed to T19 gdev-agent Baseline Report.
