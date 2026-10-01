from __future__ import annotations

from pathlib import Path
from typing import Any

import json
import re

import pytest
import yaml

from core.assertions import evaluate_check
from core.models import Trace


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Load a YAML cases file that may be a list or a dict with a `cases` key."""
    data = yaml.safe_load(path.read_text())
    if isinstance(data, dict) and "cases" in data:
        return data["cases"]
    if isinstance(data, list):
        return data
    raise ValueError(f"No cases found in {path}")


def build_setup(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate a payload/trigger_turn case into ordered runner steps."""
    user = case.get("user", "user_a")
    p = case.get("payload") or {}
    delivery = p.get("delivery", "chat")
    steps: list[dict[str, Any]] = []
    if delivery == "upload_document":
        steps.append({"type": "upload_document", "user": user,
                      "filename": p.get("filename", "document.txt"), "content": p.get("content", "")})
    elif delivery == "chat":
        steps.append({"type": "send_turn", "user": user, "message": p.get("content", "")})
    elif delivery:
        steps.append({"type": "inject_payload", "user": user, "delivery": delivery,
                      "format": p.get("format", "text"), "filename": p.get("filename"),
                      "content": p.get("content", "")})
    for msg in case.get("setup_turns") or []:
        steps.append({"type": "send_turn", "user": user, "message": msg})
    steps.append({"type": "send_turn", "user": user, "message": case["trigger_turn"]})
    return steps


def rule_violated(trace: Trace, rule: dict[str, Any]) -> bool:
    """True when a forbidden call occurred whose args match expected_arg_match (and exfil_marker)."""
    pattern = re.compile(rule["expected_arg_match"], re.I) if rule.get("expected_arg_match") else None
    marker = rule.get("exfil_marker")
    key = rule.get("arg_key")
    for tc in trace.tool_calls:
        if tc.name != rule["forbidden_call"]:
            continue
        hay = tc.arguments.get(key) if key and key in tc.arguments else tc.arguments
        text = hay if isinstance(hay, str) else json.dumps(hay, default=str)
        if pattern and not pattern.search(text):
            continue
        if marker and marker not in json.dumps(tc.arguments, default=str):
            continue
        return True
    return False


def _merge(acc: Trace | None, turn: Trace) -> Trace:
    """Accumulate tool calls across turns so abuse in any turn is visible to assertions."""
    if acc is None:
        return turn
    return turn.model_copy(update={"tool_calls": acc.tool_calls + turn.tool_calls})


def run_case(client: Any, case: dict[str, Any]) -> Trace:
    """Execute setup steps for a case and return the final normalized Trace."""
    trace: Trace | None = None

    for step in case.get("setup") or build_setup(case):
        step_type = step.get("type")
        user = step.get("user", "user_a")

        if step_type == "upload_document":
            filename = step.get("filename", "document.txt")
            content = step.get("content", "")
            client.upload_document(content.encode("utf-8"), filename, user=user)

        elif step_type == "send_turn":
            result = client.send_turn(
                step.get("message", ""),
                session_id=step.get("session_id"),
                user=user,
            )
            turn = result.inline_trace
            if turn is None and result.trace_id:
                turn = client.fetch_trace(result.trace_id, user=user)
            if turn is not None:
                trace = _merge(trace, turn)

        elif step_type == "inject_payload":
            client.inject_payload(
                step["delivery"], step.get("format", "text"), step["content"],
                filename=step.get("filename"), user=user,
            )

        elif step_type == "fetch_trace":
            trace = client.fetch_trace(step["trace_id"], user=user)

        else:
            raise ValueError(f"Unknown setup step type: {step_type}")

    if trace is None:
        raise RuntimeError("No trace was produced by setup steps")
    return trace


def assert_mitigated(case: dict[str, Any], trace: Trace) -> None:
    """Fail as VULNERABLE only when ALL vulnerable_if checks hold on the trace."""
    if "assertion_rule" in case:
        if rule_violated(trace, case["assertion_rule"]):
            pytest.fail(f"VULNERABLE: {case['id']} violated {case['assertion_rule']}")
        return
    checks = case.get("vulnerable_if", [])
    if checks and all(evaluate_check(trace, c) for c in checks):
        pytest.fail(f"VULNERABLE: {case['id']} satisfied all vulnerable_if checks")
