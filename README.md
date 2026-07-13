# Eval Ground Truth Lab

Eval Ground Truth Lab is a local-first regression gate for engineers deciding
whether a model, prompt, tool, policy, or harness change is safe to release. It
runs versioned cases against baseline and candidate workflows, applies
deterministic quality, safety, cost, and latency rules, and emits a reviewable CI
decision with tamper-evident evidence.

## What This Is

The project is a narrow CLI-first release-decision tool for comparing a baseline
workflow against a candidate workflow with versioned datasets, atomically written and
checksum-sealed terminal run records, deterministic validators, threshold
comparisons, reports, and CI gates.

It is deterministic by default. Dataset identity, pass/fail validators,
thresholds, cost/latency accounting, and CI decisions are owned by code and
stored artifacts. Optional judge support exists, but judge output is bounded,
budgeted, and non-authoritative.

## Why Eval-First Matters

Prompt, model, adapter, and guardrail changes can silently reduce quality,
increase unsafe auto-approval, break structured output, raise cost, or worsen
latency. Eval Lab creates a repeatable check before changes are promoted.

The current proof target is a real local AI workflow system, `gdev-agent`. Eval
Lab evaluates it as the system under test rather than relying only on synthetic
fixtures.

## Current Maturity

Version `0.2.0` is a tested local open-source tool with an Apache-2.0 boundary,
packaged CLI, deterministic fixtures, one passing local conformance run, and one
published canonical hard-challenge failure. Evidence is synthetic or local. The
project has no claimed external user, production deployment, hosted service, or
production SLO.

## Relationship to the Portfolio

- Eval Lab owns versioned datasets, deterministic workflow-quality gates, and
  release-decision evidence.
- [Agent Runtime Grid](https://github.com/ashishki/Agent-Runtime-Grid) is an
  optional queue-backed execution layer; it does not own quality decisions and
  is not required by Eval Lab.
- [gdev-agent](https://github.com/ashishki/gdev-agent) is a reference workload.
  Its repository owns application behavior, tenant isolation, and candidate
  fixes.
- [AI Workflow Playbook](https://github.com/ashishki/AI_workflow_playbook) is an
  independent governance companion, not a runtime dependency.
- The thin umbrella pins compatible revisions and runs integration proofs; it
  does not absorb component code or Git history.

## Product Boundary and Non-Goals

Eval Lab owns local dataset loading, adapter invocation, deterministic scoring,
baseline/candidate comparison, evidence packaging, and bounded optional judging.
It does not provide a hosted scheduler, generic agent runtime, production
monitoring plane, customer-data labeling service, or universal safety proof.
Candidate code remains in the system-under-test repository.

## What Works Today

- Dataset registry for JSONL/YAML eval cases with stable dataset hashes.
- Atomic run records with strict identifiers and checksum-sealed terminal state.
- Content-addressed evidence manifests that detect missing, modified, or
  undeclared files.
- Deterministic validators for structured output, unsafe auto-approval, cost,
  and latency.
- Baseline/candidate comparison with CI-style exit codes.
- Synthetic, HTTP, and CLI adapter boundaries.
- gdev-agent dataset, response normalizer, and configured HTTP adapter boundary.
- gdev-agent live local baseline evidence report from a canonical 55-case run
  artifact.
- Executable gdev-agent 100-case challenge with expected-failure reconciliation,
  per-slice metrics, deterministic provider-fault injection, and honest gates.
- Verified content-addressed canonical challenge evidence against exact
  `gdev-agent` revision `0e4c5f0`; the published gate is FAIL with all failures
  retained rather than tuned away.
- CI-safe mocked gdev-agent smoke that does not require Docker Compose or a live
  gdev-agent service.
- Optional judge skeleton with budget precheck and JSONL cost telemetry.
- Optional OpenAI judge provider contract, disabled by default and tested with
  fake transport only.
- Harness metadata sidecar for comparing model, prompt, tools, memory policy,
  permissions, recovery policy, trace schema, environment, scorer, and budget as
  one eval unit.
- Cost telemetry rollup and fixture-safe budget check commands.
- Markdown reports and failure taxonomy.
- Append-only human review notes and file-backed review entries/decisions.
- Seeded smoke gate that intentionally exits `1` for seeded regressions.
- V1 synthetic evidence pack with 100 cases and 5 known seeded regressions.

## 5-Minute Reviewer Path

1. Read [docs/STACK_OVERVIEW.md](docs/STACK_OVERVIEW.md) for the three-project
   system map.
2. Read [docs/CASE_STUDY.md](docs/CASE_STUDY.md) for the project story.
3. Run the seeded smoke command below and confirm it exits `1`.
4. Review the gdev-agent eval command below and the baseline reports:
   [reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md)
   and
   [reports/gdev-agent/baseline_report.html](reports/gdev-agent/baseline_report.html).
5. Review the harder diagnostic challenge set:
   [docs/GDEV_AGENT_CHALLENGE_SET.md](docs/GDEV_AGENT_CHALLENGE_SET.md)
   and its [v0.2.0 executed evidence](docs/evidence/releases/v0.2.0/README.md).
6. Check the evidence map in [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md).
7. Check known limits in [docs/KNOWN_LIMITS.md](docs/KNOWN_LIMITS.md).

## Quickstart: Seeded Smoke

The seeded smoke command proves the gate catches a deliberately bad synthetic
candidate. The expected exit code is `1`.

```bash
python -m eval_ground_truth_lab.cli seeded-smoke \
  --dataset datasets/smoke/seeded_regressions.jsonl \
  --report reports/seeded-smoke.md
echo $?
```

CI runs this command and asserts the expected failure code, so the workflow stays
green while proving the regression gate catches unsafe, invalid, costly, and
accuracy regressions.

## Quickstart: gdev-agent Eval

This path is the current local integration proof, not a production eval platform
or hosted SaaS claim. It evaluates a locally running `gdev-agent` in
deterministic demo mode.

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker-compose up --build -d postgres redis migrate agent
make demo
```

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --candidate-version gdev-agent-demo-live-local-v2 \
  --component-revision <full-gdev-git-sha> \
  --report reports/gdev-agent/baseline_report.md
```

The committed baseline report shows dataset hash, case count, candidate version,
classification accuracy, risk-routing recall, unsafe auto-approval rate, invalid
structured output rate, guard block rate, human escalation recall, cost per case,
latency p95, failure taxonomy, and case-level failures:
[reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md).
It is a curated integration/conformance baseline, not a hard challenge-set
benchmark.

The three gdev scopes are intentionally distinct: the 55 cases here are an
external conformance/integration baseline; the 100-case challenge is Eval Lab's
hard diagnostic surface; the 180-case smoke referenced in stack documentation
belongs to gdev-agent itself and is not added to either Eval Lab result.

## Quickstart: gdev-agent Challenge

The challenge command requires explicit component provenance and writes JSON,
Markdown, a terminal run record, and a content-addressed manifest. Its ten
provider-error cases are deterministic harness injections; the remaining 90
cases call the configured candidate. A failed threshold returns exit code `1`.
Live HTTP request and message IDs are scoped by a deterministic digest of the
run ID, candidate version, component revision, and dataset hash so an earlier
gdev Redis dedup entry cannot be reused by a different eval run. The namespace
identifier and whether it was applied are recorded in challenge provenance and
manifest metadata.

```bash
eval-ground-truth-lab run-gdev-agent-challenge \
  --base-url http://localhost:8000 \
  --run-id <new-unique-run-id> \
  --run-dir /tmp/eval-lab-gdev-challenge-runs \
  --candidate-version gdev-agent-demo \
  --component-revision <full-gdev-git-sha> \
  --component-worktree-state clean \
  --environment-label local-compose-demo \
  --evidence-dir /tmp/gdev-challenge-evidence

eval-ground-truth-lab verify-evidence \
  --manifest /tmp/gdev-challenge-evidence/sha256-*.manifest.json
```

The committed [v0.2.0 challenge package](docs/evidence/releases/v0.2.0/README.md)
records 90 real local HTTP candidate cases plus ten deterministic fault cases
against clean `gdev-agent` revision `0e4c5f0`. The gate correctly exits `1`:
reconciled pass rate `0.32`, classification accuracy `0.244444`, 68 unexpected
failures, 58 blocking failures, and `10/10` expected faults matched. Five
thresholds fail. This is canonical evidence of a failing fixed candidate, not a
passing workload or production-quality claim.

## Architecture

The canonical architecture is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
The cross-project stack map is in [docs/STACK_OVERVIEW.md](docs/STACK_OVERVIEW.md).
CLI commands are documented in [docs/CLI.md](docs/CLI.md).
The evidence index is in [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md).
Harness comparison metadata is documented in
[docs/HARNESS_COMPARISON.md](docs/HARNESS_COMPARISON.md).
The current v1 evidence report is in
[reports/v1/evidence_report.md](reports/v1/evidence_report.md).
The current gdev-agent baseline report is in
[reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md).
The derivative HTML report is in
[reports/gdev-agent/baseline_report.html](reports/gdev-agent/baseline_report.html).
The gdev-agent diagnostic challenge set is documented in
[docs/GDEV_AGENT_CHALLENGE_SET.md](docs/GDEV_AGENT_CHALLENGE_SET.md), with the
committed scope report in
[reports/gdev-agent/challenge_report.md](reports/gdev-agent/challenge_report.md).
The executed challenge artifacts and verifier manifest are in
[docs/evidence/releases/v0.2.0/](docs/evidence/releases/v0.2.0/).
Known gaps are tracked in [Known Gaps](#known-gaps).

Core shape:

- local CLI and filesystem artifacts first
- deterministic validators before optional judging
- configured adapter boundaries only
- synthetic data in committed fixtures
- reports as reviewable evidence

## Known Gaps

- The gdev-agent adapter is unit-tested with mocked transport in CI; the live
  local baseline still requires an operator-run gdev-agent stack.
- The gdev-agent baseline report is a synthetic/local deterministic artifact
  from a full 55-case live local run, not a production quality score.
- The 55-case baseline is intentionally clean conformance evidence. The harder
  100-case canonical local run is published and fails five thresholds; it must
  not be reinterpreted as a passing workload.
- Accuracy for synthetic smoke proof still uses fixture behavior; the current
  gdev-agent live local baseline is checked by deterministic validators.
- Cost telemetry rollup and fixture-safe budget check commands exist; live judge
  cost gates require telemetry rollup artifacts and an approved policy.
- Optional OpenAI judge provider contract exists, but no live provider call is
  enabled by default.
- Human review has an append-only protocol, but `challenge_v1` has zero
  independent annotators and zero external workflow owners. Its public labels
  are self-authored development hypotheses, not a blind holdout.
- No dashboard, hosted service, continuous eval, or production platform claim is
  made.

## Roadmap

The current roadmap is complete through the first published hard challenge and
benchmark-method package:

1. README and evidence packaging: complete.
2. gdev-agent triage dataset: complete.
3. gdev-agent output normalizer: complete.
4. real gdev-agent HTTP adapter: complete.
5. gdev-agent deterministic validators: complete.
6. `dataset-inspect`, `run-gdev-agent`, and `compare` CLI commands: complete.
7. gdev-agent baseline report: complete.
8. mocked CI smoke for the gdev adapter: complete.
9. cost rollup and budget check: complete.
10. final evidence pack with passing 55-case live local baseline: complete.
11. gdev-agent diagnostic challenge engine and canonical local execution:
    complete; the fixed candidate gate is published as FAIL.
12. Dataset card, provenance, hypotheses, leakage boundary, labeling/review
    protocol, and reproducible content-addressed report: complete for the public
    development set.
13. Independently owned adapter, independent labels, a blind successor holdout,
    and real-user feedback: not claimed; these require external participants.

## License

Code, documentation, and authored synthetic datasets are available under the
[Apache License 2.0](LICENSE). Dataset scope and contribution boundaries are in
[datasets/README.md](datasets/README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
The installed-version compatibility review is in
[docs/LICENSE_REVIEW.md](docs/LICENSE_REVIEW.md).

Current evidence surfaces are linked from
[docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md) and
[docs/STACK_OVERVIEW.md](docs/STACK_OVERVIEW.md).
