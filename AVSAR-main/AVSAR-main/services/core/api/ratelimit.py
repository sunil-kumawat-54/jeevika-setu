"""Redis token bucket for ``/auth/*`` and ``/sessions/*/turn``.

TECH_STACK.md section 9: *"CORS locked to web origin; rate-limit /auth/* and
/sessions/*/turn via Redis token bucket."*

Degradation matters here. If Redis is down mid-demo, the correct behaviour is
**not** to lock every caller out — that would turn a cache outage into a total
outage. The limiter falls back to an in-process counter and logs the
degradation; the kill-drill exercises exactly this.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

from fastapi import Request

from core.config import settings
from core.errors import AvsarError
from core.metrics import incr

log = logging.getLogger("avsar.ratelimit")

WINDOW_S = 60

_LOCAL_LOCK = threading.Lock()
_LOCAL: dict[str, list[float]] = defaultdict(list)
_redis_client = None
_redis_failed_at: float = 0.0
#: After a Redis failure, stop retrying for this long so every request does not
#: pay a connection timeout.
_REDIS_COOLDOWN_S = 30.0


def _redis():
    global _redis_client, _redis_failed_at
    if _redis_failed_at and time.monotonic() - _redis_failed_at < _REDIS_COOLDOWN_S:
        return None
    if _redis_client is None:
        try:
            import redis as redis_lib

            _redis_client = redis_lib.Redis.from_url(
                settings.redis_url, socket_connect_timeout=1, socket_timeout=1
            )
            _redis_client.ping()
            _redis_failed_at = 0.0
        except Exception as exc:
            log.warning("rate limiter falling back to in-process counters: %s", exc)
            _redis_client = None
            _redis_failed_at = time.monotonic()
    return _redis_client


def _client_key(request: Request, bucket: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "?")
    auth = request.headers.get("authorization", "")
    # Authenticated callers get their own bucket so one busy NAT does not starve
    # everyone behind it.
    subject = auth[-24:] if auth else ip
    return f"avsar:rl:{bucket}:{subject}"


def _allow_local(key: str, limit: int) -> bool:
    now = time.monotonic()
    with _LOCAL_LOCK:
        hits = [t for t in _LOCAL[key] if now - t < WINDOW_S]
        if len(hits) >= limit:
            _LOCAL[key] = hits
            return False
        hits.append(now)
        _LOCAL[key] = hits
        return True


def check(request: Request, bucket: str, limit: int) -> None:
    """Raise 429 with a speakable body when the bucket is exhausted."""
    if limit <= 0:
        return
    key = _client_key(request, bucket)

    client = _redis()
    allowed: bool
    if client is not None:
        try:
            pipe = client.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, WINDOW_S)
            count = pipe.execute()[0]
            allowed = int(count) <= limit
        except Exception as exc:
            log.warning("redis rate-limit failed, using local counter: %s", exc)
            globals()["_redis_client"] = None
            globals()["_redis_failed_at"] = time.monotonic()
            allowed = _allow_local(key, limit)
    else:
        allowed = _allow_local(key, limit)

    if not allowed:
        incr("rate_limited_total", bucket=bucket)
        lang = request.headers.get("x-avsar-lang", "hi")
        raise AvsarError(429, "rate_limited", lang, f"limit {limit}/min on {bucket}")


def rate_limit(bucket: str, limit: int):
    """FastAPI dependency factory."""

    def dependency(request: Request) -> None:
        check(request, bucket, limit)

    return dependency


def reset() -> None:
    """Test helper — clears the in-process counters."""
    with _LOCAL_LOCK:
        _LOCAL.clear()
