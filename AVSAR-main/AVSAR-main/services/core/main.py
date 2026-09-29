"""AVSAR core API — FastAPI application factory.

ARCHITECTURE.md §1 rule: `services/core` is the single source of truth; the
Next.js app never talks to gov portals or LLM providers directly (RULE 8 —
all provider egress originates here).
"""

from __future__ import annotations

import logging
import threading
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings
from core.errors import error_payload
from core.logging_setup import setup_logging
from core.metrics import incr

setup_logging(settings.log_level)
log = logging.getLogger("avsar.core")

DESCRIPTION = """
Jeevikasetu — voice-first livelihood mapping and skilling platform.

Voice-first aspiration capture for PM-AJAY Grant-in-Aid skilling, mapped to
NSQF Qualification Packs. All business logic, provider egress and government
data access lives in this service.
"""
API_PREFIX = "/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="AVSAR Core API",
        version="1.0.0",
        description=DESCRIPTION,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from core.api import health

    app.include_router(health.router, prefix=API_PREFIX)

    for module_path in (
        "core.api.auth", "core.api.sessions", "core.api.districts",
        "core.api.recommendations", "core.api.dashboard", "core.api.exports",
        "core.api.admin", "core.api.live_check",
    ):
        _include_optional(app, module_path, API_PREFIX)

    @app.middleware("http")
    async def redirect_legacy_api(request: Request, call_next):
        """Keep the cutover compatible without registering duplicate routes."""
        path = request.url.path
        if path != "/" and not path.startswith(API_PREFIX + "/") and path not in {"/docs", "/openapi.json", "/redoc"}:
            target = f"{API_PREFIX}{path}"
            if request.url.query:
                target = f"{target}?{request.url.query}"
            return RedirectResponse(target, status_code=307)
        return await call_next(request)

    @app.middleware("http")
    async def count_requests(request: Request, call_next):
        response = await call_next(request)
        incr("http_requests_total", path=request.url.path.split("?")[0], method=request.method)
        return response

    def _lang_of(request: Request) -> str:
        lang = request.headers.get("x-avsar-lang") or request.query_params.get("lang") or "hi"
        return lang if lang in ("hi", "mr", "te", "en") else "hi"

    @app.exception_handler(SQLAlchemyError)
    async def database_down(request: Request, exc: SQLAlchemyError):
        """A dead database must produce a sentence the UI can SPEAK.

        Starlette only routes unhandled exceptions to a handler registered for
        the exception *class*; registering for the status code 500 does not fire,
        which is how this path previously returned an empty 500 body. The kill
        drill catches exactly that.
        """
        log.error("database unavailable: %s", type(exc).__name__, extra={"event": "db_down"})
        incr("db_unavailable_total")
        return JSONResponse(
            status_code=503,
            content={"detail": error_payload("db_unavailable", _lang_of(request))},
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        """Never leak a traceback to a beneficiary; always say something."""
        log.exception("unhandled error")
        incr("unhandled_errors_total")
        return JSONResponse(
            status_code=500,
            content={"detail": error_payload("network_error", _lang_of(request))},
        )

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "service": "jeevikasetu-core",
            "version": "1.0.0",
            "docs": "/docs",
            "health": f"{API_PREFIX}/healthz",
            "ready": f"{API_PREFIX}/readyz",
        }

    @app.on_event("startup")
    async def warm_start() -> None:
        """Pre-load the embedder off the request path.

        ARCHITECTURE.md §10 keeps embedding out of request time ("embeddings
        computed in pipelines, not at request time"). The retrieval path still
        has to embed the *query*, and the sentence-transformer load is lazy, so
        without this the first turn after a cold start absorbs the model load.
        Measured before this change: retrieval p95 11,268 ms against a 500 ms
        budget, entirely the first call. It runs in a daemon thread so the
        container reports healthy immediately, and a failure only means the
        first query pays the load — never a boot failure.
        """
        if not settings.warm_start:
            return

        def _warm() -> None:
            try:
                from core.rag.embedder import get_embedder

                started = time.monotonic()
                get_embedder().encode_query("warm start")
                log.info(
                    "embedder warm",
                    extra={"event": "warm_start", "latency_ms": round((time.monotonic() - started) * 1000, 1)},
                )
            except Exception as exc:
                log.warning("warm start skipped: %s: %s", type(exc).__name__, exc)

        threading.Thread(target=_warm, name="avsar-warm-start", daemon=True).start()

    log.info(
        "core started",
        extra={"event": "startup", "provider": settings.voice_provider},
    )
    return app


def _include_optional(app: FastAPI, module_path: str, prefix: str = "") -> None:
    """Include a router if the module exists yet (gates land incrementally)."""
    try:
        module = __import__(module_path, fromlist=["router"])
    except ImportError:
        log.info("router not present yet: %s", module_path, extra={"event": "router_skip"})
        return
    app.include_router(module.router, prefix=prefix)


app = create_app()
