# Known Limits

Eval Ground Truth Lab is a local-first regression evaluation framework, not a
production eval platform.

- The committed gdev-agent baseline is synthetic/local deterministic evidence.
- Live gdev-agent validation requires an operator-run local gdev-agent stack.
- A live gdev-agent probe on 2026-06-12 first exposed upstream `/webhook`
  runtime failures in `gdev-agent` and an Eval Lab transport-disconnect
  handling gap. After `gdev-agent` commit `901292d` and Eval Lab commit
  `8b052f2`, the local live path reaches `/health`, `/auth/token`, `make demo`,
  and all 55 eval cases with zero adapter errors.
- The current live gdev-agent eval is still not a passing baseline. It exits
  `1` because deterministic validators find real quality/telemetry gaps:
  category/routing mismatches, unsafe auto-approval for expected-human cases,
  guard expectation mismatches, and missing per-case cost output.
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
