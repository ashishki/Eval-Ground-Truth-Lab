# Trader Risk Audit adapter review-fix verification

Date: 2026-07-13

Scope: draft Trader Risk Audit adapter PR review blockers

Implementation commit: `56de400bd4e157f70cf1538fbc464b9dbc00257b`

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
- Evidence/provenance privacy, pin, and source-review claims require byte
  identity with both packaged resources. A fully re-self-hashed caller payload
  retaining canonical case/commit/tree/path ids remains unreviewed, is not an
  overall fixture, and receives a caller-evidence candidate identity.
- A packaged offline Git-object proof independently recomputes and binds the
  source commit, root tree, repository path, and evidence blob. The proof also
  binds the protected source bundle SHA-256 already recorded in provenance.
- The wheel contains all four default Trader replay resources. CLI defaults use
  package resources instead of checkout-relative paths.
- Manifest provenance covers the parser, RunStore, manifest writer, adapter,
  runner, validators, and complete package payload. Canonical evidence records a
  clean exact Eval commit/tree; an installed wheel records its artifact digest.
- `git_worktree` implementation provenance now requires every measured package
  file to be a blob at repository HEAD. Ignored/untracked installed packages
  inside unrelated repositories report `installed_package` and payload digest.
- CI has read-only repository contents permission, a 20-minute timeout, and two
  cache-disabled builds using commit-derived `SOURCE_DATE_EPOCH`; unequal wheel
  bytes fail the job.

## Local verification

| Check | Result |
|---|---|
| Focused Trader/source/implementation suite | `30 passed` |
| Full test suite | `213 passed` |
| Ruff format check | `99 files already formatted` |
| Ruff lint | `All checks passed` |
| Mutation between validation and packaging | PASS; packaged inputs equal the original snapshots |
| Mutation after RunStore completion | PASS; packaged run/seal equal the locked snapshot, not mutated paths |
| Repeated invocation identity/mutation isolation | PASS |
| Unknown nested-field matrix | PASS for evidence, candidate, checks, boundary, metrics, artifact, and trace fields |
| Empty/two-case no-pack guard | PASS |
| Raw-trades/secret-metadata/nested payload probes | rejected; no run/evidence directories |
| Recursive duplicate JSON/YAML probes | rejected with `DatasetValidationError`; no output directories |
| Re-self-hashed caller evidence with canonical source ids | FAIL gate; unreviewed/untrusted report; no pinned/sanitized/verified claim |
| Ignored installed package inside unrelated Git repo | `installed_package`; payload digest present |
| Source identity commit/tree/path/blob mutation matrix | all rejected |
| Installed-wheel console replay from unrelated cwd | PASS; 8-artifact manifest verified |
| Two clean commit-epoch wheel builds | byte-identical |
| Canonical input byte comparison | PASS |
| Canonical symlink, workstation-path, and secret-marker scan | clean |

The wheel built twice from a clean archive of the implementation commit is
`eval_ground_truth_lab-0.2.0-py3-none-any.whl`, SHA-256
`2d79198673c73906449d42827056c15f4c3ccf7a068d6857631ff6053a370fca`.
Archive inspection found the HTML report template and the four Trader replay
resource files. The installed console replay used no explicit input paths.
The second clean build produced the same SHA-256. Its installed package payload
digest is `158a342742b0522f53c802cf8286508844e5fcfabbf8c84af5e87e5f3437ff9b`.

## Canonical evidence

The regenerated pack is
`docs/evidence/integrations/trader-risk-audit-synthetic-v1/`.

- Gate: PASS for the single authored synthetic compatibility case.
- Validators: 11/11 pass.
- Artifacts: 8/8 verify, including the exact source-identity proof.
- Content address:
  `sha256:05b2f18a78f5961f60d232d9626a471805123f78e4e46120db9c40111e2bd627`.
- Manifest file SHA-256:
  `91e998ba605d608ed96a5781154d8768296e6e7389494e2625fafcaddce2cbe5`.
- Replay result SHA-256:
  `81d5580c35d1269b446264c0cbbb2ce637ea96fd7e2a2960a3f069e9af36c1aa`.
- Sealed run JSON SHA-256:
  `1d2d0f1ee92a2c9f1260bd453c01a6c846cd30b0f821312dbaf235942e70af4d`.
- Seal file SHA-256:
  `021ce91b0766add695568dd621678924f2d32fcd322a1664601f9b42d5f90d61`.
- Eval implementation commit/tree/worktree:
  `56de400bd4e157f70cf1538fbc464b9dbc00257b` /
  `1b265941e195f053915caa27089f1dd484b3a2c7` / clean.

This evidence remains a self-authored synthetic contract replay. It is not a
financial-performance result, external-user case study, production run, or
publisher-authentication claim. GitHub-hosted CI status is recorded separately
after the branch is pushed.
