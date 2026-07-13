# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:ae5f4152cebd3c819f62b5facc09ff4c82f2dd9e9c3d1256b8b1c7b83d1eecd2`.

The pack includes the exact dataset, sanitized source export, provenance pins,
offline Git-object identity proof, machine-readable result, rendered decision,
checksum-sealed run, and verifier manifest. The eight artifacts are the exact
immutable snapshots used for validation plus their decision receipts. Packaged
source trust requires byte identity and the proof's commit-to-tree-to-path-to-
blob chain. The run JSON and seal are the locked completion snapshot; their
hashes and run identity match the result and manifest. The sealed output keeps
caller/source metadata under `declared_*` and records independently derived
`effective_trust`; validator messages refer only to the selected expectation.
The evidentiary path executes only its internally constructed canonical adapter.
Implementation provenance derives every named decision-module hash, complete
package payload, and HEAD comparison from one immutable recursive bytes/modes/path
snapshot at Eval commit
`c85d512cae53a2c20b994f2909c763695b8a5155` / tree
`52b64e4541d4f9d6e67fd4711f31c6293fc65358`. It does not claim the whole
worktree was clean. The pack represents a fully synthetic contract compatibility
fixture, not an external-user case, financial-performance evaluation, or
production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
