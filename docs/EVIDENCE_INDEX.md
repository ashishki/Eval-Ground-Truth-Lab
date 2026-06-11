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
| T04 dataset registry | test | `tests/datasets/test_registry.py` | JSONL/YAML dataset loading, required field validation, structured validation errors, and stable dataset hashing | 2026-06-11 | Yes |
| T04 deep review | review | `docs/audit/archive/CYCLE1_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T04 | 2026-06-11 | Yes |
| T05 run store | test | `tests/runs/test_run_store.py` | Local JSON run persistence, completed/interrupted immutability, duplicate run ID rejection, and duplicate case-result rejection | 2026-06-11 | Yes |
| T05 deep review | review | `docs/audit/archive/CYCLE2_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T05 | 2026-06-11 | Yes |
| T06 deterministic validators | test | `tests/validators/` | Structured output validation, unsafe auto-approval validation, and cost/latency threshold delta validation | 2026-06-11 | Yes |
| T06 deep review | review | `docs/audit/archive/CYCLE3_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T06 | 2026-06-11 | Yes |
| T07 comparison policy | test | `tests/compare/` | Dataset hash mismatch rejection, comparison metric output, threshold status, and CI exit-code mapping | 2026-06-11 | Yes |
| T07 deep review | review | `docs/audit/archive/CYCLE4_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T07 | 2026-06-11 | Yes |
| T08 candidate adapters | test | `tests/adapters/` | Synthetic deterministic adapter, HTTP destination-boundary rejection, CLI command-boundary execution, process result capture, and adapter trace stamping | 2026-06-11 | Yes |
| T08 deep review | review | `docs/audit/archive/CYCLE5_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T08 | 2026-06-11 | Yes |
| T09 optional judge and telemetry | test | `tests/judging/` | Judge disabled config, budget precheck, deterministic validator authority, telemetry fields, and positive cost reservation validation | 2026-06-11 | Yes |
| T09 deep review | review | `docs/audit/archive/CYCLE6_REVIEW_REPORT.md` | META, ARCH, CODE, cost-budget, and consolidated review gate for T09 | 2026-06-11 | Yes |
| T10 reports and failure taxonomy | test | `tests/reports/`, `tests/review/` | Markdown report sections and raw links, required failure taxonomy labels, and append-only human review decision notes | 2026-06-11 | Yes |
| T10 deep review | review | `docs/audit/archive/CYCLE7_REVIEW_REPORT.md` | META, ARCH, CODE, and consolidated review gate for T10 | 2026-06-11 | Yes |
| T11 seeded smoke gate | test | `tests/eval/` | Seeded smoke dataset coverage, unsafe regression exit code 1, and report links to dataset hash, run artifacts, threshold config, and failure taxonomy evidence | 2026-06-11 | Yes |
| T11 deep review | review | `docs/audit/archive/CYCLE8_REVIEW_REPORT.md` | META, ARCH, CODE, CI, and consolidated review gate for T11 | 2026-06-11 | Yes |
| T12 v1 evidence pack | test | `tests/eval/test_v1_evidence_pack.py` | V1 manifest 100-case/hash evidence, seeded regression manifest with 5 expected failing gates, and v1 evidence report CI-failure links | 2026-06-11 | Yes |
| T12 v1 dataset manifest | eval evidence | `datasets/v1/manifest.json` | 100-case synthetic v1 dataset manifest with canonical dataset hash | 2026-06-11 | Yes |
| T12 v1 evidence report | report | `reports/v1/evidence_report.md` | Adoption proof links for unsafe regression, invalid structured output, excessive cost increase, and material accuracy drop CI evidence | 2026-06-11 | Yes |
| T12 deep review | review | `docs/audit/REVIEW_REPORT.md` | META, ARCH, CODE, evidence-pack, and consolidated review gate for T12 | 2026-06-11 | Yes |

## Retrieval Rules

- Prefer rows that match the current task's `Context-Refs`, open findings, or
  seeded regression gates.
- If an evidence row points to a stale or missing artifact, fix the artifact or
  remove the row.
- Do not treat a journal note as proof when a test, eval, audit report, or CI
  output exists.
