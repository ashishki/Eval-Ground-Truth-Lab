# Evidence Index - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11

This file indexes durable proof so agents can retrieve prior evidence quickly.
It is not authoritative by itself. Every row must point to an actual artifact
that is the real evidence.

## When To Use

Maintain this file for:

- Phase 1 audit results.
- Seeded regression reports.
- Baseline and candidate comparison reports.
- Human review decisions.
- Cost telemetry rollups once T09 exists.

## Evidence Table

| Topic / Finding / Task | Artifact type | Location | Scope covered | Last verified | Canonical? |
|------------------------|---------------|----------|---------------|---------------|------------|
| Phase 1 local verification | test | `tests/test_phase1_docs.py` | Required Standard docs, placeholder removal, CI command declarations, and task verifier fields | 2026-06-11 | Yes |
| Phase 1 validation | audit | `docs/audit/PHASE1_AUDIT.md` | Standard Phase 1 artifact validation, cross-document consistency, and adoption reality gate | 2026-06-11 | Yes |

## Retrieval Rules

- Prefer rows that match the current task's `Context-Refs`, open findings, or
  seeded regression gates.
- If an evidence row points to a stale or missing artifact, fix the artifact or
  remove the row.
- Do not treat a journal note as proof when a test, eval, audit report, or CI
  output exists.
