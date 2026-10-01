"""Root conftest: runs the suite against a local mock agent unless AUDIT_LIVE=1."""
from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from core.config import TargetConfig, load_config

ROOT = Path(__file__).parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def mock_agent_url():
    from tests.mock_agent import app

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("mock agent failed to start")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def config(request) -> TargetConfig:
    """Mock-agent config by default; set AUDIT_LIVE=1 to use config/target_agent.yaml."""
    cfg = load_config(ROOT / "config" / "target_agent.yaml")
    if os.environ.get("AUDIT_LIVE") == "1":
        return cfg
    url = request.getfixturevalue("mock_agent_url")
    cfg.base_url = url
    cfg.scope.allowed_hosts = ["127.0.0.1"]
    cfg.trace.source = "api"
    for name, token in (("user_a", "token-a"), ("user_b", "token-b")):
        cfg.users[name].auth_headers = {"X-Session-Token": token}
        cfg.users[name].session_token = token
    paths = {"document_upload": "/upload", "chat": "/chat", "webhook_mock": "/webhook/mock",
             "trace": "/trace/{trace_id}"}
    for key, path in paths.items():
        cfg.endpoints[key].path = path
    return cfg


@pytest.fixture(autouse=True)
def _reset_mock(request):
    if "mock_agent_url" in request.fixturenames or os.environ.get("AUDIT_LIVE") == "1":
        return
    if request.node.get_closest_marker("no_mock"):
        return
    if "client" in request.fixturenames:
        import httpx
        url = request.getfixturevalue("mock_agent_url")
        httpx.post(f"{url}/reset")
