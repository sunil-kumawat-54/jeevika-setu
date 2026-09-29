"""Phase 1 contract checks for the single versioned API authority."""

from __future__ import annotations

import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]


def test_versioned_health_contract(client):
    response = client.get("/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "jeevikasetu-core",
        "env": "test",
    }


def test_unversioned_health_route_is_not_public(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert "/healthz" not in client.get("/openapi.json").json()["paths"]


def test_versioned_session_route_is_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert "/v1/sessions" in paths
    assert "/sessions" not in paths


def test_versioned_readiness_has_stable_check_envelope(client, monkeypatch):
    monkeypatch.setattr("core.db.ping", lambda: True)
    monkeypatch.setattr("core.db.pgvector_available", lambda: True)
    monkeypatch.setattr("redis.Redis.from_url", lambda *args, **kwargs: type("Redis", (), {"ping": lambda self: True})())
    response = client.get("/v1/readyz")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "checks"}
    assert set(body["checks"]) >= {"database", "pgvector", "redis", "speech", "llm"}


def test_contract_has_one_documented_versioned_route_family(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert paths
    assert all(path.startswith("/v1/") for path in paths)


def test_migration_map_has_one_canonical_runtime_owner():
    mapping = (REPO / "docs/jeevikasetu-migration-map.md").read_text(encoding="utf-8")
    assert "AVSAR FastAPI, PostgreSQL, and the Next.js BFF are the only active runtime" in mapping
    assert "KaushalVani-main/backend/src/index.ts" in mapping
    assert "KaushalVani-main/ai-service/main.py" in mapping
    assert "Generated QPs, fixed distances, salaries, grants" in mapping
    assert "decimal NSQF" in mapping
    assert "QP version" in mapping
    assert mapping.count("Canonical owner") == 1


def test_source_snapshot_manifest_covers_both_reference_trees():
    manifest = REPO.parents[1] / ".planning/source-snapshot-manifest.json"
    payload = __import__("json").loads(manifest.read_text(encoding="utf-8"))
    roots = {tree["root"] for tree in payload["trees"]}
    assert roots == {"AVSAR-main/AVSAR-main", "KaushalVani-main/KaushalVani-main"}
