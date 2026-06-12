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
