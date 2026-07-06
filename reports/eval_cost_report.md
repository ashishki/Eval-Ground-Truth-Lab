# Eval Cost Report

Status: starter artifact
Scope: local deterministic eval plus optional judge path

## Cost Surfaces

| Surface | Current state | Evidence |
|---------|---------------|----------|
| Deterministic validators | Zero model spend | tests and local CLI |
| Candidate runs | Cost recorded per case when supplied by adapter | `RunRecord.cost_*` fields |
| Optional judge | Disabled by default, budget prechecked | `docs/JUDGE_CALIBRATION.md`, judging tests |
| Human review | Append-only review notes exist | `docs/HUMAN_REVIEW.md` |
| Reports | Markdown/HTML generated locally | `reports/` |

## Required Rollups

Future live judge or provider-backed runs should publish:

- total eval inference cost
- judge cost
- cost per case
- cost per successful task
- p95 latency
- retry count
- quality outcome distribution
- human review minutes when available

## Current Decision

The default project posture remains deterministic-first. Judge output is
optional, budgeted, and non-authoritative until calibrated against human labels.

