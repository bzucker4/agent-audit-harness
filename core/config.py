from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class UserConfig(BaseModel):
    """Authentication configuration for a simulated user."""

    auth_headers: dict[str, str] = Field(default_factory=dict)
    session_token: str | None = None


class ToolDef(BaseModel):
    """Declared tool metadata from the target agent."""

    name: str
    description: str = ""
    args_schema: dict[str, Any] = Field(default_factory=dict)
    sensitive: bool = False


class Endpoint(BaseModel):
    """HTTP endpoint configuration."""

    path: str
    method: str = "POST"


class TraceConfig(BaseModel):
    """Trace source configuration."""

    source: Literal["api", "langfuse", "otel", "burp_export", "file"] = "api"
    url: str | None = None
    path: str | None = None


class Scope(BaseModel):
    """Fixed-scope guardrails."""

    allowed_hosts: list[str] = Field(default_factory=list)
    engagement_id: str = ""


class TargetConfig(BaseModel):
    """Full target agent configuration."""

    base_url: str
    timeout: float = 10.0
    users: dict[str, UserConfig]
    tools: list[ToolDef] = Field(default_factory=list)
    endpoints: dict[str, Endpoint]
    trace: TraceConfig = Field(default_factory=TraceConfig)
    scope: Scope = Field(default_factory=Scope)


def _expand_env(value: Any) -> Any:
    """Recursively expand ${ENV} style placeholders in strings."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    return value


def load_config(path: str | Path) -> TargetConfig:
    """Load and validate target configuration from YAML."""
    data = yaml.safe_load(Path(path).read_text())
    data = _expand_env(data)
    return TargetConfig.model_validate(data)
