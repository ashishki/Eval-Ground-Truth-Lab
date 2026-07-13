# License compatibility review

Review date: 2026-07-13

## Decision

The repository is licensed under Apache License 2.0. `pyproject.toml` publishes
the SPDX expression `Apache-2.0`, and the wheel includes `LICENSE`.

## Reviewed local dependency set

This review used installed package metadata and repository source headers; it
did not infer licenses for uninstalled future resolutions.

| Use | Package/version reviewed | Declared license | Compatibility |
|---|---|---|---|
| Runtime | PyYAML 6.0.3 | MIT | Compatible |
| Development | pytest 9.0.3 | MIT | Compatible |
| Development | Ruff 0.15.16 | MIT | Compatible |
| Development transitives | packaging, pluggy, Pygments | Apache/BSD/MIT | Compatible |

No vendored or `third_party` source tree and no conflicting third-party source
header was found. Dependencies remain separate works; their notices and license
terms must be preserved when redistributed in a bundled form.

## Data and documentation

Repository fixtures describe themselves as authored synthetic data. The project
license explicitly covers code, documentation, manifests, thresholds, and those
authored synthetic datasets. Contributors must document provenance and may not
submit data they cannot redistribute.

The Trader Risk Audit compatibility fixture is the sanitized `eval-export`
derived from that repository's authored `examples/synthetic_quickstart/` data.
The reviewed path-purged source candidate also declares Apache-2.0 for authored
source, documentation, configuration, and explicitly synthetic fixtures. Its
license/data review identifies the synthetic quickstart as Apache-2.0 and keeps
externally sourced rows under separate source terms. Eval Lab copies only the
synthetic sanitized export; it does not copy SEC, blockchain, or excluded Dune
rows. The exact source commit/tree/blob/bundle and fixture hashes are pinned in
`datasets/trader_risk_audit/synthetic_quickstart_v1.provenance.json`.

## Boundaries

- The conclusion covers the versions above, not every package a broad future
  dependency range could resolve to.
- Release automation should retain bounded ranges, capture resolved versions,
  and produce an SBOM/license inventory before bundled distribution.
- Optional external adapters and systems are not relicensed by this project.
