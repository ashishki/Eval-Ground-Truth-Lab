# Eval Ground Truth Lab

Eval Ground Truth Lab is a local-first regression evaluation framework for
LLM/agent workflows. It catches regressions in structured output, unsafe
auto-approval, routing, cost, latency, and accuracy before changes are promoted.

## What This Is

The project is a CLI-first eval framework for comparing a baseline workflow
against a candidate workflow with versioned datasets, atomically written and
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
   and
   [reports/gdev-agent/challenge_report.md](reports/gdev-agent/challenge_report.md).
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
  --candidate-version gdev-agent-demo \
  --component-revision <full-gdev-git-sha> \
  --component-worktree-state clean \
  --environment-label local-compose-demo \
  --evidence-dir /tmp/gdev-challenge-evidence

eval-ground-truth-lab verify-evidence \
  --manifest /tmp/gdev-challenge-evidence/sha256-*.manifest.json
```

No canonical challenge result is committed until the fixed external gdev-agent
service can be run and its exact revision captured.

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
  100-case command is executable, but it is not yet a canonical live result
  because the external fixed gdev-agent service must be run separately.
- Accuracy for synthetic smoke proof still uses fixture behavior; the current
  gdev-agent live local baseline is checked by deterministic validators.
- Cost telemetry rollup and fixture-safe budget check commands exist; live judge
  cost gates require telemetry rollup artifacts and an approved policy.
- Optional OpenAI judge provider contract exists, but no live provider call is
  enabled by default.
- Human review has append-only file-backed entries and decisions; richer
  operator workflow is still future work.
- No dashboard, hosted service, continuous eval, or production platform claim is
  made.

## Roadmap

The current roadmap is complete through the first passing live local
`gdev-agent` baseline:

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
11. gdev-agent diagnostic challenge engine: complete; canonical external-system
    execution and release promotion remain operator work.

## License

Code, documentation, and authored synthetic datasets are available under the
[Apache License 2.0](LICENSE). Dataset scope and contribution boundaries are in
[datasets/README.md](datasets/README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
The installed-version compatibility review is in
[docs/LICENSE_REVIEW.md](docs/LICENSE_REVIEW.md).

Current evidence surfaces are linked from
[docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md) and
[docs/STACK_OVERVIEW.md](docs/STACK_OVERVIEW.md).
