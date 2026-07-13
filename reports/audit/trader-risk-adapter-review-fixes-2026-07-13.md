# Trader Risk Audit adapter review-fix verification

Date: 2026-07-13

Scope: draft Trader Risk Audit adapter PR review blockers

Implementation commit: `64f57f3e037589741df236cf51e9742871a68a91`

## Implemented controls

- Adapter results are rebuilt from an immutable evidence-byte snapshot on every
  invocation; nested evidence containers are not shared between results.
- Expected data and validators cover the complete sealed adapter output,
  including evaluation boundary, artifact receipts, trace preview, source path,
  and provenance-file SHA-256. Unknown nested fields fail structured validation.
- Dataset, evidence, and provenance inputs are read once. Parsing, validation,
  hashing, replay, and packaged inputs derive from those exact byte snapshots.
- RunStore completion returns immutable terminal JSON/seal bytes created under
  the run lock. Replay packaging never reopens the mutable run-store paths.
- Packaged run hashes and run id/candidate/dataset/validator/completed status are
  cross-bound in replay result and manifest.
- Replay v1 requires exactly one case. Empty and two-case inputs fail before a
  run directory or evidence pack is created.
- Dataset cases allow only `id`, `input`, `expected`, and `metadata`; Trader
  id/input and trusted metadata schema/values are exact. Unknown/nested payloads
  and recursive duplicate JSON/YAML keys fail before output creation.
- Fixture/privacy classification requires canonical-name byte identity with the
  packaged dataset. Caller-supplied schema-valid overrides are marked
  non-fixture and not privacy-reviewed.
- The wheel contains all three default Trader replay resources. CLI defaults use
  package resources instead of checkout-relative paths.
- Manifest provenance covers the parser, RunStore, manifest writer, adapter,
  runner, validators, and complete package payload. Canonical evidence records a
  clean exact Eval commit/tree; an installed wheel records its artifact digest.
- CI has read-only repository contents permission, a 20-minute timeout, and two
  cache-disabled builds using commit-derived `SOURCE_DATE_EPOCH`; unequal wheel
  bytes fail the job.

## Local verification

| Check | Result |
|---|---|
| Focused security/runtime suite | `56 passed` |
| Full test suite | `206 passed` |
| Ruff format check | `97 files already formatted` |
| Ruff lint | `All checks passed` |
| Mutation between validation and packaging | PASS; packaged inputs equal the original snapshots |
| Mutation after RunStore completion | PASS; packaged run/seal equal the locked snapshot, not mutated paths |
| Repeated invocation identity/mutation isolation | PASS |
| Unknown nested-field matrix | PASS for evidence, candidate, checks, boundary, metrics, artifact, and trace fields |
| Empty/two-case no-pack guard | PASS |
| Raw-trades/secret-metadata/nested payload probes | rejected; no run/evidence directories |
| Recursive duplicate JSON/YAML probes | rejected with `DatasetValidationError`; no output directories |
| Installed-wheel console replay from unrelated cwd | PASS; 7-artifact manifest verified |
| Two clean commit-epoch wheel builds | byte-identical |
| Canonical input byte comparison | PASS |
| Canonical symlink, workstation-path, and secret-marker scan | clean |

The locally built wheel is
`eval_ground_truth_lab-0.2.0-py3-none-any.whl`, SHA-256
`ef6c2df5ff84d24bc15072b0d8a0b3667d32b8abac1038361848eabde74ff5d0`.
Archive inspection found the HTML report template and the three Trader replay
resource files. The installed console replay used no explicit input paths.
The second clean build produced the same SHA-256. Its installed package payload
digest is `e70f0b82b295d501e1eb83b195ab6e0d267f69ab3b046d4455d34413c1a8263d`.

## Canonical evidence

The regenerated pack is
`docs/evidence/integrations/trader-risk-audit-synthetic-v1/`.

- Gate: PASS for the single authored synthetic compatibility case.
- Validators: 11/11 pass.
- Artifacts: 7/7 verify.
- Content address:
  `sha256:094e482f281ca67ec3c47998e7101121e594732182d0b00bc165b9d158ed9b44`.
- Manifest file SHA-256:
  `93777b0358c55cde85d265ced80d91a0a51a7c15286e4b7f95b50e5c75b421de`.
- Replay result SHA-256:
  `6b5814c1987359dce82f7cdc90b0d85b97c1a1abe882ceab9f33d4ac948f7f68`.
- Sealed run JSON SHA-256:
  `4bf8f6d8fcc9320f596cf0ab0465986124290d78e044efd1018032eb2c4b1477`.
- Seal file SHA-256:
  `80e35f5d02e8faeff3416935947e92a235f608c3645d471f6d04e2179e39fbff`.
- Eval implementation commit/tree/worktree:
  `64f57f3e037589741df236cf51e9742871a68a91` /
  `e743f3d52438eec55c9c4b043cde7fddce081dd7` / clean.

This evidence remains a self-authored synthetic contract replay. It is not a
financial-performance result, external-user case study, production run, or
publisher-authentication claim. GitHub-hosted CI status is recorded separately
after the branch is pushed.
