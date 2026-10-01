from __future__ import annotations

import json
from pathlib import Path

import pytest

from reports.generator import AuditRecord, ReportGenerator


class AuditPlugin:
    """Collect per-test audit records and write a report at session finish."""

    def __init__(self, config: pytest.Config):
        self.config = config
        self.report_dir = config.getoption("--audit-report-dir") or "reports/output"
        self.records: list[AuditRecord] = []

    def collect(self, item: pytest.Item, outcome: str, longrepr: str = "") -> None:
        props = dict(item.user_properties)
        if "audit_case" not in props:
            return

        case = props["audit_case"]
        trace = props.get("audit_trace")

        status = "Error"
        if outcome == "passed":
            status = "Mitigated"
        elif outcome == "failed":
            status = "Vulnerable" if "VULNERABLE:" in longrepr else "Error"
        if "audit_status" in props:
            status = props["audit_status"]

        self.records.append(
            AuditRecord(
                test_name=item.nodeid,
                attack_class=props.get("attack_class", case.get("attack_class") or case.get("class", "unknown")),
                owasp=props.get("owasp", case.get("owasp") or case.get("owasp_category", "")),
                status=status,
                raw_trace=trace,
                remediation=props.get("remediation", case.get("remediation", "")),
                case_id=props.get("case_id", case.get("id", "")),
                description=case.get("description") or case.get("name", ""),
            )
        )

    def write(self) -> None:
        if not self.records:
            return
        ReportGenerator().generate(self.records, self.report_dir)
        Path("pytest_results.json").write_text(
            json.dumps([r.model_dump(mode="json") for r in self.records], indent=2)
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--audit-report-dir",
        action="store",
        default=None,
        help="Directory where the audit report Markdown/HTML files will be written",
    )


def pytest_configure(config: pytest.Config) -> None:
    if not hasattr(config, "_audit_plugin"):
        config._audit_plugin = AuditPlugin(config)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        plugin = getattr(item.config, "_audit_plugin", None)
        if plugin:
            plugin.collect(item, report.outcome, str(report.longrepr or ""))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    plugin = getattr(session.config, "_audit_plugin", None)
    if plugin:
        plugin.write()
