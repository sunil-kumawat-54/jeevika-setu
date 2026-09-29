"""Gate 0 — scaffold + infrastructure acceptance tests.

These assert the *behaviour* the gate demands, not merely that files exist:
the app boots, /healthz answers, /readyz genuinely pings Postgres + pgvector +
Redis, and the repository layout matches ARCHITECTURE.md section 1.
"""

from __future__ import annotations

import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


def test_healthz_reports_service_up(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "jeevikasetu-core"


def test_readyz_checks_every_dependency(client, db_available):
    if not db_available:
        pytest.skip("Postgres not reachable — start it with `make up`")
    resp = client.get("/readyz")
    body = resp.json()
    assert resp.status_code == 200, body
    assert body["status"] == "healthy"
    for dep in ("database", "pgvector", "redis", "speech", "llm"):
        assert body["checks"][dep]["ok"] is True, f"{dep} not ready: {body['checks'][dep]}"


def test_readyz_confirms_pgvector_extension_installed(db_session):
    from sqlalchemy import text

    version = db_session.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).scalar()
    assert version is not None, "pgvector extension missing from the database"


def test_postgres_is_major_version_16(db_session):
    from sqlalchemy import text

    raw = db_session.execute(text("SHOW server_version")).scalar()
    assert raw.split(".")[0] == "16", f"TECH_STACK section 1 pins PostgreSQL 16, got {raw}"


def test_metrics_endpoint_is_prometheus_format(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "avsar_" in resp.text


@pytest.mark.parametrize(
    "relpath",
    [
        "apps/web",
        "services/core/api",
        "services/core/domain",
        "services/core/llm",
        "services/core/speech",
        "services/core/rag",
        "services/core/models",
        "pipelines",
        "data/crosswalk",
        "data/prompts",
        "seeds",
        "infra",
        "scripts",
        "docs",
    ],
)
def test_monorepo_layout_matches_architecture_section_1(relpath):
    assert (REPO / relpath).is_dir(), f"ARCHITECTURE.md section 1 requires {relpath}/"


@pytest.mark.parametrize(
    "relpath",
    ["Makefile", ".env.example", "infra/docker-compose.yml", "infra/nginx.conf",
     ".github/workflows/ci.yml", "pyproject.toml"],
)
def test_required_root_files_exist(relpath):
    assert (REPO / relpath).is_file(), f"missing required file {relpath}"


@pytest.mark.parametrize(
    "target",
    ["up", "dev", "test", "ingest", "seed", "drill", "grounding", "mock-on", "mock-off"],
)
def test_makefile_declares_every_mandated_target(target):
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    assert f"\n{target}:" in text, f"TECH_STACK section 7 requires `make {target}`"


def test_env_example_documents_every_setting_field():
    """RULE 9 — .env.example must document every variable the system reads."""
    from core.config import Settings

    env_text = (REPO / ".env.example").read_text(encoding="utf-8")
    documented = {
        line.split("=", 1)[0].strip().lower()
        for line in env_text.splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }
    missing = [name for name in Settings.model_fields if name not in documented]
    assert not missing, f".env.example is missing: {missing}"


def test_no_secrets_committed():
    """RULE 9 — .env must be gitignored and contain no real keys in the example."""
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in gitignore, ".env must be gitignored"
    example = (REPO / ".env.example").read_text(encoding="utf-8")
    for secret_var in ("ANTHROPIC_API_KEY", "BHASHINI_API_KEY", "SARVAM_API_KEY", "AZURE_SPEECH_KEY"):
        line = next(ln for ln in example.splitlines() if ln.strip().startswith(secret_var))
        value = line.split("=", 1)[1].strip()
        assert value == "", f"{secret_var} must ship empty in .env.example, got {value!r}"


def test_compose_declares_healthchecks_for_every_service():
    import yaml

    compose = yaml.safe_load((REPO / "infra/docker-compose.yml").read_text(encoding="utf-8"))
    for svc in ("db", "redis", "core", "web"):
        assert svc in compose["services"], f"docker-compose must define {svc}"
        assert "healthcheck" in compose["services"][svc], f"{svc} needs a healthcheck"
    assert "pgvector" in compose["services"]["db"]["image"]
    assert compose["services"]["redis"]["image"].startswith("redis:7")


def test_ci_runs_ruff_pytest_and_next_build():
    ci = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "ruff check" in ci
    assert "pytest" in ci
    assert "npm run build" in ci


def test_phase1_preflight_is_portable():
    preflight = REPO / "scripts/preflight_phase1.py"
    assert preflight.is_file()
    source = preflight.read_text(encoding="utf-8")
    assert "BLOCKED_RUNTIME" in source
    assert "shutil.which(\"docker\")" in source
    assert "shutil.which(\"make\")" in source
