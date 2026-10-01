from __future__ import annotations

from core.models import parse_trace


def test_parse_api_trace():
    raw = {
        "trace_id": "t1",
        "tool_calls": [
            {"name": "read_file", "arguments": {"path": "/tmp/a"}},
        ],
    }
    trace = parse_trace(raw, "api")
    assert trace.trace_id == "t1"
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].name == "read_file"
    assert trace.tool_calls[0].arguments == {"path": "/tmp/a"}


def test_parse_api_arg_json_string():
    raw = {"tool_calls": [{"name": "x", "arguments": '{"a": 1}'}]}
    trace = parse_trace(raw, "api")
    assert trace.tool_calls[0].arguments == {"a": 1}


def test_parse_otel_spans():
    raw = {
        "spans": [
            {
                "name": "tool.execute",
                "attributes": {
                    "tool.name": "read_file",
                    "tool.arguments": {"path": "/x"},
                },
            }
        ]
    }
    trace = parse_trace(raw, "otel")
    assert trace.tool_calls[0].name == "read_file"
    assert trace.tool_calls[0].arguments == {"path": "/x"}


def test_parse_langfuse_observations():
    raw = {"data": [{"name": "read_file", "input": {"path": "/x"}, "output": "ok"}]}
    trace = parse_trace(raw, "langfuse")
    assert trace.tool_calls[0].name == "read_file"
    assert trace.tool_calls[0].result == "ok"


def test_parse_burp_har():
    raw = {
        "log": {
            "entries": [
                {
                    "request": {
                        "method": "POST",
                        "url": "http://agent.example.com/tool",
                        "postData": {
                            "text": '{"name": "read_file", "arguments": {"path": "/x"}}'
                        },
                    }
                }
            ]
        }
    }
    trace = parse_trace(raw, "burp_export")
    assert trace.tool_calls[0].name == "read_file"
    assert trace.tool_calls[0].arguments == {"path": "/x"}
