# Implementation Journal - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-12
Status: append-only

This file records durable handoff context across agents and sessions. It is not
the source of truth for architecture or policy.

## Journal Entry Template

```markdown
### YYYY-MM-DD - TASK-ID - Short Title

- Scope: files or directories
- Why this work happened: reason or trigger
- Decisions applied: Decision Log or ADR refs, or `none`
- Evidence collected: tests, evals, review reports, or manual checks
- Follow-ups: next task, open risk, or `none`
- Notes for next agent: only the context worth carrying forward
```

## Entries

### 2026-06-11 - T01 - Standard Bootstrap

- Scope: `docs/`, `.github/workflows/ci.yml`, `pyproject.toml`,
  `requirements*.txt`, `src/eval_ground_truth_lab/`, `tests/`
- Why this work happened: Initialize the project from the provided brief using
  the AI Workflow Playbook Standard mode.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: `docs/audit/PHASE1_AUDIT.md` after validation
- Follow-ups: Execute the first uncompleted task in `docs/tasks.md` after the
  Phase 1 audit has no blockers.
- Notes for next agent: Product capability profiles are OFF; optional judge
  work starts only at T09 and remains non-authoritative.

### 2026-06-11 - T04 - Dataset Schema and Hashing

- Scope: `src/eval_ground_truth_lab/datasets/`, `tests/datasets/`,
  `requirements.txt`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Start Phase 2 product implementation with the dataset
  registry required by baseline/candidate comparison.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: `tests/datasets/test_registry.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T05 run store implementation; formal review gate still required
  before treating T04 as independently approved.
- Notes for next agent: JSONL uses one case object per line with default schema
  version `1.0`; YAML supports either a list of cases or
  `dataset_id/schema_version/cases`.

### 2026-06-11 - T05 - Run Store and Idempotent Case Results

- Scope: `src/eval_ground_truth_lab/runs/`, `tests/runs/`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add local immutable run storage required before
  baseline/candidate comparison and validator aggregation.
- Decisions applied: `D-002`
- Evidence collected: `tests/runs/test_run_store.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T06 deterministic validator engine.
- Notes for next agent: Run records are JSON files keyed by `run_id`; duplicate
  run IDs and duplicate case results are rejected; completed and interrupted
  runs are immutable.

### 2026-06-11 - T06 - Deterministic Validator Engine

- Scope: `src/eval_ground_truth_lab/validators/`, `tests/validators/`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add deterministic validation primitives required by
  regression comparison and CI gate decisions.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/validators/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T07 baseline/candidate comparison and regression policy.
- Notes for next agent: `ValidationResult` is the shared result shape; structured
  output, unsafe auto-approval, cost, and latency validators are deterministic
  and do not call models.

### 2026-06-11 - T07 - Baseline Candidate Comparison and Regression Policy

- Scope: `src/eval_ground_truth_lab/compare/`, `src/eval_ground_truth_lab/cli.py`,
  `tests/compare/`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add baseline/candidate comparison metrics and CI
  exit-code mapping required before candidate adapters and smoke gates.
- Decisions applied: `D-002`
- Evidence collected: `tests/compare/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T08 candidate adapters.
- Notes for next agent: Comparison rejects mismatched dataset hashes, computes
  threshold statuses for accuracy, invalid output rate, unsafe auto-approval
  rate, p95 latency, and cost per case, and exposes
  `comparison_exit_code(report)` for CI boundary behavior.

### 2026-06-11 - T08 - Candidate Adapters

- Scope: `src/eval_ground_truth_lab/adapters/`,
  `src/eval_ground_truth_lab/tracing.py`, `tests/adapters/`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add explicit synthetic, HTTP, and CLI candidate
  invocation boundaries before optional judge and smoke-gate work.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: `tests/adapters/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T09 optional judge, human review queue, and cost telemetry.
- Notes for next agent: HTTP adapters reject case-provided destination fields;
  CLI adapters reject case-provided command fields and execute only the configured
  argument list; HTTP/CLI adapter results include trace ID and operation name.

### 2026-06-11 - T09 - Optional Judge, Human Review Queue, and Cost Telemetry

- Scope: `src/eval_ground_truth_lab/judging/`,
  `src/eval_ground_truth_lab/review/`, `tests/judging/`,
  `docs/COST_BUDGET.md`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add the optional judge boundary, budget precheck,
  non-authoritative judge decision handling, human review queue primitive, and
  provider-agnostic cost telemetry required before reporting and taxonomy work.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/judging/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T10 reports and failure taxonomy.
- Notes for next agent: Judge execution is disabled without credentials and a
  positive budget, uses an injected provider rather than direct model SDK calls,
  reserves a positive per-call cost estimate before each call, and cannot
  override deterministic blocking validator failures.

### 2026-06-11 - T10 - Reports and Failure Taxonomy

- Scope: `src/eval_ground_truth_lab/reports/`,
  `src/eval_ground_truth_lab/review/notes.py`, `tests/reports/`,
  `tests/review/`, `.gitignore`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add canonical markdown reporting, required failure
  taxonomy labels, and append-only human review decision notes before seeded
  regression CI smoke-gate work.
- Decisions applied: `D-002`
- Evidence collected: `tests/reports/`, `tests/review/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T11 seeded regression CI smoke gate.
- Notes for next agent: Markdown reports render from `RunRecord` and
  `ComparisonReport`, top failure categories include case-level validator
  failures and threshold regression labels, and human review notes append JSONL
  entries with reviewer, timestamp, case ID, decision, and rationale. `.gitignore`
  ignores only root `/reports/` generated output so package/test report modules
  remain tracked.

### 2026-06-11 - T11 - Seeded Regression CI Smoke Gate

- Scope: `datasets/smoke/`, `src/eval_ground_truth_lab/cli.py`,
  `.github/workflows/ci.yml`, `tests/eval/`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add a seeded smoke dataset and CI-verifiable command
  that proves the gate fails on unsafe auto-approval, invalid structured output,
  excessive cost increase, and material accuracy drop.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/eval/`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`,
  `python -m pytest tests -q --tb=short`, and direct seeded smoke command
  verification that exit code is `1`.
- Follow-ups: T12 v1 evidence pack and 100-case dataset.
- Notes for next agent: `python -m eval_ground_truth_lab.cli seeded-smoke`
  writes baseline/candidate raw run artifacts plus a markdown report and returns
  `1` for the seeded regression candidate. CI asserts that expected failure code
  so the workflow remains green while proving the gate catches seeded regressions.

### 2026-06-11 - T12 - V1 Evidence Pack and 100-Case Dataset

- Scope: `datasets/v1/`, `reports/v1/`, `.gitignore`,
  `tests/eval/test_v1_evidence_pack.py`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Complete the v1 adoption proof with at least 100
  synthetic eval cases, at least 5 known seeded regressions, and an evidence
  report linking CI failure evidence for the required regression classes.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/eval/test_v1_evidence_pack.py`; full gate passed
  with `ruff check src tests`, `ruff format --check src tests`,
  `python -m pytest tests -q --tb=short`, and direct seeded smoke command
  verification that exit code is `1`.
- Follow-ups: T13 truth surface and packaging cleanup, then the Phase 5
  gdev-agent integration roadmap in `docs/tasks.md`.
- Notes for next agent: V1 manifest records 100 cases and dataset hash
  `bfffb49cdc8fb2420ff9a499d795d84eadfc1e526a08bbe0a10a154acc2a54f7`.
  `.gitignore` keeps generated root report outputs ignored while allowing
  tracked `reports/v1/` evidence artifacts.

### 2026-06-11 - Roadmap - Real gdev-agent Integration Tasks

- Scope: `docs/tasks.md`, `docs/CODEX_PROMPT.md`,
  `docs/IMPLEMENTATION_JOURNAL.md`
- Why this work happened: Convert the next-stage plan into executable tasks
  that prove Eval Lab can evaluate a real local AI workflow system, starting
  with gdev-agent.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/test_phase1_docs.py`,
  `python -m pytest tests -q --tb=short`, `ruff check src tests`, and
  `ruff format --check src tests`.
- Follow-ups: Start T13.
- Notes for next agent: T13-T24 prioritize README/evidence packaging,
  gdev-agent dataset, normalizer, adapter, validators, CLI, baseline report,
  mocked CI smoke, cost rollup, optional provider, file-backed review, and final
  static evidence pack. Dashboard, continuous eval, and extra provider work are
  intentionally later than the real gdev-agent proof.

### 2026-06-12 - T13 - Truth Surface and Packaging Cleanup

- Scope: `README.md`, `docs/README.md`, `tests/docs/test_readme_quickstart.py`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Make the project understandable from the repository
  root and provide a clear seeded-smoke quickstart plus a gdev-agent local
  integration path.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/docs/test_readme_quickstart.py`; full gate passed
  with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T14 gdev-agent eval dataset v1.
- Notes for next agent: README positions gdev-agent as the next local
  integration proof, explicitly not a production eval platform or hosted SaaS
  claim. The README links architecture, evidence index, v1 evidence report, and
  known gaps.

### 2026-06-12 - T14 - gdev-agent Eval Dataset v1

- Scope: `datasets/gdev_agent/`, `docs/GDEV_AGENT_EVAL_DATASET.md`,
  `tests/datasets/test_gdev_agent_dataset.py`, `src/eval_ground_truth_lab/cli.py`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add the first real integration dataset surface for
  gdev-agent triage behavior with stable synthetic cases, slice coverage,
  thresholds, manifest hash evidence, and dataset inspection.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/datasets/test_gdev_agent_dataset.py`; full gate
  passed with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T15 gdev-agent output normalizer.
- Notes for next agent: Dataset has 55 synthetic cases, 5 per required slice.
  Manifest hash is
  `ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb`.
  `dataset-inspect` now emits dataset ID, schema version, case count, and hash.

### 2026-06-12 - T15 - gdev-agent Output Normalizer

- Scope: `src/eval_ground_truth_lab/adapters/gdev_normalizer.py`,
  `tests/adapters/test_gdev_agent_normalizer.py`,
  `docs/GDEV_AGENT_ADAPTER.md`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add the deterministic response-mapping boundary needed
  before a live gdev-agent adapter and gdev-agent validators can inspect real
  candidate outputs.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/adapters/test_gdev_agent_normalizer.py`; full gate
  passed with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T16 Real GDevAgentHttpAdapter.
- Notes for next agent: `normalize_gdev_response` supports executed, pending,
  blocked, and error statuses; malformed output fails closed into
  `invalid_structured_output`; HTTP 4xx/5xx responses become `adapter_error`;
  cost and latency fields are preserved when available.

### 2026-06-12 - T16 - Real GDevAgentHttpAdapter

- Scope: `src/eval_ground_truth_lab/adapters/gdev_agent.py`,
  `src/eval_ground_truth_lab/adapters/gdev_normalizer.py`,
  `tests/adapters/test_gdev_agent_adapter.py`,
  `tests/adapters/test_gdev_agent_normalizer.py`,
  `docs/GDEV_AGENT_ADAPTER.md`, `README.md`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add the configured local gdev-agent HTTP adapter
  boundary needed before gdev-agent validators and CLI orchestration can run
  against the real system under test.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/adapters/test_gdev_agent_adapter.py` and
  `tests/adapters/test_gdev_agent_normalizer.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T17 gdev-agent deterministic validators.
- Notes for next agent: `GdevAgentHttpAdapter` signs canonical JSON body bytes
  for configured `/webhook`, rejects case-controlled destination/tenant/secret
  fields, and returns normalized output. Unit tests use mocked transport. The
  normalizer now supports nested gdev-agent `classification/action/pending`
  responses and maps input-guard HTTP errors to blocked guard output.

### 2026-06-12 - T17 - gdev-agent Deterministic Validators

- Scope: `src/eval_ground_truth_lab/validators/gdev_agent.py`,
  `tests/validators/test_gdev_agent_validators.py`,
  `docs/FAILURE_TAXONOMY.md`, `docs/GDEV_AGENT_ADAPTER.md`,
  `src/eval_ground_truth_lab/reports/taxonomy.py`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Replace candidate self-reported correctness with
  deterministic validators that compare expected dataset values to normalized
  gdev-agent outputs.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/validators/test_gdev_agent_validators.py`; full
  gate passed with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T18 CLI Commands for Real External Eval.
- Notes for next agent: `validate_gdev_case` returns ordered `ValidationResult`
  entries for structure, category, status, human routing, guard behavior, unsafe
  auto-approval, confidence, cost, and latency. Candidate `correct=true` is
  ignored. Failure labels are documented in `docs/FAILURE_TAXONOMY.md`.

### 2026-06-12 - T18 - CLI Commands for Real External Eval

- Scope: `src/eval_ground_truth_lab/cli.py`, `tests/test_cli.py`,
  `docs/CLI.md`, `README.md`, `tests/docs/test_readme_quickstart.py`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Make Eval Lab usable from the local CLI for
  gdev-agent eval runs, run artifact writing, report writing, dataset inspection,
  and run comparison.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/test_cli.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T19 gdev-agent baseline report.
- Notes for next agent: `run-gdev-agent` writes completed run artifacts through
  `RunStore`, applies gdev validators, and writes a markdown report. `compare`
  reads run JSON artifacts and returns `1` on blocking threshold regression.
  README command examples are backed by subcommand help checks.

### 2026-06-12 - T19 - gdev-agent Baseline Report

- Scope: `reports/gdev-agent/`, `tests/eval/test_gdev_agent_baseline_report.py`,
  `.gitignore`, `README.md`, `docs/README.md`, `docs/EVIDENCE_INDEX.md`,
  `docs/CODEX_PROMPT.md`
- Why this work happened: Add the primary local gdev-agent baseline evidence
  report from a canonical run artifact without production-quality claims.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/eval/test_gdev_agent_baseline_report.py`; full
  gate passed with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T20 CI smoke for gdev adapter without live gdev.
- Notes for next agent: `reports/gdev-agent/baseline_run.json` is a compact
  canonical `RunRecord` evidence artifact and
  `reports/gdev-agent/baseline_report.md` is the readable report. The report
  labels the data as synthetic/local deterministic and records known limits.
  T19 tests also verify baseline case IDs against the source gdev dataset.

### 2026-06-12 - T20 - CI Smoke for gdev Adapter Without Live gdev

- Scope: `tests/eval/test_gdev_agent_smoke.py`, `.github/workflows/ci.yml`,
  `docs/GDEV_AGENT_ADAPTER.md`, `README.md`, `docs/README.md`,
  `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add a CI-safe mocked gdev-agent smoke proof that
  exercises adapter logic, validators, report generation, and threshold gate
  behavior without requiring a live Docker Compose service.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/eval/test_gdev_agent_smoke.py` and
  `tests/adapters/test_gdev_agent_adapter.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T21 cost rollup and budget check.
- Notes for next agent: The mocked smoke uses the real 55-case gdev dataset and
  real `run-gdev-agent` CLI path with fake deterministic adapter output. It
  asserts a clean pass path and a seeded unsafe auto-approval regression exit
  code `1`. Live local integration remains documented separately.

### 2026-06-12 - T21 - Cost Rollup and Budget Check

- Scope: `src/eval_ground_truth_lab/cost/`, `src/eval_ground_truth_lab/cli.py`,
  `tests/cost/`, `tests/test_cli.py`, `docs/COST_BUDGET.md`, `docs/CLI.md`,
  `README.md`, `docs/README.md`, `docs/CODEX_PROMPT.md`,
  `docs/EVIDENCE_INDEX.md`
- Why this work happened: Turn provider-agnostic JSONL telemetry into
  deterministic cost rollups and enforceable budget checks for fixture CI and
  local eval runs.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/cost/test_rollup.py`,
  `tests/cost/test_budget_check.py`, and `tests/test_cli.py`; full gate passed
  with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T22 optional real judge provider.
- Notes for next agent: `cost-rollup` writes JSON with total cost/tokens,
  cost-by dimensions, latency p95, retry count, judge call count, and quality
  outcome distribution. `budget-check` exits `1` for per-run, monthly,
  cost-per-case, or judge-call-count overrun. Live judge cost gates still require
  approved policy and telemetry artifacts before enforcement.

### 2026-06-12 - T22 - Optional Real Judge Provider

- Scope: `src/eval_ground_truth_lab/judging/providers/`,
  `src/eval_ground_truth_lab/judging/__init__.py`,
  `tests/judging/test_provider_contract.py`, `docs/JUDGE_CALIBRATION.md`,
  `datasets/judge_calibration/ambiguous_cases.jsonl`,
  `reports/judge_calibration/report.md`, `.gitignore`, `README.md`,
  `docs/README.md`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Add one optional provider integration behind the
  existing injected-provider judge boundary while preserving budget prechecks and
  non-authoritative judge behavior.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/judging/test_provider_contract.py` and existing
  `tests/judging/`; full gate passed with `ruff check src tests`,
  `ruff format --check src tests`, and `python -m pytest tests -q --tb=short`.
- Follow-ups: T23 file-backed human review queue.
- Notes for next agent: `OpenAIJudgeProvider` is disabled without environment
  credentials and a positive runner budget. Tests use fake transport only.
  Provider structured output is validated before conversion to
  `JudgeProviderResult`; telemetry goes through existing `JudgeRunner`.
  Deterministic failures remain blocking through `final_case_decision`.

### 2026-06-12 - T23 - File-Backed Human Review Queue

- Scope: `src/eval_ground_truth_lab/review/store.py`,
  `src/eval_ground_truth_lab/reports/review.py`,
  `src/eval_ground_truth_lab/review/__init__.py`,
  `src/eval_ground_truth_lab/reports/__init__.py`,
  `tests/review/test_review_store.py`, `docs/HUMAN_REVIEW.md`, `README.md`,
  `docs/README.md`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why this work happened: Replace in-memory-only human review usage with
  append-only file-backed review entries and decisions without mutating original
  judge evidence.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/review/test_review_store.py`; full gate passed
  with `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: T24 static HTML report and final evidence pack.
- Notes for next agent: `FileReviewStore` writes entries and decisions to
  separate JSONL files. `unresolved_entries()` returns entries without decisions.
  `render_unresolved_review_links` creates a markdown report section for pending
  review items.

### 2026-06-12 - T24 - Static HTML Report and Final Evidence Pack

- Scope: `src/eval_ground_truth_lab/reports/html.py`,
  `src/eval_ground_truth_lab/reports/templates/eval_report.html`,
  `tests/reports/test_html_report.py`,
  `tests/docs/test_final_evidence_pack.py`,
  `reports/gdev-agent/baseline_report.html`, `docs/REPORTING.md`,
  `docs/CASE_STUDY.md`, `docs/KNOWN_LIMITS.md`, `README.md`,
  `docs/EVIDENCE_INDEX.md`, `docs/CODEX_PROMPT.md`, `docs/README.md`
- Why this work happened: Add a derivative static HTML report and final evidence
  pack while keeping markdown reports and run artifacts canonical.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/reports/test_html_report.py` and
  `tests/docs/test_final_evidence_pack.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: none in the current task roadmap.
- Notes for next agent: HTML report is derivative and embeds escaped canonical
  markdown; `reports/gdev-agent/baseline_report.md` and
  `reports/gdev-agent/baseline_run.json` remain authoritative. Final claims are
  mapped in `docs/EVIDENCE_INDEX.md`, and limits are explicit in
  `docs/KNOWN_LIMITS.md`.

### 2026-06-12 - T25 - Live gdev-agent Probe Adapter Hardening

- Scope: `src/eval_ground_truth_lab/adapters/gdev_agent.py`,
  `tests/adapters/test_gdev_agent_adapter.py`,
  `tests/validators/test_gdev_agent_validators.py`, `.gitignore`,
  `docs/tasks.md`, `docs/KNOWN_LIMITS.md`, `docs/EVIDENCE_INDEX.md`,
  `docs/CODEX_PROMPT.md`, and `docs/audit/`.
- Why this work happened: A live local probe against `gdev-agent` reached
  `/health` and `/auth/token`, but `/webhook` returned runtime 500s. One failure
  mode closed the HTTP connection before a response was completed, which exposed
  that Eval Lab's adapter normalized `HTTPError` but not transport disconnects.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/adapters/test_gdev_agent_adapter.py` and
  `tests/validators/test_gdev_agent_validators.py`; full gate passed with
  `ruff check src tests`, `ruff format --check src tests`, and
  `python -m pytest tests -q --tb=short`.
- Follow-ups: Fix upstream `gdev-agent` `/webhook` runtime blockers, then rerun
  live `run-gdev-agent` proof.
- Notes for next agent: `_post_signed_json` now maps `URLError`,
  `TimeoutError`, `HTTPException`, and `OSError` transport failures to HTTP
  `599` with `adapter_error` output. The live probe found upstream gdev-agent
  blockers in `webhook_secrets` RLS lookup before tenant context and async
  budget checking across event loops. Transient `runs/` output and
  `reports/gdev-agent/live_probe_report.md` are ignored, not canonical evidence.

### 2026-06-12 - T26 - Live gdev-agent Proof Rerun Summary

- Scope: `reports/gdev-agent/live_probe_summary.md`, `docs/KNOWN_LIMITS.md`,
  `docs/EVIDENCE_INDEX.md`, `docs/tasks.md`, `docs/CODEX_PROMPT.md`, and
  `docs/audit/`.
- Why this work happened: After the upstream `gdev-agent` runtime fix was
  pushed at commit `901292d`, the live proof needed to be rerun and documented
  without promoting a failing quality run into the canonical baseline.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `make demo` passed against local `gdev-agent`; live
  `run-gdev-agent` reached all 55 cases with zero adapter errors and exited `1`
  from deterministic validator failures.
- Follow-ups: Align gdev-agent demo classification, routing, guard behavior,
  unsafe auto-approval, and cost output with the eval dataset; then regenerate a
  canonical passing live baseline.
- Notes for next agent: The live integration path is now operational. The
  remaining gap is not adapter/runtime connectivity; it is product-quality and
  telemetry alignment between `gdev-agent` demo behavior and
  `datasets/gdev_agent/triage_v1.jsonl`.

### 2026-06-14 - T27 - Passing gdev-agent Live Baseline Evidence Refresh

- Scope: `README.md`, `docs/CASE_STUDY.md`, `docs/EVIDENCE_INDEX.md`,
  `docs/GDEV_AGENT_ADAPTER.md`, `docs/KNOWN_LIMITS.md`, `docs/README.md`,
  `docs/tasks.md`, `docs/CODEX_PROMPT.md`, `reports/gdev-agent/`,
  `tests/eval/test_gdev_agent_baseline_report.py`,
  `tests/reports/test_html_report.py`, and `docs/audit/`.
- Why this work happened: After `gdev-agent` commit `1db09d3` aligned demo-mode
  classification, routing, guard behavior, unsafe auto-approval, and
  deterministic cost telemetry with `datasets/gdev_agent/triage_v1.jsonl`, Eval
  Lab needed its canonical baseline and evidence package refreshed from the
  passing live local run.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: live `run-gdev-agent` against local `gdev-agent` produced
  `gdev-baseline-v1` with 55 case results, zero adapter errors, zero
  deterministic validator failures, deterministic `0.0000` cost per case, and
  p95 latency around 239 ms. Local gates passed with `ruff check src tests`,
  `ruff format --check src tests`, and `python -m pytest tests -q`.
- Follow-ups: none in the current roadmap.
- Notes for next agent: `reports/gdev-agent/baseline_run.json` is now the
  canonical committed full-dataset run artifact. `runs/gdev-baseline-v1.json`
  is the CLI output source, while `reports/gdev-agent/baseline_report.md` and
  `.html` are the reviewable report surfaces.

### 2026-06-14 - T29 - gdev-agent Diagnostic Challenge Set

- Scope: `datasets/gdev_agent/challenge_v1.jsonl`,
  `datasets/gdev_agent/challenge_manifest.json`,
  `datasets/gdev_agent/challenge_thresholds.json`,
  `docs/GDEV_AGENT_CHALLENGE_SET.md`,
  `reports/gdev-agent/challenge_report.md`,
  `tests/datasets/test_gdev_agent_dataset.py`, `README.md`,
  `docs/CASE_STUDY.md`, `docs/KNOWN_LIMITS.md`, `docs/EVIDENCE_INDEX.md`,
  `docs/README.md`, `reports/gdev-agent/README.md`, `docs/tasks.md`, and
  `docs/CODEX_PROMPT.md`.
- Why this work happened: The passing 55-case gdev-agent baseline was clean
  integration/conformance evidence, but portfolio credibility needed a harder
  diagnostic dataset with ambiguous cases, policy stress, guard stress,
  tenant-boundary pressure, malformed inputs, and expected failures.
- Decisions applied: deterministic validators remain authoritative; no judge,
  live provider, or runtime tier expansion was introduced.
- Evidence collected: focused dataset tests verify 100 unique synthetic cases,
  required slices, expected-failure metadata, diagnostic threshold fields,
  documentation/report links, and no real-data markers.
- Follow-ups: Promote a live challenge run only after expected-failure matching
  is surfaced as first-class CLI/report metrics.
- Notes for next agent: `reports/gdev-agent/challenge_report.md` is a committed
  scope report, not a completed live challenge run. The canonical passing
  gdev-agent quality artifact remains `reports/gdev-agent/baseline_run.json`.
