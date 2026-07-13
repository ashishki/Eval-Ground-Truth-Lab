# Reporting

Machine-readable JSON is the canonical source for executable challenge runs;
their Markdown is rendered solely from the JSON object. The legacy curated
55-case baseline keeps its Markdown and run JSON as paired canonical evidence.
Static HTML is always derivative and contains no separate metrics logic.

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
