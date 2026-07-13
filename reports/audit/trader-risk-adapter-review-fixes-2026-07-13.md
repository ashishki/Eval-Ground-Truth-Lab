# Trader Risk Audit adapter review-fix verification

Date: 2026-07-13

Scope: draft Trader Risk Audit adapter PR review blockers

Implementation commit: `f810e3a7a9ef6c077371ef401c345f56da3c8c27`

Implementation tree: `8da573207b40329f125a999165163b73f4b0e8c0`

## High-severity review finding and disposition

The pre-fix exact head `4f95d48` could import the old canonical adapter, replace
and commit a newer on-disk adapter without reloading the process, and still
produce a passing replay whose implementation provenance described the newer
filesystem state. That demonstrated that measured files were not sufficient
evidence for the Python objects that actually made the decision.

The finding is closed fail-closed at the implementation commit above. A
generated package-wide execution digest is captured by every loaded Trader
decision module at import. Replay derives the same digest from one immutable
recursive package snapshot, validates the embedded marker, and compares every
loaded module before proof validation, dataset parsing, adapter invocation, run
creation, or evidence-pack creation. Package mutation without a marker refresh,
and old loaded modules against a correctly refreshed newer on-disk package, are
both regression-tested rejection paths.

## Implemented controls

- Adapter results are rebuilt from an immutable evidence-byte snapshot on every
  invocation; nested evidence containers are not shared between results.
- The evidentiary writer rejects every injected adapter, including exact-class
  instances and subclass overrides, before reading inputs or creating outputs.
  It constructs the canonical adapter only from the locked input snapshot; the
  input-mutation regression uses a private non-CLI callback with no snapshot or
  adapter authority.
- Direct adapter output preserves caller privacy/source values only as
  `declared_privacy_classification` and `declared_source`; its separate
  `effective_trust` block is fail-closed and unassessed.
- Replay derives effective trust from packaged byte identity and the offline
  Git-object proof before sealing RunStore output. Validator receipts label
  declarations explicitly and use neutral `selected expectation` messages.
- Expected data and validators cover the complete sealed adapter output,
  including evaluation boundary, artifact receipts, trace preview, source path,
  and provenance-file SHA-256. Unknown nested fields fail structured validation.
- Dataset, evidence, provenance, and trusted packaged evidence are read into
  immutable byte snapshots. Parsing, validation, hashing, replay, and packaged
  inputs derive from those exact bytes.
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
- Evidence/provenance privacy and source-review claims require byte identity
  with both packaged resources. A fully re-self-hashed caller payload retaining
  canonical case/commit/tree/path ids remains unreviewed, is not an overall
  fixture, and receives a caller-evidence candidate identity.
- A self-hashed modified export plus a matching caller expectation can PASS the
  compatibility gate, but direct output remains unassessed and the sealed run,
  result, manifest, report, replay type, and candidate identity remain explicitly
  caller-supplied and unreviewed.
- A packaged offline Git-object proof independently recomputes and binds the
  source commit, root tree, repository path, and evidence blob. The proof also
  binds the protected source bundle SHA-256 already recorded in provenance.
- The wheel contains all four default Trader replay resources. CLI defaults use
  package resources instead of checkout-relative paths.
- Manifest provenance schema v2 covers the adapter, adapter base, dataset
  parser, evidence writer, execution-binding module, implementation-provenance
  builder, RunStore, runner, source-identity verifier, validation-result type,
  Trader validators, and the complete package payload.
- `git_worktree` implementation provenance requires the exact recursive HEAD
  package path set, byte-for-byte Git blob identity, and executable-mode
  identity. `assume-unchanged`, `skip-worktree`, and hidden deletion probes all
  downgrade to `installed_package`; executable mode participates in the payload
  digest.
- Named component hashes, recursive package digest, Git blob ids, HEAD
  comparison, and the loaded-code digest derive from one immutable
  root-relative bytes/modes/paths snapshot. Components outside the package root
  are rejected; namespace or stat drift during capture fails closed.
- CI grants only `contents: read`, disables persisted checkout credentials, and
  pins checkout and setup-python to exact 40-character commits. It checks the
  generated execution binding and includes `tools/` in lint/format checks.
- CI has a 20-minute timeout and performs two cache-disabled wheel builds using
  commit-derived `SOURCE_DATE_EPOCH`; unequal wheel bytes fail the job.
- The clean-clone reviewer path bootstraps with `python3`, installs before any
  project module command, asserts the seeded gate's expected exit `1`, and
  verifies the committed eight-artifact Trader manifest.

## Local verification

| Check | Result |
|---|---|
| Focused Trader/source/implementation/docs-contract suite | `63 passed in 5.91s` |
| Full test suite | `229 passed in 23.00s` |
| Ruff format check | `102 files already formatted` |
| Ruff lint | `All checks passed` |
| Generated loaded-code binding check | PASS; `33c0e48b7eff1fcd4656418cbb75491d408d16f01bdea1860c818997893cc5b6` |
| Canonical evidence verifier | PASS; 8/8 artifacts at `sha256:1b228a37ea3686cc9c57132c7b2d2048a49c71995fd63b4d020d619bf30f72c3` |
| Old-loaded/new-on-disk implementation | rejected before run or evidence output |
| Package mutation without binding refresh | rejected with `ImplementationProvenanceError` |
| Mutation between validation and packaging | PASS; packaged inputs equal the original snapshots |
| Injected adapter/subclass override | rejected before input reads, invocation, run directory, or evidence pack |
| Mutation between implementation provenance phases | PASS; component, package, binding, and HEAD identities use one snapshot |
| Named component outside package root | rejected with `ImplementationProvenanceError` |
| Mutation after RunStore completion | PASS; packaged run/seal equal the locked snapshot, not mutated paths |
| Repeated invocation identity/mutation isolation | PASS |
| Unknown nested-field matrix | PASS for evidence, candidate, checks, boundary, metrics, artifact, and trace fields |
| Empty/two-case no-pack guard | PASS |
| Raw-trades/secret-metadata/nested payload probes | rejected; no run/evidence directories |
| Recursive duplicate JSON/YAML probes | rejected with `DatasetValidationError`; no output directories |
| Re-self-hashed caller evidence with canonical source ids | FAIL gate; unreviewed/untrusted report; no pinned/sanitized/verified claim |
| Re-self-hashed caller evidence plus matching caller dataset | PASS gate; direct and sealed output remain privacy-unreviewed/source-unauthenticated; neutral validator messages |
| Hidden package byte/mode mutation under index flags | all four combinations downgrade to `installed_package`; Git status stays empty |
| Hidden tracked-file deletion under `skip-worktree` | exact HEAD path-set mismatch downgrades to `installed_package` |
| Source identity commit/tree/path/blob mutation matrix | all rejected |
| Installed-wheel console replay from unrelated cwd | PASS; 8-artifact manifest verified; package binding matches |
| Two clean commit-epoch wheel builds | byte-identical |
| Canonical symlink, workstation-path, and secret-marker scan | clean |
| GitHub exact-head CI | recorded in draft PR #7 after push; no pre-push status is asserted here |

The wheel built twice from clean archives of the implementation commit with its
exact epoch `1783967141` is
`eval_ground_truth_lab-0.2.0-py3-none-any.whl`, 105,619 bytes, SHA-256
`6b09fc731aa03160e482309d6a58e9ab5b96e087373e849e71eb7c4c7838e166`.
Archive inspection found the HTML report template, execution-binding module,
and all four Trader replay resources. A fresh environment installed that wheel,
passed `pip check`, and ran the console replay with no explicit input paths from
an unrelated working directory. The installed package payload is 56 files,
SHA-256 `33f9455c2ffd9ff88c9f12387ce86e402a3345cadfb3cb53051295dda37d276e`.

## Canonical implementation identity

- Commit: `f810e3a7a9ef6c077371ef401c345f56da3c8c27`.
- Tree: `8da573207b40329f125a999165163b73f4b0e8c0`.
- Schema: `eval-lab-implementation-provenance-v2`.
- Package-wide loaded-code binding:
  `33c0e48b7eff1fcd4656418cbb75491d408d16f01bdea1860c818997893cc5b6`.
- Recursive package payload: 56 files,
  `33f9455c2ffd9ff88c9f12387ce86e402a3345cadfb3cb53051295dda37d276e`.
- The canonical replay records `git_worktree` and
  `measured_package_matches_head=true`; the installed-wheel replay records
  `installed_package` with the same payload and binding digests.

## Canonical evidence

The regenerated pack is
`docs/evidence/integrations/trader-risk-audit-synthetic-v1/`.

- Gate: PASS for the single authored synthetic compatibility case.
- Validators: 11/11 pass.
- Artifacts: 8/8 verify, including the exact source-identity proof.
- Content address:
  `sha256:1b228a37ea3686cc9c57132c7b2d2048a49c71995fd63b4d020d619bf30f72c3`.
- Manifest file SHA-256:
  `ddc4f3311a196cb6a6fd2cbe6f73bc282aa076c5b98246f9a2a62acfc55ef81b`.
- Replay result SHA-256:
  `409fe1acc8e96b624e8ac057b2b8e12e2550788426a7283f51e1308abe1def0a`.
- Sealed run JSON SHA-256:
  `de971adfdac3ca723f3b18c1db25ff7b73216e9e152696e94860e10fbfc10ccf`.
- Seal file SHA-256:
  `baee0b8bf0ce7ad07be8382b6d87f315e4a3215ed24609f7dc6626c833c2e6ed`.
- Eval implementation commit/tree/measured-package proof:
  `f810e3a7a9ef6c077371ef401c345f56da3c8c27` /
  `8da573207b40329f125a999165163b73f4b0e8c0` /
  `measured_package_matches_head=true`.

This evidence remains a self-authored synthetic contract replay. It is not a
financial-performance result, external-user case study, production run, or
publisher-authentication claim.
