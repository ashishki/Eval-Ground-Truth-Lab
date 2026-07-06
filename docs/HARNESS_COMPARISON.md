# Harness Comparison

Eval Lab compares workflow outputs, but agentic systems need one more boundary:
the harness. A fair comparison records the model, prompt, tools, memory policy,
permissions, recovery policy, trace schema, environment, scorer, and budget that
wrapped the candidate.

## Metadata Contract

Use `eval_ground_truth_lab.harness.HarnessRunMetadata` as a sidecar record for a
run:

| Field | Meaning |
|-------|---------|
| `run_id` | Baseline or candidate run ID |
| `dataset_hash` | Dataset identity used by the run |
| `scorer_version` | Deterministic/judge scorer version |
| `budget_usd` | Budget boundary for this run |
| `harness` | Versioned `HarnessConfig` boundary |

`HarnessConfig` records:

- harness ID and version
- model class
- prompt version
- tool registry version
- memory policy version
- permission policy version
- recovery policy version
- trace schema version
- environment ID

## Trace Completeness

`TraceCompletenessValidator` checks whether required event types are present in
a run trace. Required events are set by the benchmark. A simple non-tool run may
require only `run_start`, `model_call`, and `run_end`; side-effecting agent
runs should also require permission, tool, retry/recovery, and human handoff
events where applicable.

## Comparison Rule

`build_harness_comparison_report` rejects comparisons when:

- baseline/candidate run IDs do not match the metric report
- dataset hashes do not match the metric report
- baseline and candidate scorer versions differ

The resulting report includes metric thresholds, harness versions, trace
completeness, and budget delta. This keeps model/prompt comparisons from hiding
tool, memory, permission, or environment drift.

