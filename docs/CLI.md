# CLI

Eval Ground Truth Lab is CLI-first. Commands write local artifacts and use
deterministic validators by default.

## Commands

```bash
python -m eval_ground_truth_lab.cli --help
python -m eval_ground_truth_lab.cli seeded-smoke --help
python -m eval_ground_truth_lab.cli dataset-inspect --help
python -m eval_ground_truth_lab.cli run-gdev-agent --help
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
  --report reports/gdev-agent/baseline_report.md
```

The command writes a run artifact under `runs/` by default and writes a markdown
report at the requested path. It uses `GDEV_AGENT_*` environment variables for
tenant and webhook configuration unless a caller injects an adapter in code.

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
