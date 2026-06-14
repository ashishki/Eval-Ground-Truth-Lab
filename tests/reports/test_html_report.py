from __future__ import annotations

from pathlib import Path

from eval_ground_truth_lab.reports.html import render_html_report

ROOT = Path(__file__).resolve().parents[2]


def test_html_report_uses_markdown_report_data() -> None:
    markdown = _read("reports/gdev-agent/baseline_report.md")
    expected_html = render_html_report(
        markdown_report=markdown,
        canonical_markdown_path="baseline_report.md",
        run_artifact_path="baseline_run.json",
        title="gdev-agent Baseline Report",
        scope_label="synthetic/local deterministic evidence; markdown and run JSON are canonical",
    )
    committed_html = _read("reports/gdev-agent/baseline_report.html")

    assert committed_html == expected_html
    for markdown_value in (
        "classification_accuracy",
        "unsafe_auto_approval_rate",
        "latency_p95_ms",
        "No failures",
    ):
        assert markdown_value in committed_html


def test_html_report_links_canonical_artifacts() -> None:
    committed_html = _read("reports/gdev-agent/baseline_report.html")

    assert "synthetic/local deterministic evidence" in committed_html
    assert 'href="baseline_report.md"' in committed_html
    assert 'href="baseline_run.json"' in committed_html
    assert "Canonical markdown report" in committed_html
    assert "Canonical run artifact" in committed_html


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")
