# Known Limits

Eval Ground Truth Lab is a local-first regression evaluation framework, not a
production eval platform.

- The committed gdev-agent baseline is synthetic/local deterministic evidence.
- Live gdev-agent validation requires an operator-run local gdev-agent stack.
- The committed baseline run is compact representative evidence, not a full
  production quality score.
- The optional OpenAI judge provider is disabled by default and tested with fake
  transport only.
- Live judge cost gates require telemetry rollup output and an approved budget
  policy.
- Human review is file-backed and auditable, but there is no multi-user review
  workflow or dashboard.
- Static HTML is derivative; markdown reports and JSON run artifacts remain
  canonical.
- There is no hosted service, production deployment, continuous eval scheduler,
  Kubernetes path, dashboard, or production SaaS claim.
