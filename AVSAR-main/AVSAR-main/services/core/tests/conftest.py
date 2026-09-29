"""Shared pytest fixtures.

Every test runs in full mock mode (RULE 1): no network, no API keys, no
government-site access.
"""

from __future__ import annotations

import os

os.environ.setdefault("VOICE_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("ENV", "test")

import pytest  # noqa: E402


def _db_url() -> str:
    return os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://avsar:avsar@localhost:5432/avsar"
    )


os.environ["DATABASE_URL"] = _db_url()


@pytest.fixture(scope="session")
def db_available() -> bool:
    """True when a live Postgres is reachable; DB tests skip otherwise."""
    try:
        from core.db import ping

        return ping()
    except Exception:
        return False


@pytest.fixture()
def db_session(db_available):
    if not db_available:
        pytest.skip("Postgres not reachable — start it with `make up`")
    from core.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _no_live_provider_credentials(monkeypatch):
    """RULE 1: the suite runs with ZERO API keys, whatever is in the developer's
    .env.

    Without this, a machine with a real SARVAM_API_KEY makes live, billable
    calls during unit tests: the router's fallback ladder builds a real adapter
    for the next rung, so a test that means "the primary fails, mock answers"
    silently reaches the internet instead. Caught when Sarvam went live —
    ``test_router_falls_through_to_mock_when_the_primary_fails`` began returning
    an empty transcript from a genuine Sarvam request_id.

    Adapters read credentials from ``settings``, not from os.environ, so both
    are cleared. Tests that need a key pass one explicitly to the adapter.
    """
    from core.config import settings

    for field in ("sarvam_api_key", "bhashini_api_key", "bhashini_user_id", "azure_speech_key"):
        monkeypatch.setattr(settings, field, "", raising=False)
    for var in ("SARVAM_API_KEY", "BHASHINI_API_KEY", "BHASHINI_USER_ID", "AZURE_SPEECH_KEY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Give every test a fresh rate-limit budget.

    The limiter is real (Redis-backed, in-process fallback) and shared across
    the process, so without this one test's traffic exhausts the next test's
    budget and everything downstream fails with 429. Tests that assert the
    limiter *does* fire drive it deliberately.
    """
    from core.api import ratelimit

    def _clear():
        ratelimit.reset()
        try:
            client = ratelimit._redis()
            if client is not None:
                keys = list(client.scan_iter("avsar:rl:*"))
                if keys:
                    client.delete(*keys)
        except Exception:
            pass

    _clear()
    yield
    _clear()


@pytest.fixture()
def client():
    """FastAPI TestClient over the real app object."""
    from fastapi.testclient import TestClient

    from core.main import app

    with TestClient(app) as c:
        yield c
