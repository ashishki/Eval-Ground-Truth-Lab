# Integration evidence

## Current Trader Risk Audit synthetic replay v2

[`trader-risk-audit-synthetic-v2/`](trader-risk-audit-synthetic-v2/) is the
current Eval Lab v0.2.1 execution of the packaged Trader compatibility fixture.
The one-case gate is PASS and its verified content address is
`sha256:b8269aa9b416f78817a0c69848c6a4bd24957f7016e2d1c4951dee9cb7430496`.

The pack was generated on 2026-07-14 from exact Eval implementation commit
`31120c809cc4935c9f5ffbb2cb539a3018d38d92`, tree
`8cbbff195bbae0ee5309d94c38ad27e8215c755e`, and loaded-code binding
`423d9bc2bf89438b147485f88b4b251b6c872d62b00fea998c97904828da15b3`.
Its eight artifacts contain the exact dataset, sanitized source export,
provenance pins, offline commit/tree/path/blob proof, machine-readable result,
rendered decision, and checksum-sealed run.

This directory is an immutable captured execution. A semantic replay from the
same package is expected to retain the fixture identity and PASS boundary, but
RunStore start/completion timestamps intentionally make a fresh replay a new
capture with a different byte address; no byte-identical regeneration claim is
made for the Trader pack.

“v2” identifies this second immutable integration evidence execution; it does
not claim a Trader contract v2 or new source dataset. The replay still uses the
unchanged fully synthetic v1 fixture and Trader package `0.2.0`. It is local
contract-compatibility evidence, not an external-user case, financial-quality
evaluation, external-feedback maintenance signal, or production run.

## Historical replay v1

[`trader-risk-audit-synthetic-v1/`](trader-risk-audit-synthetic-v1/) remains the
byte-preserved 2026-07-13 replay for its recorded implementation. Its verified
content address is
`sha256:1b228a37ea3686cc9c57132c7b2d2048a49c71995fd63b4d020d619bf30f72c3`.
It records Eval commit `f810e3a7a9ef6c077371ef401c345f56da3c8c27`, tree
`8da573207b40329f125a999165163b73f4b0e8c0`, and loaded-code binding
`33c0e48b7eff1fcd4656418cbb75491d408d16f01bdea1860c818997893cc5b6`.
It is historical evidence and is not relabeled as a v0.2.1 execution.

Reproduction and interpretation boundaries are documented in
[`../../TRADER_RISK_AUDIT_ADAPTER.md`](../../TRADER_RISK_AUDIT_ADAPTER.md).
