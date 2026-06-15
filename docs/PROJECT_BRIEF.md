# Project Brief - Eval Ground Truth Lab

Source: `/home/ashishki/Downloads/PROJECT_BRIEF_eval_ground_truth_lab.md`
Imported: 2026-06-11

## Summary

Eval Ground Truth Lab is a regression-evaluation platform for LLM and agent
workflows. It provides versioned datasets, baseline and candidate runs,
deterministic validators, optional calibrated LLM judging, human review, CI
gates, and a failure taxonomy.

## Problem Fit

Prompt, model, adapter, or guardrail changes can silently reduce quality,
increase unsafe auto-approval, increase cost, or worsen latency. Current
workarounds rely on small pytest sets, manual prompt checks, ad hoc spreadsheets,
one-off eval scripts, and subjective sample review.

The first operator maintains gdev-agent and other LLM workflows. A secondary
reader is an AI platform operator or eval maintainer checking whether the project
demonstrates rigorous evaluation infrastructure.

## V1 Success

An operator can run evals against gdev-agent or a demo candidate, compare baseline
and candidate behavior, see pass/fail decisions, inspect failure categories, and
verify that seeded unsafe regressions fail CI.

Adoption proof for v1:

- Add at least 100 eval cases for gdev-agent-like workflows.
- Seed at least 5 known regressions.
- Show CI failure for unsafe regression, invalid structured output, excessive
  cost increase, and material accuracy drop.

## Scope

In scope for v1:

- Dataset schema and dataset versioning by file/hash.
- Baseline and candidate run storage.
- Deterministic validators and threshold gates.
- Optional LLM judge with budget caps and human review boundaries.
- Human review queue for ambiguous cases.
- Markdown and HTML reports.
- gdev-agent adapter and synthetic demo adapter.
- CI command for smoke and regression evals.

Out of scope for v1:

- Enterprise eval SaaS.
- Large labeling workforce.
- Model training or RLHF.
- Universal benchmark claims.
- Fully automated safety certification.

## AI Boundaries

AI may assist with optional subjective judging, explanation clustering, failure
summaries, and suggested taxonomy labels.

AI must not own dataset identity/versioning, schema validation, deterministic
pass/fail checks, cost/latency calculations, CI threshold enforcement, or audit
log writes.

Human ownership remains required for rubric design, ground-truth creation, final
adjudication for ambiguous cases, risk thresholds, and acceptance of production
changes.
