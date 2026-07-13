# Trader Risk Audit synthetic quickstart v1

Status: self-authored compatibility fixture; public, deterministic, and not blind.

## Purpose

This one-case dataset checks whether Eval Ground Truth Lab can fail closed while
loading the sanitized `trader-risk-audit-evidence-v1` export from the separately
versioned Trader Risk Audit product. It applies exact expectations to contract,
source path, provenance-file identity, evaluation boundary, artifact receipts,
trace preview, manifest, evidence, check, and observation fields. The entire
sealed adapter result is expected; unrecognized nested fields fail closed.

The dataset tests an adapter boundary. It does not re-run the Trader rule engine,
validate raw trades, choose suitable risk limits, assess strategy performance, or
establish the correctness of a financial audit.

## Source and privacy

- The source fixture contains four invented trade observations and seven
  deterministic rule observations.
- The committed fixture is the sanitized export only. It contains artifact
  names and digests, aggregate counts, check results, and opaque trace references;
  it contains no raw trades, account identifiers, filesystem paths, credentials,
  contact data, or customer data.
- Independent annotators: `0`.
- External workflow owners represented: `0`.
- Real users or production runs represented: `0`.

The exact publication-candidate commit, tree, Git blob, protected bundle digest,
package version, contract version, evidence file SHA-256, and evidence content
hash are pinned in `synthetic_quickstart_v1.provenance.json`. The adapter verifies
the evidence SHA-256, Git blob identity, and both contract content hashes. The
bundle digest is a provenance pin; the bundle itself is not distributed here.

## Expected decision

The unmodified fixture passes exact deterministic validators. A modified export,
provenance file, source pin/path, contract shape, evaluation boundary, artifact,
trace, check, metric, or expected value must fail loading or the Eval gate. An
empty or multi-case v1 dataset is rejected before a PASS pack can be written.
Cases allow only `id`, `input`, `expected`, and `metadata`; the case id/input and
metadata schema and values are exact. Duplicate JSON/YAML mapping keys are
rejected recursively. These checks run before output directories are created.

Fixture/privacy classification also requires byte identity with the packaged
dataset under its canonical name. A caller-supplied schema-valid override is
marked non-fixture and not privacy-reviewed even when its metadata repeats the
trusted synthetic labels.

PASS means compatibility with this single synthetic contract fixture. It is not
external validation, investment advice, a production claim, or a general quality
score for either repository.
