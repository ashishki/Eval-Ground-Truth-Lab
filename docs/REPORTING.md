# Reporting

Markdown reports and JSON run artifacts are canonical. Static HTML reports are
derivative views for easier reading and contain no separate metrics logic.

## Canonical Artifacts

- Markdown: `reports/gdev-agent/baseline_report.md`
- Run JSON: `reports/gdev-agent/baseline_run.json`

## Derivative HTML

- HTML: `reports/gdev-agent/baseline_report.html`

The HTML report is generated from the same markdown report body and links the
canonical markdown and run artifact. If values differ, the markdown and run JSON
win.
