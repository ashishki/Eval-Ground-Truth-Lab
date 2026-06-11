# Tasks - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11
Mode: Standard

## Task Rules

- Every task has explicit dependencies.
- Every acceptance criterion names a concrete test or verification command.
- `Context-Refs` are required when the task changes architecture, runtime,
  judge authority, budget policy, seeded regression gates, or failure taxonomy.
- Product capability profiles are OFF in Phase 1. Do not add RAG, Tool-Use,
  Agentic, Planning, or Compliance profile work without an ADR.

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
