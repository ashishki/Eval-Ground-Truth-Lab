# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:094e482f281ca67ec3c47998e7101121e594732182d0b00bc165b9d158ed9b44`.

The pack includes the exact dataset, sanitized source export, provenance pins,
machine-readable result, rendered decision, checksum-sealed run, and verifier
manifest. Inputs are the exact immutable snapshots used for validation and all
sealed-result fields are pinned by the one-case expectation. The run JSON and
seal are the locked completion snapshot; their hashes and run identity match the
result and manifest. Implementation provenance binds all decision modules, the
complete package payload, and clean Eval commit
`64f57f3e037589741df236cf51e9742871a68a91` / tree
`e743f3d52438eec55c9c4b043cde7fddce081dd7`. It represents a fully synthetic
contract compatibility fixture, not an external-user case,
financial-performance evaluation, or production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
