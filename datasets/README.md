# Dataset licensing and provenance

The datasets in this directory are authored synthetic fixtures and are licensed
under the repository's Apache License 2.0 unless a dataset directory explicitly
states otherwise. The same license applies to manifests, threshold configuration,
and documentation authored in this repository.

They contain no asserted real-user records and do not establish production
quality or adoption. Contributions must document provenance, remain synthetic or
be lawfully redistributable, and must not contain secrets or personal data.

The gdev-agent challenge is documented in
[`gdev_agent/challenge_v1_CARD.md`](gdev_agent/challenge_v1_CARD.md). It is a
public development set with zero independent annotators, not a blind holdout.
New datasets must declare their holdout/leakage status rather than inheriting a
benchmark claim from directory placement.
