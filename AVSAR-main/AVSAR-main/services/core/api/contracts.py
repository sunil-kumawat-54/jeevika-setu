"""Stable machine-readable envelopes for the public Jeevikasetu API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str = "jeevikasetu-core"
    env: str


class DependencyCheck(BaseModel):
    ok: bool
    provider: str | None = None
    degraded: bool | None = None
    latency_ms: float | None = None
    detail: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, dict[str, Any]]


class SessionResponse(BaseModel):
    session_id: str
    state: dict[str, Any]
