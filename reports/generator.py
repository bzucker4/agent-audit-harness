from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    """Normalized record used for report rendering."""

    test_name: str
    attack_class: str
    owasp: str
    status: str = "Mitigated"  # Vulnerable / Mitigated / Error
    raw_trace: dict[str, Any] | None = None
    remediation: str = ""
    case_id: str = ""
    description: str = ""


def summarize(records: list[AuditRecord]) -> dict[str, Any]:
    """Build executive summary counts for report templates."""
    status_counts: dict[str, int] = {"Vulnerable": 0, "Mitigated": 0, "Error": 0}
    attack_counts: dict[str, int] = {}

    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
        attack_counts[record.attack_class] = attack_counts.get(record.attack_class, 0) + 1

    return {
        "total": len(records),
        "status_counts": status_counts,
        "attack_counts": attack_counts,
    }


_STATUS_ORDER = {"Vulnerable": 0, "Error": 1, "Mitigated": 2}


def _slim_trace(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop `raw` copies that duplicate the normalized tool_calls (kept if nothing parsed)."""
    if not trace:
        return trace
    raw = trace.get("raw") or {}
    unparsed = not trace.get("tool_calls") and "tool_calls" not in raw  # keep raw as evidence only then
    slim = {k: v for k, v in trace.items() if k != "raw" or unparsed}
    slim["tool_calls"] = [{k: v for k, v in c.items() if k != "raw"} for c in trace.get("tool_calls", [])]
    return slim


def _sorted(records: list[AuditRecord]) -> list[AuditRecord]:
    """Vulnerable first, then errors, then mitigated (stable); traces slimmed for display."""
    ordered = sorted(records, key=lambda r: _STATUS_ORDER.get(r.status, 3))
    return [r.model_copy(update={"raw_trace": _slim_trace(r.raw_trace)}) for r in ordered]


class ReportGenerator:
    """Render Markdown and HTML reports from audit records."""

    def __init__(self, template_dir: str | Path | None = None):
        template_dir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "html.j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_markdown(self, records: list[AuditRecord]) -> str:
        template = self.env.get_template("report.md.j2")
        return template.render(records=_sorted(records), summary=summarize(records))

    def render_html(self, records: list[AuditRecord]) -> str:
        template = self.env.get_template("report.html.j2")
        return template.render(records=_sorted(records), summary=summarize(records))

    def generate(
        self,
        records: list[AuditRecord],
        output_dir: str | Path,
        base_name: str = "audit_report",
    ) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = output_dir / f"{base_name}.md"
        html_path = output_dir / f"{base_name}.html"

        markdown_path.write_text(self.render_markdown(records))
        html_path.write_text(self.render_html(records))
        return output_dir


def main(argv: list[str] | None = None) -> int:
    """CLI: render a report from a pytest_results.json written by the audit plugin."""
    ap = argparse.ArgumentParser(prog="python -m reports.generator")
    ap.add_argument("--input", default="pytest_results.json")
    ap.add_argument("--output", default="audit_report.md", help="Markdown path; an .html twin is written beside it")
    args = ap.parse_args(argv)
    records = [AuditRecord.model_validate(r) for r in json.loads(Path(args.input).read_text())]
    gen = ReportGenerator()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(gen.render_markdown(records))
    out.with_suffix(".html").write_text(gen.render_html(records))
    print(f"wrote {out} and {out.with_suffix('.html')} ({len(records)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
