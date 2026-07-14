# Reporting

Machine-readable JSON is the canonical source for executable challenge runs;
their Markdown is rendered solely from the JSON object. The legacy curated
55-case baseline keeps its Markdown and run JSON as paired canonical evidence.
Static HTML is always derivative and contains no separate metrics logic.

Comparison Markdown treats every run field, validator receipt, message, and raw
artifact label/path as untrusted presentation data. Table delimiters, code-span
delimiters, HTML delimiters, and Markdown/autolink punctuation are encoded for
their exact context. Newlines, Unicode line/paragraph separators, controls, and
bidirectional controls are replaced with visible escape sequences rather than
decoded control entities. A caller-controlled value therefore cannot add a
heading, table row, link, image, autolink, HTML element, directionality change,
or forged PASS statement. This output encoding is defense in depth in addition
to the strict comparison-input contract.

The threshold table records exact rational/decimal deltas and exact gate
expressions. Status is computed from those values, not from the float-facing
delta attributes or caller-authored aggregates. Non-terminating count ratios use
fraction notation such as `-1/3`; terminating cost and latency differences use
canonical decimal notation such as `0.1`.

The comparison report is published only after the complete decision succeeds.
The CLI and reusable Action stage it beside the final destination, fsync the
file, and atomically replace the verified regular-file target. Once the
respective helper owns that target, an invalid comparison removes a stale
report instead of allowing a previous decision to appear current. Setup
failures before a helper starts are not covered by its cleanup guarantee.

The shared comparison report appends `Validator Receipt Regressions` only when
one or more corresponding receipts change from pass to fail. Its deterministic
table records the case, validator, and candidate category, and the zero-tolerance
gate blocks every such transition even when the category is not one of the
five aggregate metrics. A failure already present in the baseline and a
candidate recovery do not create this regression section.

## Canonical Artifacts

- Markdown: `reports/gdev-agent/baseline_report.md`
- Run JSON: `reports/gdev-agent/baseline_run.json`

An operator-generated challenge evidence pack contains:

- `challenge-run.json`: metric, slice, reconciliation, threshold, and provenance source.
- `challenge-report.md`: deterministic view generated from `challenge-run.json`.
- `run/<run-id>.json` and `.sha256`: terminal RunStore record and seal.
- `sha256-<digest>.manifest.json`: content address plus every artifact digest/size.

## Derivative HTML

- HTML: `reports/gdev-agent/baseline_report.html`

The HTML report is generated from the same markdown report body and links the
canonical markdown and run artifact. If values differ, the markdown and run JSON
win.
