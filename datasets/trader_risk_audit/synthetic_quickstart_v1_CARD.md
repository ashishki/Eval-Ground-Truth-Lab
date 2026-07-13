# Trader Risk Audit synthetic quickstart v1

Status: self-authored compatibility fixture; public, deterministic, and not blind.

## Purpose

This one-case dataset checks whether Eval Ground Truth Lab can fail closed while
loading the sanitized `trader-risk-audit-evidence-v1` export from the separately
versioned Trader Risk Audit product. It applies exact expectations to contract,
source, manifest, evidence, check, and observation fields.

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
provenance file, source pin, contract shape, check, metric, or expected value must
fail loading or the Eval gate.

PASS means compatibility with this single synthetic contract fixture. It is not
external validation, investment advice, a production claim, or a general quality
score for either repository.
