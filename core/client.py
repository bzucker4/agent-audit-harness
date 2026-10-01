from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from core.config import Endpoint, TargetConfig
from core.models import Trace, parse_trace


class TurnResult(BaseModel):
    """Result from a chat/completion turn."""

    response_text: str
    session_id: str | None = None
    trace_id: str | None = None
    inline_trace: Trace | None = None


class AgentClient:
    """HTTP client wrapper for interacting with the target agent's API."""

    def __init__(self, config: TargetConfig, user: str = "user_a", client: httpx.Client | None = None):
        self.config = config
        self.user = user
        self.captured: list[dict[str, Any]] = []
        self._client = client or httpx.Client(timeout=config.timeout)

    def __enter__(self) -> "AgentClient":
        return self

    def __exit__(self, exc_type, exc, tb):
        self._client.close()

    def _headers(self, user: str) -> dict[str, str]:
        """Build request headers for a configured user."""
        if user not in self.config.users:
            raise ValueError(f"Unknown user: {user}")
        user_config = self.config.users[user]
        headers = dict(user_config.auth_headers)
        if user_config.session_token:
            headers.setdefault("Authorization", f"Bearer {user_config.session_token}")
        return headers

    def _enforce_scope(self, url: str) -> None:
        """Refuse to make requests to hosts outside the fixed scope."""
        host = urlparse(url).hostname
        if host is None or host not in self.config.scope.allowed_hosts:
            raise ValueError(
                f"Host '{host}' is not in the fixed-scope allowed_hosts: {self.config.scope.allowed_hosts}"
            )

    def _request(self, method: str, endpoint: Endpoint, user: str, **kwargs: Any) -> httpx.Response:
        """Build, capture, and send an HTTP request within scope."""
        if endpoint.path.startswith("http"):
            url = endpoint.path
        else:
            base = self.config.base_url.rstrip("/")
            path = endpoint.path if endpoint.path.startswith("/") else f"/{endpoint.path}"
            url = base + path

        self._enforce_scope(url)

        headers = kwargs.pop("headers", {})
        headers.update(self._headers(user))

        request = self._client.build_request(method, url, headers=headers, **kwargs)
        capture_request = {
            "method": method,
            "url": url,
            "headers": dict(request.headers),
            "body": request.read().decode(errors="replace")[:5000],
        }
        response = self._client.send(request)
        capture_response = {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:5000],
        }
        self.captured.append({"request": capture_request, "response": capture_response})
        response.raise_for_status()
        return response

    def upload_document(self, path_or_bytes: str | Path | bytes, filename: str, user: str = "user_a") -> dict:
        """Upload a document as an attachment."""
        endpoint = self.config.endpoints["document_upload"]
        if isinstance(path_or_bytes, (str, Path)):
            content = Path(path_or_bytes).read_bytes()
        else:
            content = path_or_bytes
        files = {"file": (filename, content)}
        response = self._request(endpoint.method, endpoint, user, files=files)
        return response.json()

    def inject_payload(
        self, delivery: str, fmt: str, content: str, filename: str | None = None, user: str = "user_a"
    ) -> dict:
        """Deliver a poisoned email/calendar/tool-response/memory item via the webhook mock ingress."""
        endpoint = self.config.endpoints["webhook_mock"]
        body = {"delivery": delivery, "format": fmt, "filename": filename, "content": content}
        return self._request(endpoint.method, endpoint, user, json=body).json()

    def send_turn(self, message: str, session_id: str | None = None, user: str = "user_a") -> TurnResult:
        """Send a chat message and parse the returned turn result."""
        endpoint = self.config.endpoints["chat"]
        payload: dict[str, Any] = {"message": message}
        if session_id is not None:
            payload["session_id"] = session_id

        response = self._request(endpoint.method, endpoint, user, json=payload)
        data = response.json()

        inline_trace = None
        if data.get("trace"):
            inline_trace = parse_trace(data["trace"], "api")

        return TurnResult(
            response_text=data.get("response") or data.get("text") or data.get("message") or "",
            session_id=data.get("session_id"),
            trace_id=data.get("trace_id"),
            inline_trace=inline_trace,
        )

    def fetch_trace(self, trace_id: str, user: str = "user_a") -> Trace:
        """Fetch and normalize a trace according to the configured trace source."""
        trace_config = self.config.trace
        source = trace_config.source

        if source == "api":
            endpoint = self.config.endpoints["trace"]
            path = endpoint.path.replace("{trace_id}", trace_id)
            response = self._request(endpoint.method, Endpoint(path=path, method=endpoint.method), user)
            return parse_trace(response.json(), "api")

        if source == "langfuse":
            base = trace_config.url or self.config.base_url.rstrip("/")
            path = trace_config.path or f"/api/public/observations?traceId={trace_id}"
            endpoint = Endpoint(path=path, method="GET")
            response = self._request("GET", endpoint, user)
            return parse_trace(response.json(), "langfuse")

        if source == "otel":
            base = trace_config.url or self.config.base_url.rstrip("/")
            path = trace_config.path or f"/v1/traces/{trace_id}"
            endpoint = Endpoint(path=path, method="GET")
            response = self._request("GET", endpoint, user)
            return parse_trace(response.json(), "otel")

        if source in ("burp_export", "file"):
            raw_payload: Any
            if trace_config.url and trace_config.url.startswith("http"):
                response = self._request("GET", Endpoint(path=trace_config.url, method="GET"), user)
                raw_payload = response.json()
            elif trace_config.path:
                raw_payload = json.loads(Path(trace_config.path).read_text())
            else:
                raise ValueError("No trace.url or trace.path configured for file/Burp import")
            return parse_trace(raw_payload, source)

        raise ValueError(f"Unsupported trace source: {source}")
