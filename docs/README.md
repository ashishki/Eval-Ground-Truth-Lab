# Eval Ground Truth Lab Docs

Status: active

## Purpose

This docs folder owns the Phase 1 architecture, task state, implementation
contract, budget rules, continuity surfaces, and validation evidence for Eval
Ground Truth Lab.

## Start Here

- `docs/PROJECT_BRIEF.md` - input brief distilled into project-local context.
- `docs/ARCHITECTURE.md` - canonical architecture and mode/profile decisions.
- `docs/spec.md` - feature behavior and acceptance criteria.
- `docs/tasks.md` - implementation task queue and verification requirements.
- `docs/CODEX_PROMPT.md` - current Codex session state.
- `docs/IMPLEMENTATION_CONTRACT.md` - implementation rules and forbidden actions.

## Current State

- Adoption mode: Standard.
- Runtime tier: T1.
- Product capability profiles: RAG OFF, Tool-Use OFF, Agentic OFF, Planning OFF,
  Compliance OFF.
- Optional LLM judge is disabled by default and budget-gated.

## Key Decisions

- `docs/DECISION_LOG.md#decision-index` - mode, runtime, profile, and judge
  authority decisions.

## Contracts, Proof, and Evals

- `docs/IMPLEMENTATION_CONTRACT.md` - implementation authority.
- `docs/COST_BUDGET.md` - judge/model budget boundary.
- `docs/EVIDENCE_INDEX.md` - proof retrieval index.
- `docs/audit/PHASE1_AUDIT.md` - Phase 1 validation output after it is written.

## Active Tasks

- `docs/tasks.md#t01-project-skeleton` - first task in Phase 1.

## Known Gaps

- Product implementation starts after Phase 1 validation passes.
- Cost telemetry is planned for T09; Phase 1 uses manual-review budget policy.
- Seeded regression CI smoke gate is planned for T11.

## Authority

This README is a navigation index. Canonical artifacts, tests, evals, ADRs,
proof receipts, and review reports remain authoritative.

