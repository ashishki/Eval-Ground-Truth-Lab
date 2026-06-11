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
