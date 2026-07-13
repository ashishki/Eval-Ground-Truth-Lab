# Trader Risk Audit adapter review-fix verification

Date: 2026-07-13

Scope: draft Trader Risk Audit adapter PR review blockers

Implementation commit: `0860ae64d282c3697c16f59d43b376e8557be108`

## Implemented controls

- Adapter results are rebuilt from an immutable evidence-byte snapshot on every
  invocation; nested evidence containers are not shared between results.
- Direct adapter output preserves caller privacy/source values only as
  `declared_privacy_classification` and `declared_source`; its separate
  `effective_trust` block is fail-closed and unassessed.
- Replay derives effective trust from packaged byte identity and the offline
  Git-object proof before sealing RunStore output. Validator receipts label
  declarations explicitly and use neutral `selected expectation` messages.
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
- Evidence/provenance privacy and source-review claims require byte
  identity with both packaged resources. A fully re-self-hashed caller payload
  retaining canonical case/commit/tree/path ids remains unreviewed, is not an
  overall fixture, and receives a caller-evidence candidate identity.
- A self-hashed modified export plus a matching caller expectation can PASS the
  compatibility gate, but direct output remains unassessed and the sealed run,
  result, manifest, report, replay type, and candidate identity remain explicitly
  caller-supplied and unreviewed.
- A packaged offline Git-object proof independently recomputes and binds the
  source commit, root tree, repository path, and evidence blob. The proof also
  binds the protected source bundle SHA-256 already recorded in provenance.
- The wheel contains all four default Trader replay resources. CLI defaults use
  package resources instead of checkout-relative paths.
- Manifest provenance covers the parser, RunStore, manifest writer, adapter,
  runner, validators, and complete package payload. Canonical evidence records
  the exact Eval commit/tree for which measured package bytes and modes match;
  an installed wheel records its artifact digest.
- `git_worktree` implementation provenance requires the exact recursive HEAD
  package path set, byte-for-byte Git blob identity, and executable-mode identity.
  It makes no whole-worktree cleanliness claim. `assume-unchanged`,
  `skip-worktree`, and hidden deletion probes all downgrade to
  `installed_package`; executable mode participates in the payload digest.
- CI has read-only repository contents permission, a 20-minute timeout, and two
  cache-disabled builds using commit-derived `SOURCE_DATE_EPOCH`; unequal wheel
  bytes fail the job.

## Local verification

| Check | Result |
|---|---|
| Focused Trader/source/implementation suite | `44 passed` |
| Full test suite | `221 passed` |
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
| Re-self-hashed caller evidence plus matching caller dataset | PASS gate; direct and sealed output remain privacy-unreviewed/source-unauthenticated; neutral validator messages |
| Ignored installed package inside unrelated Git repo | `installed_package`; payload digest present |
| Hidden package byte/mode mutation under `assume-unchanged` and `skip-worktree` | all four combinations downgrade to `installed_package`; Git status remains empty |
| Hidden tracked-file deletion under `skip-worktree` | exact HEAD path-set mismatch downgrades to `installed_package` |
| Source identity commit/tree/path/blob mutation matrix | all rejected |
| Installed-wheel console replay from unrelated cwd | PASS; 8-artifact manifest verified |
| Two clean commit-epoch wheel builds | byte-identical |
| Canonical input byte comparison | PASS |
| Canonical symlink, workstation-path, and secret-marker scan | clean |

The wheel built twice from a clean archive of the implementation commit is
`eval_ground_truth_lab-0.2.0-py3-none-any.whl`, SHA-256
`727ec4cf45c83e8ea6106327e93dde86b62c1df97e8117ac5c3a92bf8193763a`.
Archive inspection found the HTML report template and the four Trader replay
resource files. The installed console replay used no explicit input paths.
The second clean build produced the same SHA-256. Its installed package payload
digest is `68bcc4940f14650e3a7d091aa9feb1c4fdc30db074e4c6e0e336bdf6dd012183`.

## Canonical evidence

The regenerated pack is
`docs/evidence/integrations/trader-risk-audit-synthetic-v1/`.

- Gate: PASS for the single authored synthetic compatibility case.
- Validators: 11/11 pass.
- Artifacts: 8/8 verify, including the exact source-identity proof.
- Content address:
  `sha256:e450c9a7561f88f8f90ce1464457d8ddb18435ce105451a9dbb8ab6e64c4d5fb`.
- Manifest file SHA-256:
  `17bf64fb9c51707810e7d9a6f99f562e7fa779eda16ca1a50c990fd3c1d17f68`.
- Replay result SHA-256:
  `b764a7fe6aec51ebba792187d4c58b21dd05bce710cdc69c691a32dfc4adc19e`.
- Sealed run JSON SHA-256:
  `ef46254b2f8011cd2fc504294901595ebd62090c2cf149afb3b0f8caf02b4eb1`.
- Seal file SHA-256:
  `b55d29eca4fe902fa8b5869cf3d054adcad83c593cf709530c32af4f53e3d86f`.
- Eval implementation commit/tree/measured-package proof:
  `0860ae64d282c3697c16f59d43b376e8557be108` /
  `d79cff41a04acecc1d638d311f195fd5df9af248` /
  `measured_package_matches_head=true`.

This evidence remains a self-authored synthetic contract replay. It is not a
financial-performance result, external-user case study, production run, or
publisher-authentication claim. GitHub-hosted CI status is recorded separately
after the branch is pushed.
