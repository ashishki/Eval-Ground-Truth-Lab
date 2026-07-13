# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:c57f858899962179179109d33e165f0c8fbc3744c3cfaaffaea27e9179a0dd63`.

The pack includes the exact dataset, sanitized source export, provenance pins,
machine-readable result, rendered decision, checksum-sealed run, and verifier
manifest. Inputs are the exact immutable snapshots used for validation and all
sealed-result fields are pinned by the one-case expectation. It represents a
fully synthetic contract compatibility fixture, not
an external-user case, financial-performance evaluation, or production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
