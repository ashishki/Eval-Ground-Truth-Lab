# Trader Risk Audit adapter review-fix verification

Date: 2026-07-13

Scope: draft Trader Risk Audit adapter PR review blockers

Implementation commit: `23b26cb9401aad7c8ecec1b1bfb66f8a4c373248`

## Implemented controls

- Adapter results are rebuilt from an immutable evidence-byte snapshot on every
  invocation; nested evidence containers are not shared between results.
- Expected data and validators cover the complete sealed adapter output,
  including evaluation boundary, artifact receipts, trace preview, source path,
  and provenance-file SHA-256. Unknown nested fields fail structured validation.
- Dataset, evidence, and provenance inputs are read once. Parsing, validation,
  hashing, replay, and packaged inputs derive from those exact byte snapshots.
- Replay v1 requires exactly one case. Empty and two-case inputs fail before a
  run directory or evidence pack is created.
- The wheel contains all three default Trader replay resources. CLI defaults use
  package resources instead of checkout-relative paths.

## Local verification

| Check | Result |
|---|---|
| Focused adapter/dataset/validator/replay tests | `32 passed` |
| Full test suite | `190 passed` |
| Ruff format check | `95 files already formatted` |
| Ruff lint | `All checks passed` |
| Mutation between validation and packaging | PASS; packaged inputs equal the original snapshots |
| Repeated invocation identity/mutation isolation | PASS |
| Unknown nested-field matrix | PASS for evidence, candidate, checks, boundary, metrics, artifact, and trace fields |
| Empty/two-case no-pack guard | PASS |
| Installed-wheel console replay from unrelated cwd | PASS; 7-artifact manifest verified |
| Canonical input byte comparison | PASS |
| Canonical symlink, workstation-path, and secret-marker scan | clean |

The locally built wheel is
`eval_ground_truth_lab-0.2.0-py3-none-any.whl`, SHA-256
`89d846a965e69e7e028c9e3e2d8d568cac3afe911c52b2ce7dad3dbd38cf90a6`.
Archive inspection found the HTML report template and the three Trader replay
resource files. The installed console replay used no explicit input paths.

## Canonical evidence

The regenerated pack is
`docs/evidence/integrations/trader-risk-audit-synthetic-v1/`.

- Gate: PASS for the single authored synthetic compatibility case.
- Validators: 11/11 pass.
- Artifacts: 7/7 verify.
- Content address:
  `sha256:c57f858899962179179109d33e165f0c8fbc3744c3cfaaffaea27e9179a0dd63`.
- Manifest file SHA-256:
  `a33436d438858b49f45692418d8360cd1d3ea24deba91ca3e95dea7fd1e20dcc`.
- Replay result SHA-256:
  `d807c087a440302644f57082b3e6b06b35b58ec82162a1c275e18f063e5c57be`.
- Sealed run JSON SHA-256:
  `e77d9b8a9ed86752cd6d2d443a3e9b0b6cfdeb07bc4241c33aeeb0bf71f401dd`.

This evidence remains a self-authored synthetic contract replay. It is not a
financial-performance result, external-user case study, production run, or
publisher-authentication claim. GitHub-hosted CI status is recorded separately
after the branch is pushed.
