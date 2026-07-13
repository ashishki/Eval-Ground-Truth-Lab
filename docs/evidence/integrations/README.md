# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:e450c9a7561f88f8f90ce1464457d8ddb18435ce105451a9dbb8ab6e64c4d5fb`.

The pack includes the exact dataset, sanitized source export, provenance pins,
offline Git-object identity proof, machine-readable result, rendered decision,
checksum-sealed run, and verifier manifest. The eight artifacts are the exact
immutable snapshots used for validation plus their decision receipts. Packaged
source trust requires byte identity and the proof's commit-to-tree-to-path-to-
blob chain. The run JSON and seal are the locked completion snapshot; their
hashes and run identity match the result and manifest. The sealed output keeps
caller/source metadata under `declared_*` and records independently derived
`effective_trust`; validator messages refer only to the selected expectation.
Implementation provenance binds all decision modules, the complete package
payload, and its exact recursive bytes/modes match at Eval commit
`0860ae64d282c3697c16f59d43b376e8557be108` / tree
`d79cff41a04acecc1d638d311f195fd5df9af248`. It does not claim the whole
worktree was clean. The pack represents a fully synthetic contract compatibility
fixture, not an external-user case, financial-performance evaluation, or
production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
