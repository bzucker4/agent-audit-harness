from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Normalized tool call record."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    timestamp: datetime | None = None
    step_index: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    """Normalized trace record containing zero or more tool calls."""

    trace_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    source: str = "api"


def _as_args(value: Any) -> dict[str, Any]:
    """Normalize tool call arguments into a dict, parsing JSON strings if needed."""
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {"_raw": value}
    if isinstance(value, dict):
        return value
    return {"_raw": value}


def _parse_tool_call(obj: Any) -> ToolCall | None:
    """Normalize a dict-like object into a ToolCall."""
    if not isinstance(obj, dict):
        return None

    name = obj.get("name") or obj.get("tool_name") or obj.get("tool")
    if isinstance(name, dict):
        name = name.get("name")
    if not name:
        function = obj.get("function")
        if isinstance(function, dict):
            name = function.get("name")

    if not name:
        return None

    args = obj.get("arguments", obj.get("input", obj.get("args", obj.get("parameters", {}))))
    result = obj.get("result", obj.get("output"))
    timestamp = obj.get("timestamp") or obj.get("startTime") or obj.get("createdAt")
    step_index = obj.get("step_index") or obj.get("stepIndex")

    return ToolCall(
        name=name,
        arguments=_as_args(args),
        result=result,
        timestamp=timestamp,
        step_index=step_index,
        raw=obj,
    )


def _parse_api(raw: Any) -> list[ToolCall]:
    """Parse the target agent API trace format."""
    if not isinstance(raw, dict):
        return []
    calls = raw.get("tool_calls") or []
    if not isinstance(calls, list):
        return []
    return [tc for tc in map(_parse_tool_call, calls) if tc is not None]


def _parse_otel(raw: Any) -> list[ToolCall]:
    """Parse OpenTelemetry-style spans."""
    spans: list[Any] = []
    if isinstance(raw, dict):
        spans = raw.get("spans", [])
    elif isinstance(raw, list):
        spans = raw

    tool_calls: list[ToolCall] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        attrs = span.get("attributes", {})
        if not isinstance(attrs, dict):
            attrs = {}
        name = attrs.get("tool.name") or attrs.get("tool_name") or span.get("name") or span.get("operation.name")
        if not name:
            continue
        args = attrs.get("tool.arguments") or attrs.get("tool.args") or attrs.get("input") or span.get("input", {})
        result = attrs.get("tool.result") or attrs.get("output") or span.get("output")
        tool_calls.append(
            ToolCall(
                name=name,
                arguments=_as_args(args),
                result=result,
                timestamp=span.get("startTime") or span.get("timestamp"),
                raw=span,
            )
        )
    return tool_calls


def _parse_langfuse(raw: Any) -> list[ToolCall]:
    """Parse Langfuse observation list/dict format."""
    data: list[Any] = []
    if isinstance(raw, dict):
        data = raw.get("data", raw.get("observations", []))
    elif isinstance(raw, list):
        data = raw

    tool_calls: list[ToolCall] = []
    for obs in data:
        if not isinstance(obs, dict):
            continue
        name = obs.get("name") or obs.get("toolName") or obs.get("tool")
        if not name:
            continue
        args = obs.get("input") or obs.get("arguments") or {}
        result = obs.get("output") or obs.get("result")
        tool_calls.append(
            ToolCall(
                name=name,
                arguments=_as_args(args),
                result=result,
                timestamp=obs.get("timestamp") or obs.get("startTime"),
                step_index=obs.get("step"),
                raw=obs,
            )
        )
    return tool_calls


def _try_parse_tool_call_json(text: Any) -> ToolCall | None:
    """Attempt to parse a string as JSON containing a tool call."""
    try:
        data = json.loads(str(text))
        return _parse_tool_call(data)
    except Exception:
        return None


def _parse_burp(raw: Any) -> list[ToolCall]:
    """Parse Burp-export/HAR-style JSON into normalized tool calls."""
    entries: list[Any] = []
    if isinstance(raw, dict):
        log = raw.get("log", {})
        entries = log.get("entries", []) if isinstance(log, dict) else raw.get("entries", [])
    elif isinstance(raw, list):
        entries = raw

    tool_calls: list[ToolCall] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        request = entry.get("request", entry)
        if not isinstance(request, dict):
            continue
        url = request.get("url") or request.get("path") or ""
        method = request.get("method")
        post_data = request.get("postData")
        body_text = request.get("body") or request.get("content") or ""
        if isinstance(post_data, dict):
            body_text = post_data.get("text", body_text)
        if body_text:
            tc = _try_parse_tool_call_json(body_text)
            if tc is not None:
                tool_calls.append(tc)
                continue
        if method:
            tool_calls.append(ToolCall(name=method, arguments={"url": url}, raw=entry))
    return tool_calls


def _parse_any(raw: Any) -> list[ToolCall]:
    """Best-effort parser across supported formats."""
    if isinstance(raw, list):
        parsed = [tc for tc in map(_parse_tool_call, raw) if tc is not None]
        if parsed:
            return parsed
    return _parse_api(raw) or _parse_otel(raw) or _parse_langfuse(raw) or _parse_burp(raw)


def parse_trace(raw: Any, source: str = "api") -> Trace:
    """Normalize an arbitrary trace-like payload into a Trace."""
    if raw is None:
        return Trace(source=source, raw={})

    raw_dict = raw if isinstance(raw, dict) else {"value": raw}
    trace_id: str | None = None
    tool_calls: list[ToolCall] = []

    if source == "api":
        tool_calls = _parse_api(raw)
        if isinstance(raw, dict):
            trace_id = raw.get("trace_id") or raw.get("id")
    elif source == "otel":
        tool_calls = _parse_otel(raw)
        if isinstance(raw, dict):
            trace_id = raw.get("traceId") or raw.get("trace_id")
            if not trace_id and raw.get("spans"):
                first_span = raw["spans"][0] if raw["spans"] else {}
                trace_id = first_span.get("traceId") if isinstance(first_span, dict) else None
    elif source == "langfuse":
        tool_calls = _parse_langfuse(raw)
        if isinstance(raw, dict):
            trace_id = raw.get("traceId") or raw.get("trace_id")
    elif source in ("burp_export", "burp"):
        tool_calls = _parse_burp(raw)
    elif source == "file":
        if isinstance(raw, dict) and "tool_calls" in raw:
            return parse_trace(raw, "api")
        tool_calls = _parse_any(raw)
        if isinstance(raw, dict):
            trace_id = raw.get("trace_id") or raw.get("traceId")
    else:
        tool_calls = _parse_any(raw)
        if isinstance(raw, dict):
            trace_id = raw.get("trace_id") or raw.get("traceId") or raw.get("id")

    return Trace(trace_id=trace_id, tool_calls=tool_calls, raw=raw_dict, source=source)
