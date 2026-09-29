"""Gate 10 — hardening: retention, latency instrumentation, error contract.

PLAN.md section 14 definition of done, the items this file exercises:

* "Kill-a-service drill passes (network off -> template mode; DB down ->
  readable error + recovery)" — the drill itself is ``make drill``; here we pin
  the *contract* the drill checks, so a regression fails in CI and not only in
  the drill.
* ARCHITECTURE.md section 11: "Retention: sessions purgeable by script after N
  days (scripts/purge_old.py)".
* TECH_STACK.md section 8: per-stage instrumentation emitted to ``/metrics``
  with p50/p95.

The purge test builds its own back-dated session and deletes only that, so it
never touches the demo data the dashboard story depends on.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import sys
import uuid

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


def _load_script(name: str):
    """Import a script from ``scripts/`` by path (it is not an installed module)."""
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_script_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Retention — ARCHITECTURE.md section 11
# ---------------------------------------------------------------------------


@pytest.fixture()
def aged_session(db_session):
    """A complete session (consent + transcript + recommendation), back-dated."""
    from core.models.tables import Channel, Consent, ConsentMode, Course, Recommendation, Transcript
    from core.models.tables import Session as SessionRow

    course = db_session.query(Course).first()
    if course is None:
        pytest.skip("no courses seeded — run `make seed`")

    old = dt.datetime.now(dt.UTC) - dt.timedelta(days=400)
    session = SessionRow(
        id=uuid.uuid4(),
        channel=Channel.demo,
        lang="hi",
        state={},
        district_code=None,
        created_at=old,
    )
    db_session.add(session)
    db_session.flush()

    consent = Consent(
        session_id=session.id, mode=ConsentMode.tapped, granted=True, playback_ref="test"
    )
    db_session.add(consent)
    db_session.flush()
    session.consent_id = consent.id

    db_session.add(
        Transcript(
            session_id=session.id,
            turn_no=1,
            asr_provider="mock",
            raw_text="retention test",
            confidence=1.0,
            parsed_slots={},
            latency_ms=12,
        )
    )
    db_session.add(
        Recommendation(session_id=session.id, rank=1, course_id=course.id, score=0.5, factors={})
    )
    db_session.commit()

    yield session.id

    # Belt and braces: if the purge under test failed, do not leave the row behind.
    from sqlalchemy import delete

    db_session.execute(
        SessionRow.__table__.update().where(SessionRow.id == session.id).values(consent_id=None)
    )
    for model in (Transcript, Recommendation, Consent):
        db_session.execute(delete(model).where(model.session_id == session.id))
    db_session.execute(delete(SessionRow).where(SessionRow.id == session.id))
    db_session.commit()


def test_purge_dry_run_deletes_nothing(db_session, aged_session):
    """The default is a dry run: it must report the row and keep it."""
    from core.models.tables import Session as SessionRow

    purge_old = _load_script("purge_old")
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=90)

    plan = purge_old.survey(db_session, cutoff)
    assert aged_session in plan["ids"], "a 400-day-old session must be in scope at 90 days"
    assert plan["transcripts"] >= 1
    assert plan["recommendations"] >= 1
    assert plan["consents"] >= 1

    assert db_session.get(SessionRow, aged_session) is not None, "survey must not delete"


def test_purge_removes_session_and_children_and_audits_itself(db_session, aged_session):
    """ARCHITECTURE.md S11 — the session and everything bound to it goes."""
    from sqlalchemy import select

    from core.models.tables import AuditLog, Consent, Recommendation, Transcript
    from core.models.tables import Session as SessionRow

    purge_old = _load_script("purge_old")
    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=90)

    audits_before = db_session.scalar(
        select(Transcript.id).where(Transcript.session_id == aged_session)
    )
    assert audits_before is not None, "fixture did not create a transcript"

    result = purge_old.purge(db_session, cutoff, orphan_users=False)
    db_session.commit()

    assert result["sessions"] >= 1
    assert db_session.get(SessionRow, aged_session) is None, "session row survived the purge"
    for model in (Transcript, Recommendation, Consent):
        left = db_session.scalar(
            select(model.id).where(model.session_id == aged_session)
        )
        assert left is None, f"{model.__tablename__} row survived the purge"

    # The purge audits itself, so the retention action stays demonstrable.
    audit = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.action == "retention_purge")
        .order_by(AuditLog.id.desc())
    ).first()
    assert audit is not None, "purge must write an audit_log row"
    assert audit.entity == "sessions"
    assert audit.before and "cutoff" in audit.before


def test_purge_keeps_the_audit_trail(db_session):
    """The accountability trail is explicitly out of scope for the purge."""
    from sqlalchemy import func, select

    from core.models.tables import AuditLog

    purge_old = _load_script("purge_old")
    before = db_session.scalar(select(func.count()).select_from(AuditLog))

    purge_old.purge(db_session, dt.datetime.now(dt.UTC) - dt.timedelta(days=3650), False)
    db_session.commit()

    after = db_session.scalar(select(func.count()).select_from(AuditLog))
    assert after >= before, "audit_log must never shrink from a retention purge"


def test_retention_default_comes_from_settings():
    """`make purge` must default to the documented RETENTION_DAYS, not a literal."""
    from core.config import settings

    assert settings.retention_days == 90


# ---------------------------------------------------------------------------
# Latency instrumentation — TECH_STACK.md section 8
# ---------------------------------------------------------------------------


def test_every_documented_stage_is_exported_with_p50_p95():
    from core import metrics

    metrics.reset()
    for stage in metrics.STAGES:
        metrics.observe(stage, 100.0)
        metrics.observe(stage, 200.0)

    text = metrics.prometheus_text()
    for stage in metrics.STAGES:
        assert f'avsar_stage_latency_ms_p50{{stage="{stage}"}}' in text
        assert f'avsar_stage_latency_ms_p95{{stage="{stage}"}}' in text
        assert f'avsar_stage_latency_ms_max{{stage="{stage}"}}' in text
        assert f'avsar_stage_observations{{stage="{stage}"}}' in text


def test_latency_report_parses_what_metrics_exports():
    """The report must read the exposition the core actually emits."""
    from core import metrics

    latency_report = _load_script("latency_report")

    metrics.reset()
    for value in (10.0, 20.0, 30.0, 40.0):
        metrics.observe("retrieval", value)

    parsed = latency_report.parse_metrics(metrics.prometheus_text())
    assert "retrieval" in parsed
    assert parsed["retrieval"]["count"] == 4
    assert parsed["retrieval"]["max_ms"] == 40.0
    assert parsed["retrieval"]["p50_ms"] > 0


def test_budgets_match_the_architecture_document():
    """Budget numbers in the report must be the ones the dossier states."""
    latency_report = _load_script("latency_report")

    assert latency_report.BUDGETS["asr"][0] == 2500.0
    assert latency_report.BUDGETS["retrieval"][0] == 500.0
    assert latency_report.BUDGETS["llm_first_token"][0] == 1500.0
    assert latency_report.BUDGETS["tts_first_byte"][0] == 1500.0
    assert latency_report.BUDGETS["turn_total"] [0] == 9000.0
    assert latency_report.BUDGETS["turn_total"][1] == 15000.0
    # TECH_STACK.md S8: "regression alert ... if ... exceeds budgets by >20%"
    assert latency_report.REGRESSION_MARGIN == 1.20


def test_regression_verdicts():
    latency_report = _load_script("latency_report")
    budget = (500.0, 500.0, "test")

    assert latency_report.verdict({"p50_ms": 100.0, "p95_ms": 400.0}, budget) == ("OK", False)
    assert latency_report.verdict({"p50_ms": 100.0, "p95_ms": 550.0}, budget) == ("OVER", False)
    assert latency_report.verdict({"p50_ms": 100.0, "p95_ms": 700.0}, budget) == ("ALERT", True)


def test_scoring_stage_is_actually_instrumented(db_session):
    """STEP 4 must report its own timing, not hide inside the retrieval span."""
    from core import metrics
    from core.domain.recommender import Intent, Profile, recommend

    metrics.reset()
    recommend(
        db_session,
        Profile(district_code="270481", gender="female", edu_level="8th_10th", lang="hi"),
        Intent(concept_text="सिलाई का काम सीखना है"),
    )
    assert metrics.summary().get("scoring", {}).get("count", 0) >= 1


# ---------------------------------------------------------------------------
# Error contract — what the kill-drill asserts against a live stack
# ---------------------------------------------------------------------------


def test_database_failure_is_a_speakable_message_not_a_stack_trace(client, monkeypatch):
    """DB down -> 503 + a sentence the beneficiary can hear, in their language.

    Regression guard: Starlette's ``exception_handler(500)`` does NOT fire for
    unhandled exceptions, so before Gate 10 this path returned a 500 with an
    empty body — the drill caught it and this test pins the fix.
    """
    from sqlalchemy.exc import OperationalError

    import core.db as core_db

    def dead(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    # get_db() calls SessionLocal(); killing it is exactly what a stopped
    # database container does to every request.
    monkeypatch.setattr(core_db, "SessionLocal", dead)

    response = client.post(
        "/sessions", json={"channel": "pwa", "lang": "hi"}, headers={"x-avsar-lang": "hi"}
    )

    assert response.status_code == 503
    body = response.json()["detail"]
    assert body["code"] == "db_unavailable"
    assert body["retryable"] is True
    assert body["human"].strip(), "the error must carry a speakable sentence"
    assert response.headers.get("retry-after")

    leaked = response.text.lower()
    for secret in ("traceback", "sqlalchemy", "psycopg", "operationalerror"):
        assert secret not in leaked, f"internal detail '{secret}' leaked to the client"


def test_database_error_speaks_the_session_language(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    import core.db as core_db

    def dead(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(core_db, "SessionLocal", dead)

    messages = {}
    for lang in ("hi", "te", "mr", "en"):
        response = client.post(
            "/sessions", json={"channel": "pwa", "lang": lang}, headers={"x-avsar-lang": lang}
        )
        assert response.status_code == 503
        messages[lang] = response.json()["detail"]["human"]

    assert len(set(messages.values())) == 4, f"languages share a message: {messages}"


def test_warm_start_is_configurable_and_on_by_default():
    """A cold first turn cost 11.3 s of model load; warm start removes it."""
    from core.config import settings

    assert settings.warm_start is True
