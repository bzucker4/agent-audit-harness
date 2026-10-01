from __future__ import annotations

from pathlib import Path

from reports.generator import AuditRecord, ReportGenerator


def test_generate_report(tmp_path: Path):
    records = [
        AuditRecord(
            test_name="test_dummy.py::test_case",
            attack_class="indirect_injection",
            owasp="LLM01 Prompt Injection",
            status="Vulnerable",
            raw_trace={"trace_id": "t1", "tool_calls": []},
            remediation="Fix the prompt injection issue.",
            case_id="II-01",
            description="A malicious document was used.",
        )
    ]

    ReportGenerator().generate(records, tmp_path)

    md_path = tmp_path / "audit_report.md"
    html_path = tmp_path / "audit_report.html"
    assert md_path.exists()
    assert html_path.exists()

    md = md_path.read_text()
    assert "Vulnerable" in md
    assert "II-01" in md
    assert "Fix the prompt injection issue." in md

    html = html_path.read_text()
    assert "Vulnerable" in html
    assert "II-01" in html
    assert "Agent Tool-Abuse Audit Report" in html
