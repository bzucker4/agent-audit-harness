from __future__ import annotations

import pytest

from core.client import AgentClient


@pytest.fixture
def client(config):
    """Provide an AgentClient instance with a clean capture buffer."""
    with AgentClient(config, user="user_a") as agent:
        yield agent


@pytest.fixture
def audit_record(request):
    """Fixture used by tests to attach case metadata and trace to the report plugin."""
    def record(case, trace):
        props = request.node.user_properties
        props.append(("audit_case", case))
        props.append(("audit_trace", trace.model_dump(mode="json")))
        props.append(("remediation", case.get("remediation", "")))
        props.append(("attack_class", case.get("attack_class") or case.get("class", "")))
        props.append(("owasp", case.get("owasp") or case.get("owasp_category", "")))
        props.append(("case_id", case.get("id", "")))
    return record
