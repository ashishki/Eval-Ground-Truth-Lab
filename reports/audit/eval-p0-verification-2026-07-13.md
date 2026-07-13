# Eval Ground Truth Lab P0 verification

Date: 2026-07-13

Branch: `agent/eval-flagship-p0`

Base commit: `0b81d9ff15d8b5c27959528137609b59ea47d0f7`

## Implemented scope

- Apache-2.0 project, dataset, documentation, and wheel metadata.
- Safe RunStore identifiers, serialized updates, exclusive create, atomic
  fsync/replace writes, and checksum-sealed terminal records.
- Content-addressed evidence manifests with modification, deletion, symlink,
  and undeclared-file verification.
- Executable 100-case gdev-agent challenge semantics: 90 candidate-facing cases,
  ten labeled deterministic harness faults, expected-failure reconciliation,
  blocking/diagnostic outcomes, observed human routing, per-slice metrics, and
  all twelve declared threshold gates.
- Machine-readable challenge JSON as the source of generated Markdown and the
  final evidence manifest.

## Verification

| Check | Result |
|---|---|
| `PYTHONPATH=src python -m pytest tests -q --tb=short` | `140 passed in 18.57s` |
| `ruff check src tests` | pass |
| `ruff format --check src tests` | pass |
| RunStore/evidence/challenge/CLI focused tests | `45 passed in 9.13s` |
| Challenge and triage `dataset-inspect` | `100` and `55` cases; committed semantic hashes match |
| Clean wheel install and `pip check` | pass with PyYAML 6.0.3 |
| Installed console `--help` and HTML render | pass; rendered HTML `1632` bytes |
| Wheel license/package-data inspection | Apache-2.0 LICENSE, METADATA, entrypoint, and HTML template present |

Final wheel:

- `eval_ground_truth_lab-0.2.0-py3-none-any.whl`
- SHA-256: `e92ebe865aab3d5ea1fef6a004c1320ae56dad826d339052a2dd4b53436bd813`

Security tests explicitly cover path traversal, concurrent duplicate creation,
interrupted atomic replace, terminal record modification/deleted seal, and
evidence artifact modification/deletion/undeclared addition.

## Honest boundary / blocker

No canonical gdev-agent challenge result was generated or committed. The
deterministic passing/failing adapters exist only in tests and are labeled
`fixture:not-external-gdev` with worktree state `fixture`. Publishing canonical
challenge evidence remains blocked on running the fixed external gdev-agent
service while recording its exact git SHA, clean/dirty state, and environment.
