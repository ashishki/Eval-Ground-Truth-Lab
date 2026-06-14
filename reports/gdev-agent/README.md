# gdev-agent Evidence Artifacts

This directory contains the committed `gdev-agent` live local baseline evidence
for Eval Ground Truth Lab.

- `baseline_run.json` is the canonical run artifact.
- `baseline_report.md` is the readable report derived from that run artifact.

The data is synthetic/local deterministic and is not a production quality claim.
The current canonical baseline covers all 55 triage cases against a locally
running `gdev-agent` in `LLM_MODE=demo` with zero adapter errors and zero
deterministic validator failures.
