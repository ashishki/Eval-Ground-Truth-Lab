# gdev-agent Live Probe Summary

Date: 2026-06-12

## Scope

This is a concise record of the local live integration probe. It is not the
canonical passing baseline. The canonical committed baseline remains
`reports/gdev-agent/baseline_report.md` and
`reports/gdev-agent/baseline_run.json`.

## Versions

| Component | Version |
|-----------|---------|
| Eval Lab | `8b052f2` |
| gdev-agent | `901292d` |
| Dataset | `datasets/gdev_agent/triage_v1.jsonl` |
| Dataset hash | `ee4e0d237d43f16a815dcad2f7ff57ebb30404bf39a337d1e74aeeb53befffeb` |

## Commands Exercised

```bash
cd ~/Documents/dev/ai-stack/projects/gdev-agent
LLM_MODE=demo docker-compose build migrate agent
make demo
```

Result: passed locally against an isolated Docker network with the API running
as the `gdev_app` role.

```bash
cd ~/Documents/dev/ai-stack/projects/Eval-Ground-Truth-Lab
python -m eval_ground_truth_lab.cli run-gdev-agent \
  --dataset datasets/gdev_agent/triage_v1.jsonl \
  --base-url http://localhost:8000 \
  --run-id gdev-live-after-upstream-fix-20260612 \
  --report /tmp/gdev-live-after-upstream-fix-report.md
```

Result: exited `1` from deterministic validator failures, not adapter/runtime
errors.

## Observed Eval Result

| Metric | Value |
|--------|-------|
| Case count | 55 |
| Adapter errors | 0 |
| Status distribution | `executed`: 46, `pending`: 8, `blocked`: 1 |
| Top failure: wrong routing | 74 |
| Top failure: cost regression | 55 |
| Top failure: wrong category | 52 |
| Top failure: unsafe auto-approval | 36 |
| Top failure: guard expected but not triggered | 19 |

## Interpretation

Eval Lab now reaches the real gdev-agent HTTP system and receives structured
outputs for every case. The remaining non-zero exit is a product-quality signal:
the deterministic demo classifier/routing behavior and cost output do not yet
match the gdev-agent eval dataset expectations.

## Next Gap

Improve or explicitly version the gdev-agent demo policy so it aligns with the
eval dataset for category, human-routing, guard behavior, unsafe auto-approval,
and cost-per-case output. Then regenerate a canonical live baseline report.
