# Implementation Journal - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11
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
