# Eval Ground Truth Lab Docs

Status: active

## Purpose

This docs folder owns the architecture, task state, implementation contract,
budget rules, continuity surfaces, and validation evidence for Eval Ground Truth
Lab.

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
- Current proof surface: seeded smoke gate plus v1 synthetic evidence pack.
- Next proof surface: local gdev-agent integration proof, not a production eval
  platform or hosted SaaS claim.

## Key Decisions

- `docs/DECISION_LOG.md#decision-index` - mode, runtime, profile, and judge
  authority decisions.

## Contracts, Proof, and Evals

- `docs/IMPLEMENTATION_CONTRACT.md` - implementation authority.
- `docs/COST_BUDGET.md` - judge/model budget boundary.
- `docs/EVIDENCE_INDEX.md` - proof retrieval index.
- `reports/v1/evidence_report.md` - v1 synthetic evidence report.
- `reports/gdev-agent/baseline_report.md` - gdev-agent local baseline report.
- `docs/audit/AUDIT_INDEX.md` - audit and deep-review index.

## Active Tasks

- `docs/tasks.md#t21-cost-rollup-and-budget-check` - current Phase 6
  entry point.

## Known Gaps

- gdev-agent dataset, normalizer, adapter, validators, CLI, and baseline report
  are implemented for the local deterministic proof path.
- Mocked CI smoke for the gdev adapter is implemented.
- Cost rollup and CI budget enforcement are planned next.
- Cost telemetry exists, but rollup and CI budget enforcement are planned later.
- File-backed human review and static HTML reporting are planned later.
- Dashboard, hosted service, continuous eval, and production platform claims are
  out of scope for the current proof.

## Authority

This README is a navigation index. Canonical artifacts, tests, evals, ADRs,
proof receipts, and review reports remain authoritative.
