# Product Specification - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11

## Overview

Eval Ground Truth Lab gives operators a repeatable way to register datasets, run
baseline and candidate systems, compare results, inspect failures, and block
regressions in CI. The core path is deterministic. Optional model judging only
assists subjective review and cannot override deterministic gates without human
approval.

## User Roles

| Role | Needs |
|------|-------|
| AI engineer | Run local evals before changing prompts, models, or guardrails. |
| Eval engineer | Maintain datasets, validators, failure taxonomy, and thresholds. |
| Platform engineer | Integrate CI gates and keep run storage reproducible. |
| Eval operator | Inspect baseline evidence, seeded regression proof, and report quality. |

## Feature Area: Dataset Registry

Description:
The registry loads JSONL or YAML eval case files, validates their schema, assigns
a stable dataset hash, and records dataset metadata for later baseline and
candidate comparisons.

Acceptance criteria:

1. Given a valid dataset file, the registry returns dataset ID, schema version,
   case count, and SHA-256 content hash.
2. Given a dataset with a missing required field, the registry returns a
   structured validation error that names the case ID and field.
3. Reordering unrelated metadata fields does not change semantic case validation;
   changing case input or expected output changes the dataset hash.
4. Dataset files containing real secrets or private data are rejected by the
   configured fixture scanner once that scanner exists.

Out of scope:

- Remote dataset hosting.
- Large-scale labeling workflow.
- Multi-tenant dataset permissions.

## Feature Area: Run Orchestration and Storage

Description:
The runner executes a baseline or candidate against a dataset hash, stores
case-level outputs and metadata, and prevents duplicate case results within one
run.

Acceptance criteria:

1. A run record includes run ID, run type, dataset hash, candidate version,
   validator version, threshold config version, start time, completion time,
   status, cost, and latency fields.
2. A completed run is immutable; a rerun creates a new run ID linked to the same
   dataset hash.
3. If a run is interrupted, completed case results remain readable and the run
   status records the interruption without mutating a prior completed run.
4. Candidate calls retry at most once unless configuration explicitly changes the
   retry budget.

Out of scope:

- Distributed job queues.
- Long-lived autonomous workers.
- Production scheduling.

## Feature Area: Deterministic Validators

Description:
Validators enforce structured output, safety, confidence, evidence, and policy
requirements without model judgment.

Acceptance criteria:

1. JSON schema validation fails cases with invalid JSON, missing required fields,
   unknown enum values, or forbidden fields.
2. Unsafe auto-approval validators fail cases that mark unsafe actions as
   approved without required evidence and confidence.
3. Cost and latency validators compare candidate metrics to configured baseline
   thresholds and record the delta.
4. Validator output includes case ID, validator ID, pass/fail status, failure
   category, and human-readable evidence.

Out of scope:

- Free-form safety certification.
- Model-owned enforcement of deterministic thresholds.

## Feature Area: Baseline Comparison and Regression Gates

Description:
The comparison engine reads baseline and candidate runs for the same dataset hash
and produces pass/fail decisions based on configured thresholds.

Acceptance criteria:

1. Comparison fails when baseline and candidate runs use different dataset hashes
   unless an explicit migration comparison mode is selected.
2. The comparison report includes accuracy delta, invalid output rate, unsafe
   auto-approval rate, p95 latency, cost per case, and threshold status.
3. The CI command exits with code 1 when any blocking threshold fails.
4. The seeded unsafe regression smoke dataset fails CI after the smoke gate is
   added.

Out of scope:

- Ranking unrelated systems across different datasets.
- Universal benchmark claims.

## Feature Area: Optional LLM Judge and Human Review

Description:
The optional judge scores configured subjective cases under a strict budget and
routes ambiguous results to human review. Judge output is advisory until the
operator explicitly approves stronger authority with calibration evidence.

Acceptance criteria:

1. Judge mode is disabled when no provider key or budget is configured.
2. A judge-enabled run records model, prompt/rubric version, input tokens, output
   tokens, estimated cost, latency, retries, and per-case score.
3. Judge calls stop before exceeding the configured per-run budget.
4. Ambiguous judge results create human review queue entries with case ID,
   candidate output, rubric version, judge explanation, and reviewer status.
5. A candidate cannot pass solely because of a judge score when a deterministic
   blocking validator failed.

Out of scope:

- Judge-only pass/fail authority.
- Automated acceptance of ambiguous safety failures.

## Feature Area: Reporting and Failure Taxonomy

Description:
Reports make failures inspectable by category, severity, validator, dataset
slice, and candidate version.

Acceptance criteria:

1. Markdown reports include run metadata, threshold summary, top failure
   categories, case-level failure table, and links to raw run artifacts.
2. HTML reports render the same canonical data as markdown and do not become a
   separate source of truth.
3. Failure taxonomy labels include unsafe auto-approval, invalid structured
   output, missing evidence, low confidence, accuracy regression, cost
   regression, and latency regression.
4. Human review decisions append an auditable note that includes reviewer,
   timestamp, case ID, decision, and rationale.

Out of scope:

- Full dashboard product.
- Multi-user workflow assignment.

## Feature Area: CI Integration

Description:
GitHub Actions runs lint, format, tests, and later smoke eval gates. CI is the
default proof surface for regression prevention.

Acceptance criteria:

1. CI runs on pull requests and pushes to `main` or `master`.
2. CI installs the project, runs `ruff check`, runs `ruff format --check`, and
   runs pytest.
3. The smoke eval command is added before seeded regression claims are made.
4. Cost threshold enforcement is not enabled until telemetry source and rollup
   command exist.

Out of scope:

- Production deployment.
- Hosted dashboard environments.
