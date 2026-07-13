# CLI

Eval Ground Truth Lab is CLI-first. Commands write local artifacts and use
deterministic validators by default.

## Commands

```bash
python -m eval_ground_truth_lab.cli --help
python -m eval_ground_truth_lab.cli seeded-smoke --help
python -m eval_ground_truth_lab.cli dataset-inspect --help
python -m eval_ground_truth_lab.cli run-gdev-agent --help
python -m eval_ground_truth_lab.cli run-gdev-agent-challenge --help
python -m eval_ground_truth_lab.cli verify-evidence --help
python -m eval_ground_truth_lab.cli compare --help
python -m eval_ground_truth_lab.cli cost-rollup --help
python -m eval_ground_truth_lab.cli budget-check --help
```

## Dataset Inspect

```bash
python -m eval_ground_truth_lab.cli dataset-inspect \
  --dataset datasets/gdev_agent/triage_v1.jsonl
```

Prints dataset ID, schema version, case count, and dataset hash.

## Run gdev-agent

```bash
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-baseline-v1 \
  --candidate-version gdev-agent-demo \
  --component-revision <full-gdev-git-sha> \
  --report reports/gdev-agent/baseline_report.md
```

The command writes a run artifact under `runs/` by default and writes a markdown
report at the requested path. It uses `GDEV_AGENT_*` environment variables for
tenant and webhook configuration unless a caller injects an adapter in code.
Terminal runs also have a `.sha256` seal; this detects accidental/tampering
changes but is not a filesystem immutability guarantee.
`--component-revision` must be a full 40- or 64-character revision (or an
explicit `fixture:` identity in tests). Together with the run ID, candidate
version, and dataset hash, it produces the deterministic namespace applied to
live HTTP `request_id` and `message_id` values.

## Run gdev-agent Challenge

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
```

The command evaluates 90 candidate-facing cases and injects ten declared
provider faults in the harness. It writes machine-readable JSON first, renders
Markdown only from that JSON object, copies the terminal run/seal, and writes a
content-addressed manifest last. Every declared challenge threshold affects the
gate; failed gates exit `1` without deleting the evidence.
Challenge JSON and manifest metadata both record the request namespace,
namespace inputs, and whether a real gdev HTTP adapter or a custom passthrough
adapter handled the cases.
Keep `--run-dir` outside `--evidence-dir`: the command copies the sealed terminal
run into the evidence directory's own `run/` subdirectory during finalization.

## Verify Evidence

```bash
eval-ground-truth-lab verify-evidence \
  --manifest /tmp/gdev-challenge-evidence/sha256-*.manifest.json
```

Verification fails for a changed or deleted artifact, manifest/content-address
mismatch, symlink, or an undeclared added file.

## Compare

```bash
python -m eval_ground_truth_lab.cli compare \
  --baseline runs/gdev-baseline-v1.json \
  --candidate runs/gdev-candidate-v2.json \
  --threshold-config datasets/gdev_agent/thresholds.json \
  --report reports/gdev-agent/comparison_report.md
```

The command exits `1` when comparison thresholds have a blocking failure.

## Cost Rollup

```bash
python -m eval_ground_truth_lab.cli cost-rollup \
  --telemetry docs/ai_cost_telemetry.jsonl \
  --out reports/cost/latest.json
```

The command reads provider-agnostic JSONL telemetry and writes a deterministic
rollup with total cost, total tokens, cost by model/workflow/case, p95 latency,
retry count, judge call count, and quality outcome distribution.

## Budget Check

```bash
python -m eval_ground_truth_lab.cli budget-check \
  --rollup reports/cost/latest.json \
  --policy docs/cost_policy.json
```

The command exits `1` when the rollup exceeds `per_run_budget_usd`,
`monthly_project_budget_usd`, `cost_per_case_ceiling`, or
`judge_call_count_ceiling`. CI should use fixture telemetry by default. Live
judge cost gates require telemetry rollup artifacts and an approved budget
policy before they are enforced.
