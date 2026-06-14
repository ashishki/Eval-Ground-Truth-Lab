# Tasks - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-14
Mode: Standard

## Task Rules

- Every task has explicit dependencies.
- Every acceptance criterion names a concrete test or verification command.
- `Context-Refs` are required when the task changes architecture, runtime,
  judge authority, budget policy, seeded regression gates, or failure taxonomy.
- Product capability profiles are OFF in Phase 1. Do not add RAG, Tool-Use,
  Agentic, Planning, or Compliance profile work without an ADR.

## Implementation Status

Current status: complete through T27.

| Range | Status | Evidence |
|-------|--------|----------|
| T01-T12 | complete | Phase 1 audit, seeded smoke gate, and v1 evidence pack in `docs/EVIDENCE_INDEX.md`. |
| T13-T18 | complete | README/truth surface, gdev dataset, normalizer, adapter, validators, and CLI evidence in `docs/EVIDENCE_INDEX.md`. |
| T19-T24 | complete | gdev baseline report, mocked CI smoke, cost rollup, optional judge provider contract, file-backed review, HTML report, and final evidence pack in `docs/EVIDENCE_INDEX.md`. |
| T25 | complete | Live-probe adapter hardening for transport disconnects in `tests/adapters/test_gdev_agent_adapter.py` and `docs/EVIDENCE_INDEX.md`. |
| T26 | complete | Live gdev-agent proof rerun summary in `reports/gdev-agent/live_probe_summary.md`. |
| T27 | complete | Passing live local gdev-agent baseline and refreshed evidence pack in `reports/gdev-agent/baseline_report.md`, `reports/gdev-agent/baseline_run.json`, and `docs/EVIDENCE_INDEX.md`. |

Next task: none in the current roadmap.

## T01: Project Skeleton

Owner: codex
Phase: 1
Type: none
Depends-On: none

Objective: |
  Create the initial Python package, dependency files, docs directories, and
  bootstrap tests that verify the Phase 1 artifact surface exists.

Acceptance-Criteria:
  - id: AC-1
    description: "The package `eval_ground_truth_lab` imports and exposes version `0.1.0`."
    test: "tests/test_bootstrap.py::test_package_imports"
  - id: AC-2
    description: "The Standard Phase 1 artifacts listed in the docs gate exist in the repository."
    test: "tests/test_phase1_docs.py::test_required_phase1_artifacts_exist"
  - id: AC-3
    description: "The repository contains no unresolved double-brace template placeholders in Phase 1 docs, CI, or project metadata."
    test: "tests/test_phase1_docs.py::test_no_unresolved_template_placeholders"

Files:
  - pyproject.toml
  - requirements.txt
  - requirements-dev.txt
  - src/eval_ground_truth_lab/__init__.py
  - tests/test_bootstrap.py
  - tests/test_phase1_docs.py
  - docs/

Context-Refs:
  - docs/PROJECT_BRIEF.md
  - docs/DECISION_LOG.md#decision-index

## T02: CI Setup

Owner: codex
Phase: 1
Type: none
Depends-On: T01

Objective: |
  Add a GitHub Actions workflow that installs the project and runs lint,
  formatting, and tests on pull requests and pushes.

Acceptance-Criteria:
  - id: AC-1
    description: "CI declares Python 3.12, ruff lint, ruff format check, and pytest commands."
    test: "tests/test_phase1_docs.py::test_ci_workflow_declares_required_steps"
  - id: AC-2
    description: "The same verification commands used by CI pass locally."
    verify: "ruff check src tests && ruff format --check src tests && python -m pytest tests -q --tb=short"

Files:
  - .github/workflows/ci.yml
  - requirements-dev.txt
  - pyproject.toml

Context-Refs:
  - docs/IMPLEMENTATION_CONTRACT.md#ci-gate

## T03: Phase 1 Documentation Gate Tests

Owner: codex
Phase: 1
Type: none
Depends-On: T02

Objective: |
  Keep the Phase 1 planning package mechanically verifiable by checking required
  artifacts, placeholder removal, CI command declarations, and task acceptance
  criterion verification fields.

Acceptance-Criteria:
  - id: AC-1
    description: "Every task acceptance criterion in `docs/tasks.md` has a `test:` or `verify:` field."
    test: "tests/test_phase1_docs.py::test_tasks_acceptance_criteria_have_verification_fields"
  - id: AC-2
    description: "The full bootstrap verification command passes."
    verify: "ruff check src tests && ruff format --check src tests && python -m pytest tests -q --tb=short"

Files:
  - tests/test_phase1_docs.py
  - docs/tasks.md

Context-Refs:
  - docs/IMPLEMENTATION_CONTRACT.md#mandatory-pre-task-protocol

## T04: Dataset Schema and Hashing

Owner: codex
Phase: 2
Type: none
Depends-On: T03

Objective: |
  Implement dataset loading for JSONL and YAML eval cases with schema validation,
  stable dataset hashing, and structured validation errors.

Acceptance-Criteria:
  - id: AC-1
    description: "A valid JSONL dataset returns schema version, case count, and SHA-256 dataset hash."
    test: "tests/datasets/test_registry.py::test_valid_jsonl_dataset_metadata"
  - id: AC-2
    description: "A case missing a required field raises a validation error containing the case ID and field name."
    test: "tests/datasets/test_registry.py::test_missing_required_field_names_case_and_field"
  - id: AC-3
    description: "Changing case input or expected output changes the dataset hash."
    test: "tests/datasets/test_registry.py::test_case_content_changes_dataset_hash"

Files:
  - src/eval_ground_truth_lab/datasets/
  - tests/datasets/test_registry.py

Context-Refs:
  - docs/spec.md#feature-area-dataset-registry

## T05: Run Store and Idempotent Case Results

Owner: codex
Phase: 2
Type: none
Depends-On: T04

Objective: |
  Implement local run storage for baseline and candidate runs with immutable
  completed run records and duplicate case-result protection.

Acceptance-Criteria:
  - id: AC-1
    description: "A run record persists run ID, run type, dataset hash, candidate version, status, cost fields, and latency fields."
    test: "tests/runs/test_run_store.py::test_run_record_persists_required_metadata"
  - id: AC-2
    description: "Attempting to mutate a completed run raises a domain error."
    test: "tests/runs/test_run_store.py::test_completed_run_is_immutable"
  - id: AC-3
    description: "Adding the same case result twice to one run raises a duplicate-result error."
    test: "tests/runs/test_run_store.py::test_duplicate_case_result_rejected"

Files:
  - src/eval_ground_truth_lab/runs/
  - tests/runs/test_run_store.py

Context-Refs:
  - docs/ARCHITECTURE.md#runtime-and-isolation-model
  - docs/spec.md#feature-area-run-orchestration-and-storage

## T06: Deterministic Validator Engine

Owner: codex
Phase: 2
Type: none
Depends-On: T04

Objective: |
  Implement deterministic validators for structured output, unsafe
  auto-approval, confidence, evidence requirements, cost, and latency.

Acceptance-Criteria:
  - id: AC-1
    description: "Invalid JSON, missing required fields, unknown enum values, and forbidden fields fail with validator IDs."
    test: "tests/validators/test_structured_output.py::test_structured_output_failures_include_validator_id"
  - id: AC-2
    description: "Unsafe auto-approval without required evidence fails with category `unsafe_auto_approval`."
    test: "tests/validators/test_safety.py::test_unsafe_auto_approval_without_evidence_fails"
  - id: AC-3
    description: "Cost and latency validators report baseline delta and threshold status."
    test: "tests/validators/test_regression_metrics.py::test_cost_latency_threshold_deltas"

Files:
  - src/eval_ground_truth_lab/validators/
  - tests/validators/

Context-Refs:
  - docs/spec.md#feature-area-deterministic-validators
  - docs/IMPLEMENTATION_CONTRACT.md#project-specific-rules

## T07: Baseline Candidate Comparison and Regression Policy

Owner: codex
Phase: 2
Type: none
Depends-On: T05 T06

Objective: |
  Compare baseline and candidate runs for the same dataset hash, calculate
  regression deltas, and produce blocking threshold decisions.

Acceptance-Criteria:
  - id: AC-1
    description: "Comparison rejects baseline and candidate runs with different dataset hashes."
    test: "tests/compare/test_comparison.py::test_rejects_mismatched_dataset_hashes"
  - id: AC-2
    description: "Comparison output includes accuracy delta, invalid output rate, unsafe auto-approval rate, p95 latency, cost per case, and threshold status."
    test: "tests/compare/test_comparison.py::test_comparison_outputs_required_metrics"
  - id: AC-3
    description: "A blocking threshold failure maps to process exit code 1 through the CLI boundary."
    test: "tests/compare/test_ci_gate.py::test_blocking_threshold_maps_to_exit_code_one"

Files:
  - src/eval_ground_truth_lab/compare/
  - src/eval_ground_truth_lab/cli.py
  - tests/compare/

Context-Refs:
  - docs/spec.md#feature-area-baseline-comparison-and-regression-gates
  - docs/DECISION_LOG.md#decision-index

## T08: Candidate Adapters

Owner: codex
Phase: 2
Type: none
Depends-On: T04 T05

Objective: |
  Implement explicit candidate adapters for a deterministic synthetic demo and
  configured gdev-agent HTTP or CLI invocation.

Acceptance-Criteria:
  - id: AC-1
    description: "The synthetic demo adapter returns deterministic fixture outputs for the same case input."
    test: "tests/adapters/test_synthetic_adapter.py::test_synthetic_adapter_is_deterministic"
  - id: AC-2
    description: "The HTTP adapter calls only the configured base URL and rejects case-provided network destinations."
    test: "tests/adapters/test_http_adapter.py::test_http_adapter_rejects_case_defined_destinations"
  - id: AC-3
    description: "The CLI adapter executes only the configured command template and records stdout, stderr, exit code, and latency."
    test: "tests/adapters/test_cli_adapter.py::test_cli_adapter_records_process_result"

Files:
  - src/eval_ground_truth_lab/adapters/
  - tests/adapters/

Context-Refs:
  - docs/ARCHITECTURE.md#security-boundaries
  - docs/IMPLEMENTATION_CONTRACT.md#control-surface-and-runtime-boundaries

## T09: Optional Judge, Human Review Queue, and Cost Telemetry

Owner: codex
Phase: 3
Type: cost:telemetry
Depends-On: T06 T07

Objective: |
  Add optional budget-capped judge calls, non-authoritative judge scoring,
  human review queue entries, and provider-agnostic cost telemetry.

Acceptance-Criteria:
  - id: AC-1
    description: "Judge mode is disabled when provider credentials or budget are absent."
    test: "tests/judging/test_judge_config.py::test_judge_disabled_without_credentials_or_budget"
  - id: AC-2
    description: "Judge calls stop before exceeding the configured per-run budget."
    test: "tests/judging/test_budget.py::test_judge_stops_before_budget_overrun"
  - id: AC-3
    description: "A deterministic blocking validator failure cannot be converted to pass by a judge score."
    test: "tests/judging/test_authority.py::test_judge_cannot_override_blocking_validator"
  - id: AC-4
    description: "Each judge call emits telemetry with project, workflow, role, model, environment, tokens, cost, latency, retry count, and quality outcome."
    test: "tests/judging/test_cost_telemetry.py::test_judge_call_emits_required_telemetry_fields"

Files:
  - src/eval_ground_truth_lab/judging/
  - src/eval_ground_truth_lab/review/
  - docs/COST_BUDGET.md
  - tests/judging/

Context-Refs:
  - docs/COST_BUDGET.md
  - docs/ARCHITECTURE.md#inference--model-strategy
  - docs/IMPLEMENTATION_CONTRACT.md#cost-budget-rules

Cost-Budget:
  scope: workflow
  max_cost_usd: 2.00
  max_model_calls: 300
  max_tool_calls: n/a
  max_retries: 1
  approval_required_when: "model escalation, fan-out increase, retry expansion, or budget overrun"

## T10: Reports and Failure Taxonomy

Owner: codex
Phase: 3
Type: none
Depends-On: T07

Objective: |
  Generate markdown reports from canonical run and comparison data, initialize
  the failure taxonomy, and record human review decisions as append-only notes.

Acceptance-Criteria:
  - id: AC-1
    description: "Markdown reports include run metadata, threshold summary, top failure categories, case-level failure table, and raw artifact links."
    test: "tests/reports/test_markdown_report.py::test_markdown_report_contains_required_sections"
  - id: AC-2
    description: "Failure taxonomy includes unsafe auto-approval, invalid structured output, missing evidence, low confidence, accuracy regression, cost regression, and latency regression."
    test: "tests/reports/test_failure_taxonomy.py::test_required_taxonomy_labels_present"
  - id: AC-3
    description: "Human review decisions append reviewer, timestamp, case ID, decision, and rationale."
    test: "tests/review/test_review_notes.py::test_review_decision_note_contains_required_fields"

Files:
  - src/eval_ground_truth_lab/reports/
  - src/eval_ground_truth_lab/review/
  - tests/reports/
  - tests/review/

Context-Refs:
  - docs/spec.md#feature-area-reporting-and-failure-taxonomy
  - docs/EVIDENCE_INDEX.md

## T11: Seeded Regression CI Smoke Gate

Owner: codex
Phase: 4
Type: none
Depends-On: T08 T10

Objective: |
  Add a small seeded regression dataset and CI smoke command that fails on unsafe
  regression, invalid structured output, excessive cost increase, and material
  accuracy drop.

Acceptance-Criteria:
  - id: AC-1
    description: "The smoke dataset contains at least one case for each blocking regression class: unsafe auto-approval, invalid structured output, excessive cost increase, and material accuracy drop."
    test: "tests/eval/test_seeded_smoke_dataset.py::test_seeded_smoke_dataset_covers_blocking_regressions"
  - id: AC-2
    description: "The seeded unsafe regression candidate causes the smoke eval command to exit with code 1."
    test: "tests/eval/test_seeded_smoke_gate.py::test_seeded_unsafe_regression_fails_ci_gate"
  - id: AC-3
    description: "The generated regression report links to dataset hash, baseline run, candidate run, threshold config, and failure taxonomy evidence."
    test: "tests/eval/test_seeded_smoke_report.py::test_seeded_report_links_required_evidence"

Files:
  - datasets/smoke/
  - src/eval_ground_truth_lab/cli.py
  - tests/eval/
  - .github/workflows/ci.yml

Context-Refs:
  - docs/PROJECT_BRIEF.md#v1-success
  - docs/EVIDENCE_INDEX.md

## T12: V1 Evidence Pack and 100-Case Dataset

Owner: codex
Phase: 4
Type: none
Depends-On: T11

Objective: |
  Expand the eval corpus and evidence package to satisfy the v1 adoption proof:
  at least 100 eval cases, at least 5 known seeded regressions, and reports that
  show the configured CI gates catch the required regression classes.

Acceptance-Criteria:
  - id: AC-1
    description: "The v1 dataset manifest references at least 100 eval cases and records the dataset hash."
    test: "tests/eval/test_v1_evidence_pack.py::test_v1_manifest_has_at_least_100_cases"
  - id: AC-2
    description: "The seeded regression manifest contains at least 5 known regressions with expected failing gate IDs."
    test: "tests/eval/test_v1_evidence_pack.py::test_seeded_regression_manifest_has_at_least_5_regressions"
  - id: AC-3
    description: "The v1 evidence report links CI failure evidence for unsafe regression, invalid structured output, excessive cost increase, and material accuracy drop."
    test: "tests/eval/test_v1_evidence_pack.py::test_v1_report_links_required_ci_failures"

Files:
  - datasets/v1/
  - reports/v1/
  - docs/EVIDENCE_INDEX.md
  - tests/eval/test_v1_evidence_pack.py

Context-Refs:
  - docs/PROJECT_BRIEF.md#v1-success
  - docs/spec.md#feature-area-ci-integration
  - docs/EVIDENCE_INDEX.md

## Next Stage: Real gdev-agent Integration

Goal:
  Prove that Eval Ground Truth Lab can evaluate a real local AI workflow system,
  not only synthetic fixtures. The first real proof target is
  `~/Documents/dev/ai-stack/projects/gdev-agent`, run locally in deterministic
  demo mode.

Reviewer path:
  1. Start gdev-agent locally:
     `LLM_MODE=demo docker compose up --build -d && make demo`
  2. Run Eval Lab against gdev-agent:
     `python -m eval_ground_truth_lab.cli run-gdev-agent --dataset datasets/gdev_agent/triage_v1.jsonl --base-url http://localhost:8000 --report reports/gdev-agent/baseline_report.md`
  3. Inspect `reports/gdev-agent/baseline_report.md` for dataset hash, case
     count, candidate version, classification accuracy, risk-routing recall,
     unsafe auto-approval rate, invalid structured output rate, guard block rate,
     human escalation recall, cost per case, latency p95, failure taxonomy, and
     case-level failures.

Ordering rule:
  Prioritize real gdev-agent integration before HTML, dashboard, scheduled eval,
  continuous eval, Kubernetes, or additional judge providers.

## T13: Truth Surface and Packaging Cleanup

Owner: codex
Phase: 5
Type: docs
Depends-On: T12

Objective: |
  Add a root-level explanation and quickstart path so a reviewer can understand
  the project and run the existing seeded smoke proof in 5-10 minutes, while
  clearly separating current synthetic evidence from the upcoming local
  gdev-agent integration proof.

Acceptance-Criteria:
  - id: AC-1
    description: "Root README explains what Eval Lab is, why eval-first matters, what works today, seeded smoke quickstart, gdev-agent quickstart path, architecture, known gaps, and roadmap."
    test: "tests/docs/test_readme_quickstart.py::test_root_readme_covers_required_sections"
  - id: AC-2
    description: "README links architecture, evidence index, v1 evidence report, and known gaps."
    test: "tests/docs/test_readme_quickstart.py::test_root_readme_links_core_evidence"
  - id: AC-3
    description: "Docs state that the gdev-agent path is a local integration proof, not a production eval platform or hosted SaaS claim."
    test: "tests/docs/test_readme_quickstart.py::test_readme_avoids_production_overclaim"

Files:
  - README.md
  - docs/README.md
  - docs/EVIDENCE_INDEX.md
  - docs/PROJECT_BRIEF.md
  - docs/ARCHITECTURE.md
  - reports/v1/evidence_report.md
  - tests/docs/test_readme_quickstart.py

Context-Refs:
  - docs/ARCHITECTURE.md
  - docs/EVIDENCE_INDEX.md
  - reports/v1/evidence_report.md

## T14: gdev-agent Eval Dataset v1

Owner: codex
Phase: 5
Type: none
Depends-On: T13

Objective: |
  Add the first real integration dataset for gdev-agent triage behavior with
  stable synthetic cases, slice coverage, thresholds, and a manifest containing
  the canonical dataset hash.

Acceptance-Criteria:
  - id: AC-1
    description: "The gdev-agent dataset contains at least 50 synthetic cases with stable unique IDs."
    test: "tests/datasets/test_gdev_agent_dataset.py::test_gdev_agent_dataset_has_50_unique_synthetic_cases"
  - id: AC-2
    description: "Every case has input, expected, and metadata with required gdev-agent triage fields."
    test: "tests/datasets/test_gdev_agent_dataset.py::test_gdev_agent_dataset_case_shape"
  - id: AC-3
    description: "Dataset covers billing_refund, account_access, bug_report, moderation_report, legal_gdpr, low_confidence, prompt_injection, unsafe_url, secret_leak_attempt, duplicate_webhook, and cross_tenant_boundary slices."
    test: "tests/datasets/test_gdev_agent_dataset.py::test_gdev_agent_dataset_slice_coverage"
  - id: AC-4
    description: "Manifest records case count and dataset hash matching dataset-inspect output."
    test: "tests/datasets/test_gdev_agent_dataset.py::test_gdev_agent_manifest_hash_matches_dataset"
  - id: AC-5
    description: "No cases contain secrets, real user data, or non-synthetic metadata."
    test: "tests/datasets/test_gdev_agent_dataset.py::test_gdev_agent_dataset_contains_no_real_data"

Files:
  - datasets/gdev_agent/triage_v1.jsonl
  - datasets/gdev_agent/manifest.json
  - datasets/gdev_agent/thresholds.json
  - docs/GDEV_AGENT_EVAL_DATASET.md
  - tests/datasets/test_gdev_agent_dataset.py
  - src/eval_ground_truth_lab/cli.py

Context-Refs:
  - docs/PROJECT_BRIEF.md#v1-success
  - docs/ARCHITECTURE.md#component-map
  - docs/EVIDENCE_INDEX.md

## T15: gdev-agent Output Normalizer

Owner: codex
Phase: 5
Type: none
Depends-On: T14

Objective: |
  Normalize gdev-agent HTTP responses into a canonical eval output before
  validators or reports inspect them.

Acceptance-Criteria:
  - id: AC-1
    description: "Normalizer supports executed, pending, blocked, and error paths."
    test: "tests/adapters/test_gdev_agent_normalizer.py::test_normalizer_supports_core_paths"
  - id: AC-2
    description: "Missing required fields fail closed into invalid_structured_output."
    test: "tests/adapters/test_gdev_agent_normalizer.py::test_missing_fields_fail_closed"
  - id: AC-3
    description: "HTTP errors become normalized eval failures rather than uncaught crashes."
    test: "tests/adapters/test_gdev_agent_normalizer.py::test_http_error_response_normalizes_to_eval_failure"
  - id: AC-4
    description: "Latency and cost fields are preserved when available."
    test: "tests/adapters/test_gdev_agent_normalizer.py::test_latency_and_cost_are_preserved"

Files:
  - src/eval_ground_truth_lab/adapters/gdev_normalizer.py
  - tests/adapters/test_gdev_agent_normalizer.py
  - docs/GDEV_AGENT_ADAPTER.md

Context-Refs:
  - docs/IMPLEMENTATION_CONTRACT.md#deterministic-gates-own-blocking-decisions
  - docs/ARCHITECTURE.md#component-map

## T16: Real GDevAgentHttpAdapter

Owner: codex
Phase: 5
Type: none
Depends-On: T08 T15

Objective: |
  Add a configured HTTP adapter that can call a locally running gdev-agent
  instance in `LLM_MODE=demo` without allowing eval cases to control network
  destinations, secrets, or commands.

Acceptance-Criteria:
  - id: AC-1
    description: "Adapter calls only the configured gdev-agent base URL and `/webhook` path."
    test: "tests/adapters/test_gdev_agent_adapter.py::test_adapter_uses_configured_base_url_only"
  - id: AC-2
    description: "Case input cannot override base_url, host, endpoint, webhook_secret, tenant secret, auth token, or command."
    test: "tests/adapters/test_gdev_agent_adapter.py::test_case_cannot_override_network_or_secret_boundary"
  - id: AC-3
    description: "Webhook signature is generated from adapter config, not case input."
    test: "tests/adapters/test_gdev_agent_adapter.py::test_webhook_signature_uses_configured_secret"
  - id: AC-4
    description: "Unit tests use mocked transport and do not require live gdev-agent."
    test: "tests/adapters/test_gdev_agent_adapter.py::test_adapter_uses_mocked_transport"
  - id: AC-5
    description: "Integration doc explains how to run live local gdev-agent in demo mode."
    verify: "rg -n \"LLM_MODE=demo|docker compose|run-gdev-agent|localhost:8000\" docs/GDEV_AGENT_ADAPTER.md README.md"

Files:
  - src/eval_ground_truth_lab/adapters/gdev_agent.py
  - src/eval_ground_truth_lab/adapters/gdev_normalizer.py
  - tests/adapters/test_gdev_agent_adapter.py
  - docs/GDEV_AGENT_ADAPTER.md
  - README.md

Context-Refs:
  - docs/IMPLEMENTATION_CONTRACT.md#explicit-candidate-adapter-boundary
  - docs/ARCHITECTURE.md#security-boundaries

## T17: gdev-agent Deterministic Validators

Owner: codex
Phase: 5
Type: none
Depends-On: T15

Objective: |
  Replace synthetic self-reported correctness with deterministic gdev-agent
  validators that derive pass/fail from expected values and normalized actual
  outputs.

Acceptance-Criteria:
  - id: AC-1
    description: "Candidate output cannot mark itself correct; correctness is derived from expected vs normalized actual."
    test: "tests/validators/test_gdev_agent_validators.py::test_candidate_cannot_self_report_correctness"
  - id: AC-2
    description: "Expected category, expected status, requires_human, and guard behavior mismatches produce blocking validator failures."
    test: "tests/validators/test_gdev_agent_validators.py::test_routing_and_guard_mismatches_block"
  - id: AC-3
    description: "Unsafe auto-approval is blocking."
    test: "tests/validators/test_gdev_agent_validators.py::test_unsafe_auto_approval_blocks"
  - id: AC-4
    description: "Confidence, cost, and latency validators produce deterministic threshold failures."
    test: "tests/validators/test_gdev_agent_validators.py::test_confidence_cost_latency_thresholds"
  - id: AC-5
    description: "Each ValidationResult includes case_id, validator_id, passed, category, message, and evidence."
    test: "tests/validators/test_gdev_agent_validators.py::test_gdev_validator_result_shape"

Files:
  - src/eval_ground_truth_lab/validators/gdev_agent.py
  - tests/validators/test_gdev_agent_validators.py
  - docs/GDEV_AGENT_ADAPTER.md
  - docs/FAILURE_TAXONOMY.md

Context-Refs:
  - docs/spec.md#feature-area-deterministic-validators
  - docs/IMPLEMENTATION_CONTRACT.md#deterministic-gates-own-blocking-decisions

## T18: CLI Commands for Real External Eval

Owner: codex
Phase: 5
Type: none
Depends-On: T14 T16 T17

Objective: |
  Make Eval Lab usable as a local CLI tool for dataset inspection, running
  gdev-agent evals, writing run artifacts, generating reports, and comparing
  baseline/candidate runs.

Acceptance-Criteria:
  - id: AC-1
    description: "CLI exposes help for dataset-inspect, run-gdev-agent, compare, and existing seeded-smoke commands."
    test: "tests/test_cli.py::test_cli_help_includes_real_eval_commands"
  - id: AC-2
    description: "dataset-inspect prints dataset ID, schema version, case count, and dataset hash."
    test: "tests/test_cli.py::test_dataset_inspect_outputs_dataset_metadata"
  - id: AC-3
    description: "run-gdev-agent exits 0 on passing eval, writes run artifacts, and writes a report."
    test: "tests/test_cli.py::test_run_gdev_agent_writes_artifacts_and_report"
  - id: AC-4
    description: "compare exits 1 on blocking regression and writes a comparison report."
    test: "tests/test_cli.py::test_compare_command_returns_one_on_blocking_regression"
  - id: AC-5
    description: "README command examples match implemented CLI commands."
    test: "tests/docs/test_readme_quickstart.py::test_readme_cli_examples_are_supported"

Files:
  - src/eval_ground_truth_lab/cli.py
  - tests/test_cli.py
  - docs/CLI.md
  - README.md

Context-Refs:
  - docs/ARCHITECTURE.md#runtime-contract
  - docs/EVIDENCE_INDEX.md

## T19: gdev-agent Baseline Report

Owner: codex
Phase: 5
Type: none
Depends-On: T18

Objective: |
  Generate the primary local gdev-agent baseline evidence report from canonical
  run artifacts without claiming production quality.

Acceptance-Criteria:
  - id: AC-1
    description: "Baseline report is generated from canonical run artifacts."
    test: "tests/eval/test_gdev_agent_baseline_report.py::test_baseline_report_generated_from_run_artifact"
  - id: AC-2
    description: "Report includes reproduction command, dataset hash, environment, candidate version, metrics, threshold summary, failure taxonomy, case-level failures, and known limits."
    test: "tests/eval/test_gdev_agent_baseline_report.py::test_baseline_report_contains_required_sections"
  - id: AC-3
    description: "Report labels data as synthetic/local deterministic and avoids production quality claims."
    test: "tests/eval/test_gdev_agent_baseline_report.py::test_baseline_report_labels_scope_and_limits"
  - id: AC-4
    description: "Evidence index links to the gdev-agent baseline report."
    test: "tests/eval/test_gdev_agent_baseline_report.py::test_evidence_index_links_baseline_report"

Files:
  - reports/gdev-agent/baseline_report.md
  - reports/gdev-agent/baseline_run.json
  - reports/gdev-agent/README.md
  - docs/EVIDENCE_INDEX.md
  - README.md
  - tests/eval/test_gdev_agent_baseline_report.py

Context-Refs:
  - docs/EVIDENCE_INDEX.md
  - docs/spec.md#feature-area-reporting-and-failure-taxonomy

## T20: CI Smoke for gdev Adapter Without Live gdev

Owner: codex
Phase: 5
Type: none
Depends-On: T16 T17 T18

Objective: |
  Add a CI-safe mocked gdev-agent smoke eval that checks adapter logic,
  validators, report generation, and threshold gate behavior without requiring a
  live Docker Compose gdev-agent service.

Acceptance-Criteria:
  - id: AC-1
    description: "CI runs mocked gdev eval smoke without Docker Compose or live gdev-agent."
    test: "tests/eval/test_gdev_agent_smoke.py::test_mocked_gdev_eval_smoke_passes_in_ci"
  - id: AC-2
    description: "Mocked unsafe auto-approval regression exits 1."
    test: "tests/eval/test_gdev_agent_smoke.py::test_mocked_unsafe_regression_exits_one"
  - id: AC-3
    description: "Docs clearly separate CI mocked smoke from live local gdev-agent integration."
    test: "tests/eval/test_gdev_agent_smoke.py::test_docs_separate_ci_smoke_from_live_integration"

Files:
  - tests/eval/test_gdev_agent_smoke.py
  - tests/adapters/test_gdev_agent_adapter.py
  - .github/workflows/ci.yml
  - datasets/gdev_agent/triage_v1.jsonl
  - reports/gdev-agent/
  - docs/GDEV_AGENT_ADAPTER.md

Context-Refs:
  - docs/spec.md#feature-area-ci-integration
  - docs/IMPLEMENTATION_CONTRACT.md#ci-gate

## T21: Cost Rollup and Budget Check

Owner: codex
Phase: 6
Type: cost:telemetry
Depends-On: T09 T18

Objective: |
  Turn provider-agnostic telemetry JSONL into cost rollups and enforceable
  budget checks for CI fixtures and local eval runs.

Acceptance-Criteria:
  - id: AC-1
    description: "Cost rollup reads JSONL telemetry and outputs total cost, total tokens, cost by model, cost by workflow, cost by case, latency p95, retry count, and quality outcome distribution."
    test: "tests/cost/test_rollup.py::test_cost_rollup_reads_jsonl_telemetry"
  - id: AC-2
    description: "Budget check exits 1 on per-run, monthly, cost-per-case, or judge-call-count overrun."
    test: "tests/cost/test_budget_check.py::test_budget_check_exits_one_on_overrun"
  - id: AC-3
    description: "CI can run budget check against fixture telemetry without real model calls."
    test: "tests/cost/test_budget_check.py::test_budget_check_uses_fixture_telemetry"
  - id: AC-4
    description: "Docs state live judge cost gates require telemetry rollup."
    verify: "rg -n \"cost-rollup|budget-check|telemetry rollup|live judge\" docs/COST_BUDGET.md docs/CLI.md"

Files:
  - src/eval_ground_truth_lab/cost/rollup.py
  - src/eval_ground_truth_lab/cost/policy.py
  - tests/cost/test_rollup.py
  - tests/cost/test_budget_check.py
  - docs/COST_BUDGET.md
  - docs/CLI.md
  - src/eval_ground_truth_lab/cli.py

Context-Refs:
  - docs/COST_BUDGET.md
  - docs/IMPLEMENTATION_CONTRACT.md#cost-budget-rules

Cost-Budget:
  scope: workflow
  max_cost_usd: 0
  max_model_calls: 0
  max_tool_calls: n/a
  max_retries: 0
  approval_required_when: "adding live model calls, changing budget thresholds, or enabling CI cost gates on non-fixture telemetry"

## T22: Optional Real Judge Provider

Owner: codex
Phase: 6
Type: cost:model
Depends-On: T09 T21

Objective: |
  Add one real optional judge provider behind the existing injected-provider
  boundary while preserving non-authoritative judge behavior and budget
  prechecks.

Acceptance-Criteria:
  - id: AC-1
    description: "Provider is disabled without API key and positive budget."
    test: "tests/judging/test_provider_contract.py::test_provider_disabled_without_api_key_or_budget"
  - id: AC-2
    description: "Provider uses structured output and validates provider result shape."
    test: "tests/judging/test_provider_contract.py::test_provider_uses_structured_output_contract"
  - id: AC-3
    description: "Budget precheck happens before provider call."
    test: "tests/judging/test_provider_contract.py::test_budget_precheck_happens_before_provider_call"
  - id: AC-4
    description: "Telemetry records tokens, cost, latency, retry count, model, and quality outcome."
    test: "tests/judging/test_provider_contract.py::test_provider_records_telemetry"
  - id: AC-5
    description: "Judge result creates human review item for ambiguous cases, and deterministic failures remain blocking."
    test: "tests/judging/test_provider_contract.py::test_judge_routes_ambiguous_cases_without_overriding_deterministic_failure"

Files:
  - src/eval_ground_truth_lab/judging/providers/
  - tests/judging/test_provider_contract.py
  - docs/JUDGE_CALIBRATION.md
  - datasets/judge_calibration/ambiguous_cases.jsonl
  - reports/judge_calibration/report.md

Context-Refs:
  - docs/COST_BUDGET.md
  - docs/ARCHITECTURE.md#inference--model-strategy
  - docs/IMPLEMENTATION_CONTRACT.md#optional-judge-is-budgeted-and-non-authoritative

Cost-Budget:
  scope: task
  max_cost_usd: 0
  max_model_calls: 0
  max_tool_calls: n/a
  max_retries: 0
  approval_required_when: "running live provider calls, adding provider credentials, model escalation, retry expansion, or budget overrun"

## T23: File-Backed Human Review Queue

Owner: codex
Phase: 6
Type: none
Depends-On: T09 T10

Objective: |
  Replace in-memory-only human review queue usage with append-only file-backed
  review entries and auditable decisions, without mutating original judge
  evidence.

Acceptance-Criteria:
  - id: AC-1
    description: "Review entries append only and include review_id, case_id, candidate_version, rubric_version, judge_explanation, reviewer_status, and created_at."
    test: "tests/review/test_review_store.py::test_review_entries_are_append_only"
  - id: AC-2
    description: "Review decisions append reviewer, decision, rationale, and reviewed_at without mutating original review entry."
    test: "tests/review/test_review_store.py::test_review_decisions_do_not_mutate_original_evidence"
  - id: AC-3
    description: "Report can link unresolved review items."
    test: "tests/review/test_review_store.py::test_report_links_unresolved_review_items"

Files:
  - src/eval_ground_truth_lab/review/store.py
  - tests/review/test_review_store.py
  - docs/HUMAN_REVIEW.md
  - src/eval_ground_truth_lab/reports/

Context-Refs:
  - docs/spec.md#feature-area-optional-llm-judge-and-human-review
  - docs/IMPLEMENTATION_CONTRACT.md#repository-authority

## T24: Static HTML Report and Final Evidence Pack

Owner: codex
Phase: 6
Type: none
Depends-On: T19 T20 T21 T23

Objective: |
  Add a derivative static HTML report and final case-study evidence pack while
  keeping markdown/run artifacts as the canonical source of truth.

Acceptance-Criteria:
  - id: AC-1
    description: "HTML report is generated from the same canonical report data as markdown and has no separate metrics logic."
    test: "tests/reports/test_html_report.py::test_html_report_uses_markdown_report_data"
  - id: AC-2
    description: "HTML report includes clear local/synthetic evidence labels and links canonical markdown/run artifacts."
    test: "tests/reports/test_html_report.py::test_html_report_links_canonical_artifacts"
  - id: AC-3
    description: "README gives a 5-minute reviewer path and links seeded smoke, gdev-agent eval, known limits, and evidence index."
    test: "tests/docs/test_final_evidence_pack.py::test_readme_has_5_minute_reviewer_path"
  - id: AC-4
    description: "Case study explains what Eval Lab evaluates, dataset versioning, baseline/candidate comparison, deterministic validators, unsafe auto-approval, gdev-agent eval, synthetic vs real integration, cost/latency handling, non-authoritative judge, and known limits."
    test: "tests/docs/test_final_evidence_pack.py::test_case_study_answers_required_questions"
  - id: AC-5
    description: "Evidence index maps every final claim to an artifact, test, or report."
    test: "tests/docs/test_final_evidence_pack.py::test_evidence_index_maps_final_claims"
  - id: AC-6
    description: "Docs avoid production SaaS/platform overclaim."
    test: "tests/docs/test_final_evidence_pack.py::test_docs_avoid_production_overclaim"

Files:
  - src/eval_ground_truth_lab/reports/html.py
  - src/eval_ground_truth_lab/reports/templates/eval_report.html
  - tests/reports/test_html_report.py
  - tests/docs/test_final_evidence_pack.py
  - reports/gdev-agent/baseline_report.html
  - docs/REPORTING.md
  - docs/CASE_STUDY.md
  - docs/KNOWN_LIMITS.md
  - docs/EVIDENCE_INDEX.md
  - README.md

Context-Refs:
  - docs/EVIDENCE_INDEX.md
  - reports/v1/evidence_report.md
  - docs/ARCHITECTURE.md

## T25: Live gdev-agent Probe Adapter Hardening

Owner: codex
Phase: 7
Type: none
Depends-On: T16 T18 T20

Objective: |
  Harden the real gdev-agent adapter after a live local probe revealed that
  transport-level disconnects can occur when the external system returns a 500
  before completing an HTTP response.

Acceptance-Criteria:
  - id: AC-1
    description: "A network disconnect from the configured gdev-agent URL normalizes to an adapter_error output instead of crashing the CLI."
    test: "tests/adapters/test_gdev_agent_adapter.py::test_network_disconnect_normalizes_to_adapter_error"
  - id: AC-2
    description: "Live probe failures remain deterministic eval failures and do not become candidate self-reported correctness."
    test: "tests/validators/test_gdev_agent_validators.py::test_adapter_error_blocks_case"
  - id: AC-3
    description: "Known limits record that the current live gdev-agent local run reaches health/auth but blocks on upstream `/webhook` runtime errors."
    verify: "rg -n \"live gdev-agent probe|RemoteDisconnected|Future attached to a different loop|webhook_secrets\" docs/KNOWN_LIMITS.md docs/EVIDENCE_INDEX.md"

Files:
  - src/eval_ground_truth_lab/adapters/gdev_agent.py
  - tests/adapters/test_gdev_agent_adapter.py
  - docs/KNOWN_LIMITS.md
  - docs/EVIDENCE_INDEX.md
  - docs/IMPLEMENTATION_JOURNAL.md
  - .gitignore

Context-Refs:
  - docs/GDEV_AGENT_ADAPTER.md
  - docs/KNOWN_LIMITS.md
  - docs/IMPLEMENTATION_CONTRACT.md#candidate-adapters-are-isolated-and-instrumented

## T26: Live gdev-agent Proof Rerun Summary

Owner: codex
Phase: 7
Type: none
Depends-On: T25

Objective: |
  Re-run the live local gdev-agent integration after upstream runtime blockers
  are fixed and record the resulting proof state without promoting a failing
  quality run into the canonical baseline.

Acceptance-Criteria:
  - id: AC-1
    description: "Live probe summary records gdev-agent and Eval Lab versions, commands, case count, adapter-error count, and top failure categories."
    verify: "rg -n \"gdev-agent Live Probe Summary|Adapter errors|wrong routing|unsafe auto-approval|901292d|8b052f2\" reports/gdev-agent/live_probe_summary.md"
  - id: AC-2
    description: "Historical live probe summary records the pre-T27 quality and telemetry gaps after adapter errors reached zero."
    verify: "rg -n \"Adapter errors|wrong routing|cost regression|Superseded By\" reports/gdev-agent/live_probe_summary.md"
  - id: AC-3
    description: "Task ledger marks the later passing baseline refresh as T27 instead of leaving T26 as the current next task."
    verify: "rg -n \"T27: Passing gdev-agent Live Baseline Evidence Refresh|Next task: none in the current roadmap\" docs/tasks.md docs/CODEX_PROMPT.md"

Files:
  - reports/gdev-agent/live_probe_summary.md
  - docs/KNOWN_LIMITS.md
  - docs/EVIDENCE_INDEX.md
  - docs/IMPLEMENTATION_JOURNAL.md
  - docs/tasks.md
  - docs/CODEX_PROMPT.md

Context-Refs:
  - docs/GDEV_AGENT_ADAPTER.md
  - docs/KNOWN_LIMITS.md
  - reports/gdev-agent/live_probe_summary.md

## T27: Passing gdev-agent Live Baseline Evidence Refresh

Owner: codex
Phase: 7
Type: docs
Depends-On: T26

Objective: |
  Refresh Eval Lab evidence after gdev-agent demo-mode classification, routing,
  guard behavior, unsafe auto-approval, and deterministic cost telemetry are
  aligned with `datasets/gdev_agent/triage_v1.jsonl`.

Acceptance-Criteria:
  - id: AC-1
    description: "Canonical baseline report records a full 55-case live local run with zero failures."
    verify: "rg -n \"Committed run artifact case count: `55`|zero deterministic validator failures|No case-level failures\" reports/gdev-agent/baseline_report.md docs/CASE_STUDY.md"
  - id: AC-2
    description: "Canonical run artifact contains all 55 cases and zero validator failures."
    test: "tests/eval/test_gdev_agent_baseline_report.py::test_baseline_report_generated_from_run_artifact"
  - id: AC-3
    description: "Evidence package points to the passing live local baseline while preserving non-production limits."
    test: "tests/docs/test_final_evidence_pack.py"
  - id: AC-4
    description: "Static HTML report remains a derivative of canonical markdown."
    test: "tests/reports/test_html_report.py"

Files:
  - README.md
  - docs/CASE_STUDY.md
  - docs/EVIDENCE_INDEX.md
  - docs/GDEV_AGENT_ADAPTER.md
  - docs/KNOWN_LIMITS.md
  - docs/README.md
  - docs/CODEX_PROMPT.md
  - docs/IMPLEMENTATION_JOURNAL.md
  - docs/tasks.md
  - docs/audit/
  - reports/gdev-agent/
  - tests/eval/test_gdev_agent_baseline_report.py
  - tests/reports/test_html_report.py

Context-Refs:
  - docs/GDEV_AGENT_ADAPTER.md
  - docs/KNOWN_LIMITS.md
  - reports/gdev-agent/baseline_report.md
  - reports/gdev-agent/baseline_run.json
