# Eval Ground Truth Lab Docs

Status: active

## Purpose

This docs folder owns the architecture, budget rules, continuity surfaces, and
validation evidence for Eval Ground Truth Lab.

## Start Here

- `docs/PROJECT_BRIEF.md` - input brief distilled into project-local context.
- `docs/ARCHITECTURE.md` - canonical architecture and mode/profile decisions.
- `docs/spec.md` - feature behavior and acceptance criteria.
- `docs/STACK_OVERVIEW.md` - three-project reliability stack map.
- `docs/EVIDENCE_INDEX.md` - durable proof retrieval index.
- `docs/KNOWN_LIMITS.md` - explicit local and production-boundary limits.
- `docs/HARNESS_COMPARISON.md` - harness metadata and trace completeness
  sidecar contract.

## Current State

- Adoption mode: Standard.
- Runtime tier: T1.
- Product capability profiles: RAG OFF, Tool-Use OFF, Agentic OFF, Planning OFF,
  Compliance OFF.
- Optional LLM judge is disabled by default and budget-gated.
- Current proof surface: seeded smoke gate, v1 synthetic evidence pack, a
  passing local gdev-agent integration proof, and a committed gdev-agent
  diagnostic challenge set, not a production eval platform or hosted SaaS
  claim.

## Key Decisions

- `docs/DECISION_LOG.md#decision-index` - mode, runtime, profile, and judge
  authority decisions.

## Contracts, Proof, and Evals

- `docs/COST_BUDGET.md` - judge/model budget boundary.
- `docs/EVIDENCE_INDEX.md` - proof retrieval index.
- `docs/HARNESS_COMPARISON.md` - harness comparison metadata contract.
- `reports/eval_cost_report.md` - starter eval cost report.
- `reports/v1/evidence_report.md` - v1 synthetic evidence report.
- `reports/gdev-agent/baseline_report.md` - gdev-agent local baseline report.
- `docs/GDEV_AGENT_CHALLENGE_SET.md` - gdev-agent hard-case diagnostic dataset.
- `reports/gdev-agent/challenge_report.md` - committed challenge-set scope
  report.

## Active Tasks

- Current roadmap status: complete through the gdev-agent diagnostic challenge
  set.

## Known Gaps

- gdev-agent dataset, normalizer, adapter, validators, CLI, and baseline report
  are implemented for the local deterministic proof path.
- Mocked CI smoke for the gdev adapter is implemented.
- Cost rollup and fixture budget-check are implemented.
- Optional real judge provider contract is implemented and remains disabled
  without credentials and budget.
- File-backed human review queue is implemented.
- Static HTML report and final evidence pack are implemented.
- The challenge set is committed as diagnostic evidence, but live challenge-run
  promotion and expected-failure summary metrics remain future work.
- Runtime Grid live-local proof exists as an optional operator-run path in the
  runtime repository; it is not a hosted eval scheduler.
- Dashboard, hosted service, continuous eval, and production platform claims are
  out of scope for the current proof.

## Authority

This README is a navigation index. Canonical artifacts, tests, evals, ADRs,
proof receipts, and report artifacts remain authoritative.
