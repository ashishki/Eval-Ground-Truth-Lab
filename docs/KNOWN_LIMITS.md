# Known Limits

Eval Ground Truth Lab is a local-first regression evaluation framework, not a
production eval platform.

- The committed gdev-agent baseline is synthetic/local deterministic live local
  evidence, not production traffic evidence.
- Reproducing live gdev-agent validation requires an operator-run local
  gdev-agent stack.
- A live gdev-agent probe on 2026-06-12 first exposed upstream `/webhook`
  runtime failures in `gdev-agent` and an Eval Lab transport-disconnect
  handling gap. After `gdev-agent` commit `901292d` and Eval Lab commit
  `8b052f2`, the local live path reaches `/health`, `/auth/token`, `make demo`,
  and all 55 eval cases with zero adapter errors.
- After `gdev-agent` commit `1db09d3`, the canonical live local run
  `gdev-baseline-v1` covers all 55 cases with zero adapter errors and zero
  deterministic validator failures.
- The committed baseline run is full-dataset synthetic/local evidence, not a
  production quality score.
- Runtime Grid live-local proof is an operator-run local HTTP path in the
  runtime repository; it is not a hosted eval scheduler or production traffic
  claim.
- The 55-case gdev-agent baseline is a curated integration/conformance set. It
  is not a hard challenge set and does not hide the need for ambiguous,
  expected-failure, and policy-stress eval cases.
- The committed `reports/gdev-agent/challenge_report.md` is a static
  dataset/scope report. The separate v0.2.0 package is a completed canonical
  local run against exact `gdev-agent` revision `0e4c5f0`; its gate fails five
  thresholds and does not approve that workload for release.
- The 100-case challenge is public, self-authored development data with zero
  independent annotators or external workflow owners. It is not blind,
  expert-labeled, or evidence of generalization. Tuning a candidate against its
  text contaminates the set for those claims.
- Built-in live gdev HTTP runs scope `request_id` and `message_id` by a
  deterministic run/candidate/component/dataset namespace, preventing stale
  Redis dedup responses from crossing eval runs. This does not clear Redis,
  validate arbitrary custom adapters, or replace gdev-agent's configured dedup
  TTL and operational lifecycle controls.
- The Trader Risk Audit adapter replays one pinned, sanitized, fully synthetic
  export from a separate path-purged publication candidate. It does not invoke
  the Trader rule engine or inspect raw trades. Its PASS is contract-compatibility
  evidence, not a financial-quality score, external case study, or user proof.
- Trader source commit/tree/blob and protected bundle digest are pinned. The
  adapter verifies the fixture SHA-256, Git blob, and evidence content hash, but
  local hashes do not authenticate the publisher and the protected bundle is not
  distributed by Eval Lab.
- Demo-mode local cost telemetry is deterministic and reports `0.0000` cost per
  case; it is not billing reconciliation.
- The optional OpenAI judge provider is disabled by default and tested with fake
  transport only.
- Live judge cost gates require telemetry rollup output and an approved budget
  policy.
- Human review is file-backed and auditable, but there is no multi-user review
  workflow or dashboard. `human_review_required` is a reference label, not proof
  that a human reviewed each challenge output.
- Static HTML is derivative; markdown reports and JSON run artifacts remain
  canonical.
- Local checksums and content addresses make evidence tamper-evident; they do
  not make a filesystem immutable or authenticate the publisher.
- There is no hosted service, production deployment, continuous eval scheduler,
  Kubernetes path, dashboard, or production SaaS claim.
