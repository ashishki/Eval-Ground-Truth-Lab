# Integration evidence

## Trader Risk Audit synthetic sanitized-export replay

The directory
[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) contains the
exact one-case replay generated on 2026-07-13. Its gate is PASS and its verified
content address is
`sha256:1b228a37ea3686cc9c57132c7b2d2048a49c71995fd63b4d020d619bf30f72c3`.

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
`f810e3a7a9ef6c077371ef401c345f56da3c8c27` / tree
`8da573207b40329f125a999165163b73f4b0e8c0`. Its package-wide loaded-code
binding is
`33c0e48b7eff1fcd4656418cbb75491d408d16f01bdea1860c818997893cc5b6`.
It does not claim the whole worktree was clean. The pack represents a fully
synthetic contract compatibility
fixture, not an external-user case, financial-performance evaluation, or
production run.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
