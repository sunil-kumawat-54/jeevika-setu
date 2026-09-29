"""Health endpoints. ARCHITECTURE.md §5: `/healthz` liveness, `/readyz` pings
DB + providers (mock counts as OK)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Response

from core import db as dbmod
from core.api.contracts import HealthResponse, ReadyResponse
from core.config import settings
from core.metrics import prometheus_text

log = logging.getLogger("avsar.health")
router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Liveness — process is up. Never touches the DB."""
    return HealthResponse(status="ok", env=settings.env)


@router.get("/readyz", response_model=ReadyResponse)
def readyz(response: Response) -> ReadyResponse:
    """Readiness — DB reachable, pgvector installed, redis reachable, speech
    provider resolvable. A `mock` provider counts as healthy by design."""
    checks: dict[str, dict] = {}
    healthy = True

    try:
        dbmod.ping()
        checks["database"] = {"ok": True}
    except Exception as exc:  # pragma: no cover - exercised by the kill drill
        healthy = False
        checks["database"] = {"ok": False, "error": type(exc).__name__}

    try:
        checks["pgvector"] = {"ok": dbmod.pgvector_available()}
        healthy = healthy and checks["pgvector"]["ok"]
    except Exception as exc:
        healthy = False
        checks["pgvector"] = {"ok": False, "error": type(exc).__name__}

    try:
        import redis as redis_lib

        client = redis_lib.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        checks["redis"] = {"ok": True}
    except Exception as exc:
        healthy = False
        checks["redis"] = {"ok": False, "error": type(exc).__name__}

    # Speech: a `mock` provider counts as healthy (ARCHITECTURE.md §5).
    try:
        from core.speech.router import get_router

        checks["speech"] = get_router().health()
    except ImportError:
        provider = settings.voice_provider.lower()
        checks["speech"] = {"ok": provider in {"mock", "bhashini", "sarvam", "azure"}, "provider": provider}
    except Exception as exc:
        checks["speech"] = {"ok": False, "error": type(exc).__name__}
    healthy = healthy and bool(checks["speech"].get("ok"))

    checks["llm"] = {"ok": True, "provider": settings.llm_provider}

    status = "healthy" if healthy else "degraded"
    if not healthy:
        response.status_code = 503
    return ReadyResponse(status=status, checks=checks)


@router.get("/metrics")
def metrics() -> Response:
    return Response(content=prometheus_text(), media_type="text/plain; version=0.0.4")
