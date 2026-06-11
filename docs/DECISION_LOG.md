# Decision Log - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11

This file is a retrieval index for important decisions. It is not the source of
truth. If an entry conflicts with a canonical document, the canonical document
wins and this file must be corrected.

## Rules

- Keep entries short and link to the authoritative document or section.
- Record why a decision was made and what it replaced.
- Update this file when architecture, runtime, governance, budget, judge
  authority, or major implementation direction changes.
- Mark superseded decisions explicitly instead of deleting them.

## Decision Index

| ID | Date | Status | Decision | Why it matters | Canonical source | Supersedes |
|----|------|--------|----------|----------------|------------------|------------|
| D-001 | 2026-06-11 | Active | Use Standard adoption mode. | The project needs CI, auditability, recurring evidence, and budget controls, but v1 has synthetic data and no privileged autonomous runtime. | `docs/ARCHITECTURE.md#solution-shape` | none |
| D-002 | 2026-06-11 | Active | Use hybrid deterministic subsystem plus fixed workflow orchestration at runtime tier T1. | Deterministic validators own the core gates; fixed orchestration coordinates baseline, candidate, comparison, report, and review flow. | `docs/ARCHITECTURE.md#solution-shape` | none |
| D-003 | 2026-06-11 | Active | Keep RAG, Tool-Use, Agentic, Planning, and Compliance profiles OFF in Phase 1. | The brief does not require retrieval-backed answering, LLM-directed tools, autonomous loops, primary plan output, or compliance evidence in v1. | `docs/ARCHITECTURE.md#capability-profiles` | none |
| D-004 | 2026-06-11 | Active | Optional judge output is budgeted and non-authoritative. | A model judge can assist subjective review but cannot override deterministic validators or become blocking authority without approval and calibration evidence. | `docs/IMPLEMENTATION_CONTRACT.md#optional-judge-is-budgeted-and-non-authoritative` | none |

## Retrieval Notes

- Read this file before revisiting architecture, changing runtime tier, changing
  capability profile status, changing judge authority, or overriding a prior
  tradeoff.
- If a task has `Context-Refs`, prefer those entries over scanning this file
  top-to-bottom.

