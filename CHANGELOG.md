# Changelog

All notable changes are documented here. The project follows semantic versioning
once stable releases begin.

## Unreleased

- Add a fail-closed Eval-side import/replay adapter for the separate Trader Risk
  Audit sanitized evidence contract.
- Pin a fully synthetic Trader export to an exact path-purged candidate commit,
  tree, Git blob, bundle digest, file SHA-256, and evidence content hash.
- Add exact deterministic validators, a sealed CLI replay, content-addressed
  evidence packaging, fixture tests, documentation, and explicit financial,
  production, and external-validation boundaries.
- Seal one-read input snapshots, validate every nested result field, bind source
  path and provenance-file identity, and reject vacuous non-singleton v1 datasets.
- Ship the default synthetic Trader replay inputs in the wheel and exercise its
  console command from an unrelated working directory in CI.
- Package the exact locked terminal RunStore JSON/seal snapshot and cross-bind
  its hashes and run identity through result and manifest.
- Reject unknown dataset fields, noncanonical Trader metadata, malformed nested
  expectations, and recursive JSON/YAML duplicate keys before output creation;
  withhold fixture/privacy claims from caller-supplied dataset overrides.
- Bind the full replay decision path and package payload to source commit/tree or
  installed-artifact identity, and require two commit-epoch wheel builds to be
  byte-identical in least-privilege, time-bounded CI.
- Require byte-identical packaged Trader evidence/provenance before granting
  reviewed source or privacy claims, and bind commit/tree/path/blob with a
  packaged offline Git-object proof.
- Classify ignored or untracked package installations inside unrelated Git
  repositories as installed artifacts with payload digests, not worktrees.
- Separate caller-declared Trader privacy/source metadata from effective trust
  in direct adapter output and sealed runs; unreviewed evidence stays downgraded
  even when a matching caller expectation makes the compatibility gate pass.
- Replace whole-worktree cleanliness claims with an exact measured-package proof
  over the recursive HEAD path set, every file byte, and executable mode, including
  adversarial `assume-unchanged`, `skip-worktree`, and hidden-deletion coverage.
- Reject all injected adapters on the evidentiary Trader replay path and always
  construct the exact canonical adapter from its captured input bytes; keep input
  mutation testing behind a private non-CLI snapshot hook.
- Derive named component hashes, recursive package identity, and HEAD comparison
  from one immutable bytes/modes/paths snapshot; reject components outside the
  package root and fail closed on mutation during recursive capture.

## 0.2.0 - 2026-07-13

- Add executable gdev-agent challenge reconciliation and threshold gates.
- Add deterministic provider-fault injection for declared failure cases.
- Add machine-readable challenge results and content-addressed evidence manifests.
- Scope live gdev HTTP request/message IDs by deterministic run, candidate,
  component, and dataset context; record the namespace in challenge evidence.
- Require explicit component revisions for gdev eval runs and fail closed when a
  live HTTP adapter has no request namespace.
- Publish the canonical 100-case local gdev-agent challenge as a verified
  content-addressed FAIL without changing dataset cases or thresholds.
- Add a dataset card, executable hypotheses, provenance and holdout status,
  leakage controls, and an append-only independent-label review protocol.
- Harden RunStore identifiers, concurrent creation, atomic writes, and terminal seals.
- Publish Apache-2.0 project metadata and complete wheel package data.

## 0.1.0

- Initial local-first dataset, validator, adapter, run, comparison, and report proof.
