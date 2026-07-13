# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:05b2f18a78f5961f60d232d9626a471805123f78e4e46120db9c40111e2bd627`.

The pack includes the exact dataset, sanitized source export, provenance pins,
offline Git-object identity proof, machine-readable result, rendered decision,
checksum-sealed run, and verifier manifest. The eight artifacts are the exact
immutable snapshots used for validation plus their decision receipts. Packaged
source trust requires byte identity and the proof's commit-to-tree-to-path-to-
blob chain. The run JSON and seal are the locked completion snapshot; their
hashes and run identity match the result and manifest. Implementation provenance
binds all decision modules, the complete package payload, and clean Eval commit
`56de400bd4e157f70cf1538fbc464b9dbc00257b` / tree
`1b265941e195f053915caa27089f1dd484b3a2c7`. It represents a fully synthetic
contract compatibility fixture, not an external-user case,
financial-performance evaluation, or production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
