# Architecture - Eval Ground Truth Lab

Version: 1.0
Last updated: 2026-06-11
Status: Draft

## System Overview

Eval Ground Truth Lab is a local-first regression evaluation platform for LLM and
agent workflows. It serves AI engineers, eval engineers, platform engineers, and
reviewers who need reproducible evidence that a candidate workflow did not
regress against a baseline. The system is deterministic by default: datasets,
validators, run identity, thresholds, cost accounting, latency accounting, and CI
decisions are owned by code and stored artifacts; optional model judging is
bounded, budgeted, calibrated, and routed to human review where ambiguity remains.

## Problem Fit and Adoption Reality

### Problem-First Entry Gate

| Question | Answer |
|----------|--------|
| Concrete operational pain | Prompt, model, adapter, and guardrail changes can silently reduce quality, increase unsafe auto-approval, raise cost, or worsen latency. |
| Current workaround | Small pytest sets, manual prompt checks, ad hoc spreadsheets, one-off eval scripts, and subjective sample review. |
| Why existing process is insufficient | The current process lacks versioned datasets, baseline comparison, failure taxonomy, CI gating, cost/latency tracking, and a clear split between deterministic validation and judge-based scoring. |
| First user / operator who feels the pain | The portfolio owner maintaining gdev-agent and related LLM workflows; secondarily, AI platform/eval reviewers inspecting the project. |
| What would make v1 not worth adopting | A generic score without failure explanations, pass/fail controlled only by an uncalibrated judge, missing baseline comparison, or inability to catch seeded regressions. |
| First proof of value | At least 100 eval cases, at least 5 seeded regressions, and CI failure for unsafe regression, invalid structured output, excessive cost increase, and material accuracy drop. |

### Adoption Reality Gate

| Boundary | Decision |
|----------|----------|
| Work AI is expected to improve | Optional subjective scoring, failure explanation clustering, failure summarization, and suggested taxonomy labels for review. |
| Work AI will not replace | Human rubric ownership, ground-truth creation, final adjudication of ambiguous cases, threshold changes, and acceptance of production changes. |
| Claims not allowed before evidence | The system does not prove safety, replace domain experts, provide universal LLM truth, or make an LLM judge authoritative without calibration and human review. |
| Demo-to-production evidence required | Dataset hash, candidate version, baseline version, threshold config, case-level outputs, validator version, judge rubric, cost/latency metrics, seeded regression report, and human review notes for ambiguous cases. |

## Solution Shape

| Decision | Selection | Justification |
|----------|-----------|---------------|
| Primary shape | Hybrid decomposition: deterministic subsystem plus fixed workflow orchestration | The core problem is formalizable with schemas, validators, thresholds, run records, and reports. A fixed workflow coordinates dataset registration, baseline run, candidate run, comparison, reporting, and human review. Optional judge calls are a bounded subpath, not the system authority. |
| Governance level | Standard | The project is an internal/portfolio operational system with recurring evidence, CI gates, optional paid model use, and reviewable audit needs. It does not handle real PII, compliance evidence, privileged autonomous execution, or production customer risk in v1. |
| Runtime tier | T1 | The v1 target is local CLI plus Docker Compose and GitHub Actions. Containerized Postgres/SQLite-backed runs and explicit candidate adapters need bounded service boundaries, but no ephemeral microVM or persistent privileged worker is justified. |

### Rejected Lower-Complexity Options

| Rejected option | Why it is insufficient |
|-----------------|------------------------|
| Manual spreadsheets and sample review | They do not provide dataset hashes, immutable run records, reproducible baseline comparison, or CI gates. |
| One-off eval scripts | They can calculate a score but do not create durable failure taxonomy, review queues, budget boundaries, or reusable adapters. |
| Judge-only scoring | It overtrusts an uncalibrated model and misses deterministic failures such as invalid JSON, unsafe action flags, and cost or latency regression. |

### Minimum Viable Control Surface

- Dataset identity is a content hash plus schema version; eval runs reference the dataset hash.
- Run records are immutable once completed; reruns create new run IDs.
- Deterministic validators own schema validity, policy checks, thresholds, cost, and latency.
- Optional judge calls are sampled or routed, budget-capped, and never become blocking authority without human approval.
- CI fails on configured regression thresholds and on seeded unsafe smoke cases.
- Human approval is required for threshold changes and acceptance of safety regression.

### Human Approval Boundaries

| Boundary | Human approval required? | Why |
|----------|--------------------------|-----|
| Changing pass/fail thresholds | Yes | Thresholds define the release gate and can hide regressions if loosened. |
| Accepting a candidate with safety regression | Yes | Unsafe auto-approval is a high-risk failure class even in v1. |
| Adding or removing high-risk eval cases | Yes | Dataset composition changes the meaning of baseline comparisons. |
| Marking ambiguous failures as acceptable | Yes | Ambiguity requires accountable rubric judgment. |
| Enabling LLM judge as blocking authority | Yes | A judge cannot become authoritative without calibration evidence and review. |
| Running deterministic evals and producing reports | No | This is the safe core workflow when thresholds are already configured. |

### Deterministic vs LLM-Owned Subproblems

| Subproblem | Owner | Reason |
|------------|-------|--------|
| Dataset identity/versioning | Deterministic | Hashes, schema versions, and file paths must be reproducible. |
| Structured output validation | Deterministic | JSON schema, required fields, enums, forbidden fields, and unsafe flags are code-owned. |
| Metrics and thresholds | Deterministic | Accuracy, invalid output rate, unsafe auto-approval rate, p95 latency, and cost deltas must be repeatable. |
| Run idempotency and audit records | Deterministic | Duplicate prevention and immutable records cannot depend on model judgment. |
| Subjective explanation quality | LLM-assisted, human-reviewed | Optional judge output can help triage but needs calibration and human adjudication. |
| Failure summaries and suggested labels | LLM-assisted, non-authoritative | Suggestions reduce review effort but canonical taxonomy labels remain auditable data. |

### Runtime and Isolation Model

| Property | Decision |
|----------|----------|
| Isolation boundary | T1 container and CI job boundary for local service dependencies and verification. |
| Persistence model | SQLite or Postgres for run metadata; filesystem for datasets and reports. Eval run records are immutable. |
| Network model | Candidate adapters may call explicit configured HTTP endpoints. Eval case data cannot declare arbitrary network calls. Optional judge calls require explicit provider configuration and budget. |
| Secrets model | Secrets live in environment variables or GitHub Actions secrets. No secrets are committed. Optional judge key is unavailable by default. |
| Runtime mutation boundary | Package and service changes occur through committed dependency files and CI. Runtime package installation by eval cases is forbidden. |
| Rollback / recovery model | Rerun from the same dataset hash, candidate version, validator version, and threshold config; failed or interrupted runs do not mutate completed run records. |

## Inference / Model Strategy

| Path / Task | Model class | Why this class | Fallback / escalation | Budget / latency constraint |
|-------------|-------------|----------------|-----------------------|-----------------------------|
| Optional rubric judge | Cheap structured-output judge | Subjective outputs may need rubric scoring, but deterministic validators remain primary. | Escalate to stronger judge only for sampled ambiguous cases after budget approval. | Recommended under 2 USD per full benchmark run; sampled mode preferred for CI. |
| Failure summarization | Cheap summarization model or deterministic template | Summaries are non-authoritative and optimize review ergonomics. | Disable summarization and show raw failures when budget is unavailable. | Zero model calls in default deterministic mode. |
| Suggested taxonomy labels | Cheap classifier or deterministic keyword baseline | Labels are suggestions and require human review for ambiguous cases. | Route to human review when confidence is below threshold. | No blocking CI dependence on model output in v1. |

## Cost Budget and Attribution

| Budget Scope | Limit | Approval Trigger | Attribution Fields | Evidence Location |
|--------------|-------|------------------|--------------------|-------------------|
| Deterministic run | 0 USD model spend | Any model call in deterministic mode | project, workflow, environment | `docs/COST_BUDGET.md` |
| Judge-enabled run | Recommended cap: 2 USD per benchmark run | Projected or actual overrun; model escalation; retry expansion; fan-out increase | project, task/workflow, role, model, operator, feature, environment | `docs/COST_BUDGET.md` |
| Monthly project | Unknown initial ceiling; provisional 25 USD until changed | Exceeding provisional cap or enabling recurring scheduled judge runs | project, operator, model, environment | `docs/COST_BUDGET.md` |

## Capability Profiles

| Profile | Status | Evaluation Artifact | Justification |
|---------|--------|---------------------|---------------|
| RAG | OFF | `docs/retrieval_eval.md` | Retrieval may help display prior similar failures later, but v1 core does not require a retrieval-backed answer system, corpus ingestion, embeddings, citations, or insufficient-evidence behavior. |
| Tool-Use | OFF | `docs/tool_eval.md` | Candidate adapters are deterministic configured integrations. LLM-directed tool calls that choose or mutate external state are out of scope for v1. |
| Agentic | OFF | `docs/agent_eval.md` | Eval orchestration is a fixed deterministic workflow, not a multi-step autonomous loop. |
| Planning | OFF | `docs/plan_eval.md` | The product emits reports and review queues, not structured plans as its primary deliverable. |
| Compliance | OFF | `docs/compliance_eval.md` | V1 uses synthetic data only and has no named regulatory framework launch gate. |

## Component Table

| Component | File / Directory | Responsibility |
|-----------|------------------|----------------|
| Dataset registry | `src/eval_ground_truth_lab/datasets/` | Load JSONL/YAML cases, validate schema, compute dataset hash, and expose dataset metadata. |
| Run store | `src/eval_ground_truth_lab/runs/` | Persist baseline and candidate run metadata, case results, cost, latency, and immutable run status. |
| Validator engine | `src/eval_ground_truth_lab/validators/` | Apply deterministic schema, policy, safety, confidence, and evidence-required checks. |
| Adapter layer | `src/eval_ground_truth_lab/adapters/` | Invoke synthetic demo candidates and explicit gdev-agent HTTP/CLI candidates. |
| Comparison engine | `src/eval_ground_truth_lab/compare/` | Compare baseline and candidate metrics and calculate regression deltas. |
| Judge and review | `src/eval_ground_truth_lab/judging/` | Run optional budget-capped judge calls and route ambiguous outputs to human review. |
| Reporting | `src/eval_ground_truth_lab/reports/` | Produce markdown/HTML reports with metrics, failure taxonomy, and seeded regression evidence. |
| CLI | `src/eval_ground_truth_lab/cli.py` | Provide local commands for dataset inspection, runs, comparison, and CI smoke evals. |

## Data Flow

1. Operator registers or selects a dataset file.
2. Dataset registry validates case schema and computes a dataset hash.
3. Baseline runner invokes the baseline candidate and stores immutable case results.
4. Candidate runner invokes the candidate system with the same dataset hash and stores immutable case results.
5. Validator engine applies deterministic validators to every case result.
6. Optional judge scores configured subjective cases within the declared budget.
7. Comparison engine computes metric deltas against the baseline and threshold config.
8. Human review queue receives ambiguous or judge-routed cases.
9. Reporter writes markdown/HTML output and updates evidence pointers.
10. CI command exits non-zero when configured thresholds fail.

## Tech Stack

| Area | Choice | Rationale |
|------|--------|-----------|
| Language | Python 3.12 | Fits Typer/FastAPI/Pydantic ecosystem and GitHub Actions support. |
| CLI | Typer or argparse baseline | CLI-first local workflow is the v1 entry point; Typer can be added when command surface grows. |
| API | FastAPI optional after CLI core | Dashboard/API is useful later but not required for first deterministic eval loop. |
| Data validation | Pydantic and JSON Schema | Explicit schemas for eval cases, structured outputs, and run records. |
| Storage | SQLite by default; Postgres-compatible repository boundary | Local mode stays simple while preserving a path to Postgres. |
| Reports | Markdown first; Jinja2/HTML later | Markdown is reviewable in CI and easy to diff. |
| Tests | pytest and ruff | Standard Python verification gate. |
| CI | GitHub Actions | Required Phase 1 gate for lint, format, and tests. |

## Security Boundaries

- V1 uses synthetic data only; real PII is forbidden in committed datasets and fixtures.
- Candidate adapters only call configured HTTP base URLs or configured CLI commands.
- Eval case files cannot declare arbitrary network destinations, shell commands, or package installs.
- Optional judge provider credentials come from environment variables and are unavailable by default.
- Reports and logs must not include secrets or real private data.
- Public health/status endpoints, if added later, expose no secrets and no dataset contents.

## External Integrations

| Integration | Required in v1? | Credentials | Boundary |
|-------------|-----------------|-------------|----------|
| gdev-agent HTTP/CLI candidate | Yes for portfolio proof; adapter can be stubbed first | Optional local token from environment | Explicit configured endpoint or command only. |
| Synthetic demo candidate | Yes | None | Local deterministic fixture. |
| LLM judge provider | Optional | API key from environment | Disabled unless budget and provider settings are configured. |
| GitHub Actions | Yes | Repository CI token managed by GitHub | Runs lint, format, tests, and later smoke eval gates. |
| Agent Runtime Grid | No | N/A | Future optional parallel-run integration, not a v1 dependency. |

## File Layout

```text
.
|-- .github/workflows/ci.yml
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- CODEX_PROMPT.md
|   |-- COST_BUDGET.md
|   |-- DECISION_LOG.md
|   |-- EVIDENCE_INDEX.md
|   |-- IMPLEMENTATION_CONTRACT.md
|   |-- IMPLEMENTATION_JOURNAL.md
|   |-- PROJECT_BRIEF.md
|   |-- README.md
|   |-- spec.md
|   |-- tasks.md
|   `-- audit/
|       |-- AUDIT_INDEX.md
|       `-- PHASE1_AUDIT.md
|-- src/eval_ground_truth_lab/
|   |-- adapters/
|   |-- compare/
|   |-- datasets/
|   |-- judging/
|   |-- reports/
|   |-- runs/
|   `-- validators/
`-- tests/
```

## Runtime Contract

| Env var | Required? | Purpose |
|---------|-----------|---------|
| `EVAL_DB_URL` | No | SQLite/Postgres run store URL; defaults to local SQLite when absent. |
| `EVAL_DATA_DIR` | No | Dataset directory; defaults to `datasets/`. |
| `EVAL_REPORT_DIR` | No | Report output directory; defaults to `reports/`. |
| `CANDIDATE_HTTP_BASE_URL` | No | Optional explicit HTTP candidate endpoint. |
| `CANDIDATE_CLI_COMMAND` | No | Optional explicit local candidate command. |
| `LLM_JUDGE_API_KEY` | No | Optional judge provider credential; judge disabled when absent. |
| `LLM_JUDGE_BUDGET_USD` | No | Per-run judge budget cap; defaults to deterministic-only mode. |

## Continuity and Retrieval Model

Canonical truth surfaces:

- `docs/ARCHITECTURE.md`
- `docs/spec.md`
- `docs/tasks.md`
- `docs/CODEX_PROMPT.md`
- `docs/IMPLEMENTATION_CONTRACT.md`
- ADRs once introduced
- tests, CI output, eval reports, and audit reports

Retrieval convenience surfaces:

- `docs/DECISION_LOG.md`
- `docs/IMPLEMENTATION_JOURNAL.md`
- `docs/EVIDENCE_INDEX.md`
- task-level `Context-Refs`

Scoped retrieval rules:

- Read `Context-Refs` before broad searching.
- Read the decision log before changing architecture, runtime tier, cost policy,
  threshold policy, or judge authority.
- Read the evidence index before changing seeded regression gates, baseline
  reports, or failure taxonomy.
- Convenience summaries never override canonical docs, tests, CI, or eval
  artifacts.

## Non-Goals

- Do not build an enterprise eval SaaS in v1.
- Do not claim universal LLM truth or safety certification.
- Do not make an uncalibrated LLM judge the sole pass/fail authority.
- Do not introduce autonomous eval-case execution, arbitrary shell commands, or
  package mutation from dataset files.
- Do not add RAG, agent loops, compliance evidence, or privileged runtime
  infrastructure for speculative future flexibility.

