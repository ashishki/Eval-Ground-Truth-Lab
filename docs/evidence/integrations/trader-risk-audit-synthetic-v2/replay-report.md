# Trader Risk Audit sanitized evidence replay

Gate: **PASS**

This is a deterministic compatibility replay of one fully synthetic expectation dataset distributed with Eval Lab.
The source evidence is the byte-identical packaged export. Its Git identity is bound by the packaged commit-to-tree-to-path-to-blob proof. It is not a financial-performance evaluation, live-data audit, external-user case study, investment recommendation, or production claim.

## Source pins

- Trader package: `trader-risk-audit` / `0.2.0`
- Export contract: `trader-risk-audit-evidence-v1`
- Source commit: `bf755a24450ff7c17328fa6d447f36bea8ea0fe5`
- Source tree: `1a2c4ff91a7504642a1bae05a9487fa2e898e0b6`
- Source path: `examples/synthetic_quickstart/evidence_preview/eval-evidence.json`
- Source blob: `9a64dc98e8edbe1ec39756611a6cb3b73b4994b9`
- Source bundle SHA-256: `2c5b36afa9b2a9847de1c97789c52c57600e1d38cfd4947458906ee3bb3992ca`
- Evidence SHA-256: `9925144d39bd41d6fdf8f54a1bbd900c871f1bb73cd008980baa2ae1f2d51ced`
- Evidence content hash: `d7e6fe92f50ba410a2c23882ea617b38081a8bbe84fe66727dfaecca115eb63f`
- Privacy classification: `fully-synthetic-sanitized-export`

## Eval run

- Run ID: `trader-synthetic-quickstart-v2-20260714`
- Candidate version: `trader-risk-audit-0.2.0@bf755a24450f`
- Dataset: `synthetic_quickstart_v1` / `df201d0787c6ea31868f7f6465a2fb9895b6f14b78cb01e13e0f9ff244e5b67a`
- Dataset cases: `1`
- Dataset fixture: `True`
- Dataset privacy classification: `fully-synthetic-packaged-expectation-dataset`
- Validator: `trader-risk-audit-exact-replay-validators-v1`
- Run status: `completed`

## Case decisions

| Case | Status | Failed validators |
|---|---|---|
| `synthetic-quickstart-v1` | `pass` | `none` |

## Decision boundary

PASS means the pinned sanitized export matches this self-authored synthetic dataset and its exact contract expectations. It does not validate suitable risk thresholds, investment outcomes, raw-source correctness, publisher authenticity, external adoption, or general workflow quality.
