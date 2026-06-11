# Implementation Contract - Eval Ground Truth Lab

Status: IMMUTABLE - changes to this document require an Architectural Decision
Record filed in `docs/adr/`.
Version: 1.0
Effective date: 2026-06-11

Any agent may cite this document as the authority on implementation rules. A
violation of this contract is a P1 finding unless a stricter severity is stated.

## Universal Rules

### SQL Safety

- All SQL must be parameterized.
- Do not interpolate variables into SQL strings with f-strings, percent
  formatting, `format`, or concatenation.
- Identifier allowlists are required before dynamic table, column, or ordering
  choices are introduced.
- Violation: P1.

### Credentials and Secrets

- Do not commit credentials, API keys, tokens, passwords, private data, or real
  `.env` files.
- Test fixtures may use obvious placeholder strings only.
- Secrets come from environment variables or GitHub Actions secrets.
- Required environment variables must be documented in
  `docs/ARCHITECTURE.md#runtime-contract`.
- Violation: P1, and P0 if a real secret is exposed.

### CI Gate

- CI must pass before merge.
- CI includes lint, format check, and tests.
- Failing CI is not bypassed because of deadline pressure.
- Flaky tests are fixed or quarantined with an explicit finding and owner.
- Violation: P1.

### No Self-Review

- The agent that writes a meaningful implementation change does not close its
  own review findings.
- Review findings are resolved with code/test evidence or explicitly deferred by
  the human owner.
- Violation: P1 for P1/P2 finding closure without evidence.

### Repository Authority

- Repository artifacts, code, tests, CI, eval reports, audit reports, and run
  records are authoritative.
- Decision logs, journals, evidence indexes, and generated summaries are
  retrieval surfaces only.
- Generated or remembered context must cite canonical paths before it influences
  implementation or review.
- Violation: P1 when convenience memory overrides canonical repo state.

## Project-Specific Rules

### Deterministic Gates Own Blocking Decisions

Schema validity, unsafe auto-approval checks, confidence thresholds,
evidence-required checks, cost deltas, latency deltas, and CI threshold
decisions are deterministic. Optional judge output cannot convert a deterministic
blocking failure into a pass.

Violation: P1.

### Dataset and Run Identity Are Immutable

Dataset hashes identify the evaluated case set. Completed run records are
immutable. Reruns create new run IDs rather than rewriting prior completed
results.

Violation: P1 for mutation of completed records; P2 for missing lineage fields
that do not affect an existing completed run.

### Synthetic Data Only in V1

Committed datasets and fixtures must be synthetic. Real PII, private customer
data, secrets, or production transcripts are out of scope for v1.

Violation: P1, and P0 if real sensitive data is committed.

### Explicit Candidate Adapter Boundary

Candidate adapters may call only configured HTTP endpoints or configured CLI
commands. Eval case files cannot declare arbitrary network destinations, shell
commands, package installs, or credential paths.

Violation: P1.

### Optional Judge Is Budgeted and Non-Authoritative

Judge mode is disabled unless provider configuration and a budget cap exist.
Judge calls record model, prompt/rubric version, token counts, estimated cost,
latency, retries, and score. Judge authority cannot become blocking without
human approval and calibration evidence.

Violation: P1 for unbudgeted judge calls or judge-only blocking authority.

## Continuity and Retrieval Rules

- `docs/ARCHITECTURE.md`, `docs/spec.md`, `docs/tasks.md`,
  `docs/CODEX_PROMPT.md`, this contract, tests, CI, eval reports, and audit
  reports are canonical.
- `docs/DECISION_LOG.md`, `docs/IMPLEMENTATION_JOURNAL.md`, and
  `docs/EVIDENCE_INDEX.md` are navigation and retrieval surfaces.
- Before changing architecture, runtime tier, judge authority, cost policy,
  threshold policy, failure taxonomy, or seeded regression gates, read the
  relevant decision log and evidence index entries.
- Task-level `Context-Refs` are the first retrieval target for implementation.
- If a retrieval surface conflicts with a canonical artifact, fix the retrieval
  surface or escalate before coding.

## Control Surface and Runtime Boundaries

| Boundary | Rule |
|----------|------|
| Secrets scope | Only local operator env vars and GitHub Actions secrets may hold credentials. Judge credentials are unavailable by default. |
| Network egress | Candidate HTTP adapters call only the configured base URL. Judge provider egress is disabled unless configured. Dataset cases cannot define egress. |
| Privileged actions | Threshold changes, accepting safety regression, enabling judge as blocking authority, and high-risk dataset edits require human approval. |
| Runtime mutation | Dependency and toolchain changes happen through committed files and CI. Eval cases cannot install packages or mutate the runtime. |
| Persistence | SQLite/Postgres run metadata and filesystem reports persist. Completed runs are immutable. |
| Auditability | Threshold, rubric, dataset, and judge-authority changes are recorded in canonical docs, ADRs, or run metadata before use. |

### Runtime Tier Guardrails

- Implement within T1 unless an ADR changes runtime tier.
- Do not add T2/T3 behavior such as privileged worker state, broad shell
  mutation, mutable autonomous execution, or persistent agent runtime without an
  ADR and human approval.
- Container/service configuration must be reproducible from committed files.

## Mandatory Pre-Task Protocol

Before implementation:

1. Read `docs/IMPLEMENTATION_CONTRACT.md`.
2. Read the assigned task block in `docs/tasks.md`.
3. Read the task's `Context-Refs`.
4. Run `python -m pytest tests -q --tb=short` and record the current baseline.
5. Run `ruff check src tests`.
6. Run `ruff format --check src tests`.
7. If the task affects architecture, runtime, judge authority, budget policy,
   threshold policy, seeded regression evidence, or failure taxonomy, read
   `docs/DECISION_LOG.md` and `docs/EVIDENCE_INDEX.md` before editing.

## Forbidden Actions

- Do not interpolate SQL.
- Do not commit secrets, real PII, private transcripts, or real customer data.
- Do not skip baseline capture before implementation.
- Do not weaken tests, acceptance criteria, validators, thresholds, or CI gates
  to obtain a pass.
- Do not self-close P1/P2 findings without code/test/eval evidence.
- Do not defer CI setup past Phase 1.
- Do not expand runtime tier, network egress, tool privileges, judge authority,
  or autonomous behavior without ADR and approval.
- Do not make judge output the sole blocking authority.
- Do not let eval cases define arbitrary network calls, shell commands, package
  installs, or credential paths.

## Cost Budget Rules

- Deterministic eval mode has 0 USD model spend.
- Recurring or materially costly AI usage is governed by `docs/COST_BUDGET.md`.
- Every AI/model task must have a per-run or per-task budget.
- Model escalation, retry expansion, tool-call expansion, fan-out increase, or
  budget overrun requires approval.
- Cost-saving changes are accepted only when quality and latency thresholds
  remain within policy.
- Enforceable automated cost gates require a telemetry source and a rollup
  command. Until T09 implements telemetry, cost thresholds are manual-review
  policy, not CI-enforced checks.

Violation: P1 for missing budget on active model work; P0 if an unapproved
overrun creates production, customer, or billing risk.

## Inactive Profile Rules

- RAG Profile: OFF. Do not add retrieval ingestion, embeddings, vector indexes,
  or retrieval answer paths without ADR.
- Tool-Use Profile: OFF. Do not add LLM-directed tool choice or unsafe external
  action paths without ADR.
- Agentic Profile: OFF. Do not add autonomous loops, handoffs, or termination
  contracts without ADR.
- Planning Profile: OFF. Do not make structured plan output a primary product
  deliverable without ADR.
- Compliance Profile: OFF. Do not claim compliance evidence or regulatory
  coverage without ADR and explicit controls.

