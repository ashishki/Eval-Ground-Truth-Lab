# Eval Ground Truth Lab

Eval Ground Truth Lab is a local-first regression evaluation framework for
LLM/agent workflows. It catches regressions in structured output, unsafe
auto-approval, routing, cost, latency, and accuracy before changes are promoted.

## What This Is

The project is a CLI-first eval framework for comparing a baseline workflow
against a candidate workflow with versioned datasets, immutable run artifacts,
deterministic validators, threshold comparisons, reports, and CI gates.

It is deterministic by default. Dataset identity, pass/fail validators,
thresholds, cost/latency accounting, and CI decisions are owned by code and
stored artifacts. Optional judge support exists, but judge output is bounded,
budgeted, and non-authoritative.

## Why Eval-First Matters

Prompt, model, adapter, and guardrail changes can silently reduce quality,
increase unsafe auto-approval, break structured output, raise cost, or worsen
latency. Eval Lab creates a repeatable check before changes are promoted.

The next proof target is a real local AI workflow system, `gdev-agent`. Eval Lab
will evaluate it as the system under test rather than relying only on synthetic
fixtures.

## What Works Today

- Dataset registry for JSONL/YAML eval cases with stable dataset hashes.
- Immutable run records for baseline and candidate outputs.
- Deterministic validators for structured output, unsafe auto-approval, cost,
  and latency.
- Baseline/candidate comparison with CI-style exit codes.
- Synthetic, HTTP, and CLI adapter boundaries.
- gdev-agent dataset, response normalizer, and configured HTTP adapter boundary.
- gdev-agent baseline evidence report from a canonical run artifact.
- CI-safe mocked gdev-agent smoke that does not require Docker Compose or a live
  gdev-agent service.
- Optional judge skeleton with budget precheck and JSONL cost telemetry.
- Optional OpenAI judge provider contract, disabled by default and tested with
  fake transport only.
- Cost telemetry rollup and fixture-safe budget check commands.
- Markdown reports and failure taxonomy.
- Append-only human review notes and file-backed review entries/decisions.
- Seeded smoke gate that intentionally exits `1` for seeded regressions.
- V1 synthetic evidence pack with 100 cases and 5 known seeded regressions.

## 5-Minute Reviewer Path

1. Read [docs/CASE_STUDY.md](docs/CASE_STUDY.md) for the project story.
2. Run the seeded smoke command below and confirm it exits `1`.
3. Review the gdev-agent eval command below and the baseline reports:
   [reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md)
   and
   [reports/gdev-agent/baseline_report.html](reports/gdev-agent/baseline_report.html).
4. Check the evidence map in [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md).
5. Check known limits in [docs/KNOWN_LIMITS.md](docs/KNOWN_LIMITS.md).

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

This path is the next local integration proof, not a production eval platform or
hosted SaaS claim. It will evaluate a locally running `gdev-agent` in deterministic
demo mode.

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker compose up --build -d
make demo
```

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --report reports/gdev-agent/baseline_report.md
```

The committed baseline report shows dataset hash, case count, candidate version,
classification accuracy, risk-routing recall, unsafe auto-approval rate, invalid
structured output rate, guard block rate, human escalation recall, cost per case,
latency p95, failure taxonomy, and case-level failures:
[reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md).

## Architecture

The canonical architecture is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
CLI commands are documented in [docs/CLI.md](docs/CLI.md).
The evidence index is in [docs/EVIDENCE_INDEX.md](docs/EVIDENCE_INDEX.md).
The current v1 evidence report is in
[reports/v1/evidence_report.md](reports/v1/evidence_report.md).
The current gdev-agent baseline report is in
[reports/gdev-agent/baseline_report.md](reports/gdev-agent/baseline_report.md).
The derivative HTML report is in
[reports/gdev-agent/baseline_report.html](reports/gdev-agent/baseline_report.html).
Known gaps are tracked in [Known Gaps](#known-gaps).

Core shape:

- local CLI and filesystem artifacts first
- deterministic validators before optional judging
- configured adapter boundaries only
- synthetic data in committed fixtures
- reports as reviewable evidence

## Known Gaps

- The gdev-agent adapter is unit-tested with mocked transport; live local
  integration still needs an operator-run gdev-agent stack.
- The gdev-agent baseline report is a compact synthetic/local deterministic
  artifact; full live local validation still needs an operator-run gdev-agent
  stack.
- Accuracy for synthetic smoke proof still uses fixture behavior; real
  gdev-agent correctness will come from deterministic validators.
- Cost telemetry rollup and fixture-safe budget check commands exist; live judge
  cost gates require telemetry rollup artifacts and an approved policy.
- Optional OpenAI judge provider contract exists, but no live provider call is
  enabled by default.
- Human review has append-only file-backed entries and decisions; richer
  operator workflow is still future work.
- No dashboard, hosted service, continuous eval, or production platform claim is
  made.

## Roadmap

The next stage moves from synthetic proof to real local integration:

1. README and evidence packaging.
2. gdev-agent triage dataset.
3. gdev-agent output normalizer.
4. real gdev-agent HTTP adapter.
5. gdev-agent deterministic validators.
6. `dataset-inspect`, `run-gdev-agent`, and `compare` CLI commands.
7. gdev-agent baseline report.
8. mocked CI smoke for the gdev adapter.
9. cost rollup and budget check.
10. final evidence pack.

The task queue is tracked in [docs/tasks.md](docs/tasks.md).
