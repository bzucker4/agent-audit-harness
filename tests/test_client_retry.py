from __future__ import annotations

import httpx
import pytest

from core.client import AgentClient, TargetAgentUnavailableError
from core.config import Endpoint, TargetConfig, UserConfig


def make_client(statuses: list[int | Exception]) -> tuple[AgentClient, list[int]]:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        item = statuses[len(calls)] if len(calls) < len(statuses) else statuses[-1]
        calls.append(1)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(item, json={"ok": True})

    cfg = TargetConfig(
        base_url="http://127.0.0.1:9",
        users={"user_a": UserConfig(session_token="t")},
        endpoints={"chat": Endpoint(path="/chat")},
        scope={"allowed_hosts": ["127.0.0.1"]},
    )
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return AgentClient(cfg, client=http, backoff_initial=0, backoff_max=0), calls


def call(client: AgentClient):
    return client._request("POST", client.config.endpoints["chat"], "user_a", json={})


@pytest.mark.parametrize("status", [429, 503, 504])
def test_transient_status_then_success(status):
    client, calls = make_client([status, 200])
    assert call(client).status_code == 200
    assert len(calls) == 2


def test_exhausted_retries_raise_descriptive_error():
    client, calls = make_client([429])
    with pytest.raises(TargetAgentUnavailableError) as exc:
        call(client)
    assert len(calls) == 3
    assert exc.value.status_code == 429 and exc.value.attempts == 3
    assert "/chat" in str(exc.value)


def test_network_error_is_retried():
    client, calls = make_client([httpx.ConnectTimeout("slow"), 200])
    assert call(client).status_code == 200
    assert len(calls) == 2


def test_non_transient_error_not_retried():
    client, calls = make_client([404])
    with pytest.raises(httpx.HTTPStatusError):
        call(client)
    assert len(calls) == 1
