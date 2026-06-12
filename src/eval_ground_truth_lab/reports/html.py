from __future__ import annotations

from html import escape
from pathlib import Path

TEMPLATE_PATH = Path(__file__).with_name("templates") / "eval_report.html"


def render_html_report(
    *,
    markdown_report: str,
    canonical_markdown_path: str,
    run_artifact_path: str,
    title: str,
    scope_label: str,
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    values = {
        "title": escape(title),
        "scope_label": escape(scope_label),
        "canonical_markdown_path": escape(canonical_markdown_path, quote=True),
        "run_artifact_path": escape(run_artifact_path, quote=True),
        "markdown_body": escape(markdown_report),
    }
    for key, value in values.items():
        template = template.replace("{{ " + key + " }}", value)
    return template
