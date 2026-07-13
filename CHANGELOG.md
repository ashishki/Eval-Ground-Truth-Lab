# Changelog

All notable changes are documented here. The project follows semantic versioning
once stable releases begin.

## 0.2.0 - Unreleased

- Add executable gdev-agent challenge reconciliation and threshold gates.
- Add deterministic provider-fault injection for declared failure cases.
- Add machine-readable challenge results and content-addressed evidence manifests.
- Scope live gdev HTTP request/message IDs by deterministic run, candidate,
  component, and dataset context; record the namespace in challenge evidence.
- Require explicit component revisions for gdev eval runs and fail closed when a
  live HTTP adapter has no request namespace.
- Harden RunStore identifiers, concurrent creation, atomic writes, and terminal seals.
- Publish Apache-2.0 project metadata and complete wheel package data.

## 0.1.0

- Initial local-first dataset, validator, adapter, run, comparison, and report proof.
