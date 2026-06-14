# Evidence Index - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-14

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
| T12 deep review | review | `docs/audit/archive/CYCLE9_REVIEW_REPORT.md` | META, ARCH, CODE, evidence-pack, and consolidated review gate for T12 | 2026-06-11 | Yes |
| T13 truth surface and packaging | test | `tests/docs/test_readme_quickstart.py` | Root README required sections, core evidence links, gdev-agent local proof positioning, and production/SaaS overclaim guard | 2026-06-12 | Yes |
| T13 deep review | review | `docs/audit/archive/CYCLE10_REVIEW_REPORT.md` | META, ARCH, CODE, docs, and consolidated review gate for T13 | 2026-06-12 | Yes |
| T14 gdev-agent dataset | test | `tests/datasets/test_gdev_agent_dataset.py` | 55-case synthetic gdev-agent triage dataset, required slice coverage, manifest hash consistency, dataset-inspect output, and no real data markers | 2026-06-12 | Yes |
| T14 gdev-agent dataset manifest | eval evidence | `datasets/gdev_agent/manifest.json` | gdev-agent triage v1 case count, dataset hash, slice list, and threshold config pointer | 2026-06-12 | Yes |
| T14 deep review | review | `docs/audit/archive/CYCLE11_REVIEW_REPORT.md` | META, ARCH, CODE, dataset, and consolidated review gate for T14 | 2026-06-12 | Yes |
| T15 gdev-agent normalizer | test | `tests/adapters/test_gdev_agent_normalizer.py` | Executed, pending, blocked, error, malformed structured output, HTTP error, cost, and latency normalization | 2026-06-12 | Yes |
| T15 gdev-agent adapter contract | docs | `docs/GDEV_AGENT_ADAPTER.md` | Canonical normalized output shape, fail-closed behavior, adapter error mapping, and live adapter boundary | 2026-06-12 | Yes |
| T15 deep review | review | `docs/audit/archive/CYCLE12_REVIEW_REPORT.md` | META, ARCH, CODE, normalizer, and consolidated review gate for T15 | 2026-06-12 | Yes |
| T16 gdev-agent HTTP adapter | test | `tests/adapters/test_gdev_agent_adapter.py` | Configured `/webhook` URL, forbidden case overrides, configured-secret HMAC signature, mocked transport, and normalized adapter output | 2026-06-12 | Yes |
| T16 gdev-agent adapter docs | docs | `docs/GDEV_AGENT_ADAPTER.md` | Config, signing, payload shape, local demo-mode commands, and CLI limitation | 2026-06-12 | Yes |
| T16 deep review | review | `docs/audit/archive/CYCLE13_REVIEW_REPORT.md` | META, ARCH, CODE, adapter boundary, and consolidated review gate for T16 | 2026-06-12 | Yes |
| T17 gdev-agent validators | test | `tests/validators/test_gdev_agent_validators.py` | Candidate self-report non-authority, category/status/routing/guard failures, unsafe auto-approval, confidence/cost/latency thresholds, and result shape | 2026-06-12 | Yes |
| T17 failure taxonomy | docs | `docs/FAILURE_TAXONOMY.md` | gdev failure labels and deterministic validator authority | 2026-06-12 | Yes |
| T17 deep review | review | `docs/audit/archive/CYCLE14_REVIEW_REPORT.md` | META, ARCH, CODE, validator, taxonomy, and consolidated review gate for T17 | 2026-06-12 | Yes |
| T18 CLI commands | test | `tests/test_cli.py` | CLI help, dataset-inspect metadata, run-gdev-agent artifact/report writing, and compare blocking exit code | 2026-06-12 | Yes |
| T18 CLI docs | docs | `docs/CLI.md` | Help, dataset-inspect, run-gdev-agent, and compare command examples | 2026-06-12 | Yes |
| T18 deep review | review | `docs/audit/archive/CYCLE15_REVIEW_REPORT.md` | META, ARCH, CODE, CLI command, and consolidated review gate for T18 | 2026-06-12 | Yes |
| T19 gdev-agent baseline report | test | `tests/eval/test_gdev_agent_baseline_report.py` | Report-to-run-artifact consistency, required report sections, synthetic/local deterministic scope labels, and evidence-index links | 2026-06-12 | Yes |
| T19 gdev-agent baseline run | eval evidence | `reports/gdev-agent/baseline_run.json` | Canonical gdev-agent baseline run artifact with candidate version, dataset hash, metrics, 55 case outputs, and case-level validator evidence | 2026-06-14 | Yes |
| T19 gdev-agent baseline report artifact | report | `reports/gdev-agent/baseline_report.md` | Dataset hash, environment, candidate version, metrics, thresholds, failure taxonomy, zero case-level failures, known limits, and reproduction command | 2026-06-14 | Yes |
| T19 deep review | review | `docs/audit/archive/CYCLE16_REVIEW_REPORT.md` | META, ARCH, CODE, baseline report, run artifact, and consolidated review gate for T19 | 2026-06-12 | Yes |
| T20 mocked gdev CI smoke | test | `tests/eval/test_gdev_agent_smoke.py` | 55-case mocked gdev eval pass path, unsafe auto-approval regression exit `1`, and docs/workflow separation from live integration | 2026-06-12 | Yes |
| T20 mocked gdev workflow step | ci | `.github/workflows/ci.yml` | Explicit mocked gdev-agent smoke step running smoke and adapter tests without Docker Compose | 2026-06-12 | Yes |
| T20 gdev adapter docs | docs | `docs/GDEV_AGENT_ADAPTER.md` | CI mocked smoke versus live local integration boundary | 2026-06-12 | Yes |
| T20 deep review | review | `docs/audit/archive/CYCLE17_REVIEW_REPORT.md` | META, ARCH, CODE, mocked smoke, CI, docs, and consolidated review gate for T20 | 2026-06-12 | Yes |
| T21 cost rollup | test | `tests/cost/test_rollup.py` | JSONL telemetry rollup for total cost/tokens, cost by model/workflow/case, latency p95, retry count, judge call count, and quality outcomes | 2026-06-12 | Yes |
| T21 budget check | test | `tests/cost/test_budget_check.py` | Per-run, monthly, cost-per-case, and judge-call-count overrun detection plus fixture telemetry CLI path | 2026-06-12 | Yes |
| T21 cost CLI docs | docs | `docs/CLI.md` | `cost-rollup` and `budget-check` command examples and live judge cost-gate boundary | 2026-06-12 | Yes |
| T21 cost budget docs | docs | `docs/COST_BUDGET.md` | Telemetry rollup status, budget-check status, fixture CI use, and live judge approval boundary | 2026-06-12 | Yes |
| T21 deep review | review | `docs/audit/archive/CYCLE18_REVIEW_REPORT.md` | META, ARCH, CODE, cost rollup, budget policy, CLI, docs, and consolidated review gate for T21 | 2026-06-12 | Yes |
| T22 optional OpenAI judge provider | test | `tests/judging/test_provider_contract.py` | Disabled-without-key/budget behavior, structured output schema, budget precheck, telemetry, human review routing, and deterministic failure authority | 2026-06-12 | Yes |
| T22 judge calibration docs | docs | `docs/JUDGE_CALIBRATION.md` | Optional provider boundary, fake-transport tests, synthetic calibration fixtures, and non-authoritative judge rules | 2026-06-12 | Yes |
| T22 judge calibration dataset | eval evidence | `datasets/judge_calibration/ambiguous_cases.jsonl` | Synthetic ambiguous cases for judge calibration documentation | 2026-06-12 | Yes |
| T22 judge calibration report | report | `reports/judge_calibration/report.md` | Provider contract evidence and no-live-call boundary | 2026-06-12 | Yes |
| T22 deep review | review | `docs/audit/archive/CYCLE19_REVIEW_REPORT.md` | META, ARCH, CODE, provider contract, calibration artifacts, and consolidated review gate for T22 | 2026-06-12 | Yes |
| T23 file-backed human review | test | `tests/review/test_review_store.py` | Append-only review entries, separate decisions without evidence mutation, and unresolved review report links | 2026-06-12 | Yes |
| T23 human review docs | docs | `docs/HUMAN_REVIEW.md` | Review entry JSONL shape, decision JSONL shape, append-only rule, and unresolved review links | 2026-06-12 | Yes |
| T23 deep review | review | `docs/audit/archive/CYCLE20_REVIEW_REPORT.md` | META, ARCH, CODE, file-backed review store, report links, docs, and consolidated review gate for T23 | 2026-06-12 | Yes |
| T24 static HTML report | test | `tests/reports/test_html_report.py` | HTML report generated from canonical markdown body and links canonical markdown/run artifacts | 2026-06-12 | Yes |
| T24 final evidence pack | test | `tests/docs/test_final_evidence_pack.py` | 5-minute reviewer path, case study required answers, evidence index final claims, and overclaim guard | 2026-06-12 | Yes |
| T24 reporting docs | docs | `docs/REPORTING.md` | Markdown/run JSON canonical source of truth and HTML derivative boundary | 2026-06-12 | Yes |
| T24 case study | docs | `docs/CASE_STUDY.md` | Final evidence answers for eval target, dataset versioning, comparison, validators, gdev-agent, cost/latency, judge, and limits | 2026-06-12 | Yes |
| T24 known limits | docs | `docs/KNOWN_LIMITS.md` | Explicit local/synthetic, no-dashboard, no-hosted-service, no-production-platform boundaries | 2026-06-12 | Yes |
| T24 HTML report artifact | report | `reports/gdev-agent/baseline_report.html` | Derivative readable HTML linked to canonical markdown and run JSON | 2026-06-12 | Yes |
| T25 transport disconnect hardening | test | `tests/adapters/test_gdev_agent_adapter.py` | `RemoteDisconnected` from live gdev-agent transport normalizes to deterministic `adapter_error` instead of crashing CLI | 2026-06-12 | Yes |
| T25 adapter-error blocking | test | `tests/validators/test_gdev_agent_validators.py` | Normalized adapter errors remain blocking deterministic eval failures | 2026-06-12 | Yes |
| T25 live gdev-agent pre-fix probe | docs | `docs/KNOWN_LIMITS.md` | Pre-fix live local probe found upstream `webhook_secrets` RLS and async-loop runtime failures plus the Eval Lab transport-disconnect gap | 2026-06-12 | Yes |
| T26 live gdev-agent proof rerun | report | `reports/gdev-agent/live_probe_summary.md` | Post-fix live run reaches all 55 cases with zero adapter errors and records remaining deterministic quality/telemetry failures | 2026-06-12 | Yes |
| T27 gdev-agent passing live baseline | report | `reports/gdev-agent/baseline_report.md`, `reports/gdev-agent/baseline_run.json` | After gdev-agent demo policy and cost telemetry alignment, live local run covers all 55 cases with zero adapter errors and zero deterministic validator failures | 2026-06-14 | Yes |
| T27 evidence pack refresh | docs | `README.md`, `docs/CASE_STUDY.md`, `docs/KNOWN_LIMITS.md`, `docs/EVIDENCE_INDEX.md` | Evidence package now points to the passing live local baseline while preserving production/platform limits | 2026-06-14 | Yes |
| T27 deep review | review | `docs/audit/REVIEW_REPORT.md` | META, ARCH, CODE, evidence-pack, audit continuity, and consolidated review gate for T27 | 2026-06-14 | Yes |
| Final claim: dataset versioning | test/report | `tests/datasets/test_gdev_agent_dataset.py`, `datasets/gdev_agent/manifest.json`, `docs/CASE_STUDY.md` | Dataset hash and case count evidence | 2026-06-12 | Yes |
| Final claim: baseline candidate comparison | test | `tests/compare/`, `tests/test_cli.py`, `docs/CASE_STUDY.md` | Comparison threshold and CLI compare behavior | 2026-06-12 | Yes |
| Final claim: unsafe auto-approval | test/report | `tests/eval/test_seeded_smoke_gate.py`, `tests/validators/test_gdev_agent_validators.py`, `tests/eval/test_gdev_agent_smoke.py` | Seeded and gdev unsafe regression gates | 2026-06-12 | Yes |
| Final claim: gdev-agent eval | test/report | `tests/eval/test_gdev_agent_smoke.py`, `reports/gdev-agent/baseline_report.md`, `reports/gdev-agent/baseline_run.json` | Local gdev-agent adapter/eval proof path with full 55-case passing live local baseline | 2026-06-14 | Yes |
| Final claim: cost and latency | test/docs | `tests/cost/test_rollup.py`, `tests/cost/test_budget_check.py`, `docs/COST_BUDGET.md` | Cost/latency rollup and budget-check evidence | 2026-06-12 | Yes |
| Final claim: non-authoritative judge | test/docs | `tests/judging/test_provider_contract.py`, `tests/judging/test_authority.py`, `docs/JUDGE_CALIBRATION.md` | Judge disabled, budgeted, and cannot override deterministic failures | 2026-06-12 | Yes |
| Final claim: known limits | docs | `docs/KNOWN_LIMITS.md`, `README.md` | Explicit non-production, synthetic/local, no-dashboard, operator-run live-local, and deterministic demo-cost limits | 2026-06-14 | Yes |
| T24 deep review | review | `docs/audit/REVIEW_REPORT.md` | META, ARCH, CODE, HTML report, final evidence docs, evidence index, and consolidated review gate for T24 | 2026-06-12 | Yes |
| T25 deep review | review | `docs/audit/REVIEW_REPORT.md` | META, ARCH, CODE, live-probe transport hardening, known limits, and consolidated review gate for T25 | 2026-06-12 | Yes |
| T26 deep review | review | `docs/audit/REVIEW_REPORT.md` | META, ARCH, CODE, live proof rerun summary, known limits, and consolidated review gate for T26 | 2026-06-12 | Yes |

## Retrieval Rules

- Prefer rows that match the current task's `Context-Refs`, open findings, or
  seeded regression gates.
- If an evidence row points to a stale or missing artifact, fix the artifact or
  remove the row.
- Do not treat a journal note as proof when a test, eval, audit report, or CI
  output exists.
