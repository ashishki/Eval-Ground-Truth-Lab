# Trader Risk Audit sanitized evidence adapter

Status: implemented pinned import/replay contract for one fully synthetic fixture.

## Product boundary

Trader Risk Audit remains a separate applied FinTech product. It owns trade
normalization, policy rules, deterministic findings, P&L attribution, reporting,
and the upstream `eval-export` command. Eval Ground Truth Lab owns the versioned
expected case, fail-closed import adapter, deterministic comparison, sealed run,
gate decision, and content-addressed replay evidence.

There is no code import from Trader Risk Audit and no product merge. The adapter
reads only its sanitized JSON export. It does not run the Trader rule engine,
read raw trades, choose risk thresholds, infer financial ground truth, or apply
investment advice.

## Pinned source

The committed v1 fixture is exported by Trader Risk Audit package `0.2.0` using
contract `trader-risk-audit-evidence-v1`. Its provenance record pins:

- path-purged publication-candidate commit
  `bf755a24450ff7c17328fa6d447f36bea8ea0fe5`;
- tree `1a2c4ff91a7504642a1bae05a9487fa2e898e0b6`;
- Git blob `9a64dc98e8edbe1ec39756611a6cb3b73b4994b9`;
- repository-relative source path
  `examples/synthetic_quickstart/evidence_preview/eval-evidence.json`;
- protected public-candidate bundle SHA-256
  `2c5b36afa9b2a9847de1c97789c52c57600e1d38cfd4947458906ee3bb3992ca`;
- fixture SHA-256
  `9925144d39bd41d6fdf8f54a1bbd900c871f1bb73cd008980baa2ae1f2d51ced`;
- upstream evidence content hash
  `d7e6fe92f50ba410a2c23882ea617b38081a8bbe84fe66727dfaecca115eb63f`;
- provenance-file SHA-256
  `3cd4339892665f5ed0003856a4b251e7524733a4ce5c99fac834d84fcdf8e402`.

The packaged Git proof contains the exact commit object and every tree object on
the repository path. Eval Lab recomputes their Git object ids and traverses the
chain from commit to root tree, path, and evidence blob. It also recomputes the
fixture SHA-256, Git blob identity, and upstream evidence content hash. The
bundle digest binds the protected source bundle used to derive this proof; the
full bundle is not distributed or opened by this command. This authenticates
the packaged source identity against Eval Lab's reviewed trust anchor, not an
external publisher identity.

## Fail-closed validation

Before Eval validators run, the adapter requires the exact v1 field shape and
checks all of the following:

- contract, package, case, and provenance version agreement;
- lowercase SHA-256 and full Git object identifiers;
- source fixture bytes against the pinned SHA-256 and Git blob;
- canonical upstream `evidence_content_hash` recomputation;
- required, unique, name-sorted artifact digests without artifact paths;
- exact boolean manifest, trace-resolution, and P&L checks;
- bounded finite metrics and status/check consistency;
- opaque `sha256-v1` rule, row, and violation trace-reference shapes;
- exact evaluation-boundary, artifact-receipt, trace-preview, source-path, and
  provenance-file expectations with no unknown nested fields;
- dataset cases allow only `id`, `input`, `expected`, and `metadata`; the Trader
  case id/input and synthetic metadata keys and values are exact;
- duplicate JSON or YAML mapping keys are rejected recursively;
- dataset cases cannot select a different evidence path or configure execution.

Eval validators then compare the validated export with the versioned one-case
synthetic expectation, including every field that the adapter seals into its
result. A mismatch returns a failing gate and still writes evidence. A malformed
or tampered source fails loading before a gate can be claimed. V1 requires
exactly one dataset case; empty or multi-case inputs fail before a run or PASS
pack can be created. Unknown fields, secret metadata, malformed nested expected
payloads, and duplicate keys fail before either run or evidence directories are
created.

The replay reads dataset, evidence, and provenance bytes once, then derives
parsing, validation, hashing, execution, and packaged inputs from those immutable
snapshots. Adapter invocations return fresh nested containers. Mutating an input
path or a prior result cannot change a later result or the bytes written to the
pack.

Dataset fixture/privacy claims are not inferred from metadata alone. Only bytes
that are identical to the packaged dataset under its canonical name are marked
as the reviewed synthetic fixture. A schema-valid caller override may produce a
diagnostic PASS or FAIL, but the result and manifest mark it as non-fixture and
`caller-supplied-dataset-not-privacy-reviewed`.

Evidence trust is independent from dataset trust. Sanitized, pinned, reviewed,
and source-identity claims require both evidence and provenance to be
byte-identical to the packaged resources and require the packaged Git-object
proof to bind commit, tree, path, and blob. Any caller-modified pair is marked
`caller-supplied-evidence-not-privacy-reviewed`, is not an overall fixture, and
uses a caller-evidence candidate identity. This remains true when the caller
recomputes every local content hash while retaining canonical source ids. Its
Markdown report labels values as caller declarations and makes no packaged
source or privacy claim.

Run completion returns the exact terminal JSON and checksum-seal bytes created
while holding the RunStore lock. Replay packaging never reopens those mutable
source paths. The terminal record SHA-256, seal SHA-256, run id, candidate,
dataset hash, validator, and completed status are identical in the packaged run,
replay result, and content-addressed manifest.

Implementation provenance covers the adapter, dataset parser, RunStore,
manifest writer, replay runner, and validators individually, plus a digest of
the complete installed package payload. Source executions record the exact Eval
commit/tree and whether the worktree was clean only when every measured package
file is tracked at that repository's HEAD. Ignored or untracked installations
inside an unrelated Git repository are classified as `installed_package` and
bind the complete installed package digest instead.

## Reproduce

Keep the mutable run store outside the evidence pack:

```bash
eval-ground-truth-lab run-trader-risk-audit-replay \
  --run-id trader-synthetic-quickstart-v1 \
  --run-dir /tmp/eval-lab-trader-runs \
  --evidence-dir /tmp/eval-lab-trader-evidence

eval-ground-truth-lab verify-evidence \
  --manifest /tmp/eval-lab-trader-evidence/sha256-*.manifest.json
```

The default dataset, evidence, provenance, and Git source proof are installed
package resources, not current-working-directory paths. Explicit `--dataset`,
`--evidence`, and `--provenance` overrides remain available and are subject to
the same snapshot and validation rules.

The first command writes the replay JSON, Markdown decision, exact input files,
checksum-sealed run record, and content-addressed manifest. Its decision is
deterministic for the pinned inputs; timestamps and the resulting pack content
address identify the individual execution and therefore are not expected to be
byte-identical across new runs.

Wheel builds are made byte-reproducible by setting `SOURCE_DATE_EPOCH` from the
Eval commit timestamp. CI performs two cache-disabled clean builds and requires
their wheel bytes to compare equal before installing either artifact.

## Evidence interpretation

The committed input contains four invented trade observations and seven
deterministic rule observations. It represents no person, account, broker,
customer, design partner, or production workload. Independent annotators: `0`.
External workflow owners represented: `0`.

A PASS proves only that Eval Lab can verify and apply exact expectations to this
specific sanitized contract fixture. It does not establish raw-data correctness,
suitable policy thresholds, investment performance, production reliability,
external adoption, or the audit report's usefulness to a real user. A real
external adapter/case study and real design-partner validation remain separate
milestones that cannot be satisfied by this repository-authored fixture.

The committed 2026-07-13 replay is indexed at
`docs/evidence/integrations/README.md` and verifies at content address
`sha256:05b2f18a78f5961f60d232d9626a471805123f78e4e46120db9c40111e2bd627`.
