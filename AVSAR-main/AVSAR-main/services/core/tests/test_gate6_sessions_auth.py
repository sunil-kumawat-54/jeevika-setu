"""Gate 6 — Sessions API + Auth acceptance tests.

Verifies: session creation, consent gating, profile collection, recommendation,
confirmation, summary, **SSE event ordering**, 401, 403, RBAC, and that every
admin mutation writes an ``audit_log`` row.

The headline test — ``test_full_beneficiary_session_in_mock_mode`` — drives a
complete journey over httpx in mock mode, which is the Gate 6 requirement.
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from core.config import settings
from core.domain.fsm import (
    CLARIFY_THRESHOLD,
    EMPTY_ASR_LIMIT,
    PROFILE_STEPS,
    FsmState,
    Step,
    TurnInput,
    advance,
)
from core.models.tables import AuditLog, Consent
from core.models.tables import Session as SessionRow

LATUR = "270481"


@pytest.fixture()
def audio() -> str:
    from core.speech.mock import _wav_bytes

    return base64.b64encode(_wav_bytes(1.0)).decode("ascii")


def sse_events(response) -> list[tuple[str, dict]]:
    """Parse an SSE body into ordered (event, data) pairs."""
    events: list[tuple[str, dict]] = []
    name = None
    for line in response.text.splitlines():
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: ") and name:
            events.append((name, json.loads(line[6:])))
    return events


def _turn(client: TestClient, sid: str, **payload) -> list[tuple[str, dict]]:
    response = client.post(f"/sessions/{sid}/turn", json=payload)
    assert response.status_code == 200, response.text
    return sse_events(response)


def _last(events, name: str) -> dict:
    matches = [d for e, d in events if e == name]
    assert matches, f"no {name} event in {[e for e, _ in events]}"
    return matches[-1]


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==========================================================================
# FSM unit behaviour (PLAN.md §4.1)
# ==========================================================================


def test_consent_gates_every_profile_slot():
    """ARCHITECTURE §9: consent is bound before any profile slot is stored."""
    state = FsmState(step=Step.consent)
    transition = advance(state, TurnInput(choice="no"))
    assert transition.state.step == Step.declined
    assert not transition.state.consent_granted


def test_declining_consent_ends_politely():
    state = FsmState(step=Step.consent)
    transition = advance(state, TurnInput(text="नहीं"))
    assert transition.state.step == Step.declined
    assert transition.message_key == "consent_declined"


def test_ambiguous_consent_reasks_rather_than_assuming_yes():
    state = FsmState(step=Step.consent)
    transition = advance(state, TurnInput(text="माफ कीजिये क्या"))
    assert transition.state.step == Step.consent
    assert transition.error_code == "consent_required"
    assert not transition.state.consent_granted


def test_profile_step_without_consent_bounces_back():
    state = FsmState(step=Step.profile_district, consent_granted=False)
    transition = advance(state, TurnInput(choice=LATUR))
    assert transition.state.step == Step.consent
    assert "district_code" not in transition.state.slots


def test_five_profile_slots_in_order():
    """PLAN.md §4.1 fixes the order: district, age, gender, education, work."""
    state = FsmState(step=Step.consent)
    state = advance(state, TurnInput(choice="yes")).state
    seen = []
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        seen.append(state.step)
        state = advance(state, TurnInput(choice=value)).state
    assert seen == list(PROFILE_STEPS)
    assert state.step == Step.aspiration
    assert state.profile_complete


def test_clarify_fires_once_only():
    """PLAN.md §4.1: "If parse confidence < tau: clarify ONCE"."""
    state = FsmState(step=Step.aspiration, consent_granted=True)
    first = advance(state, TurnInput(text="सिलाई", confidence=CLARIFY_THRESHOLD - 0.2))
    assert first.state.step == Step.clarify
    assert first.state.clarified is True

    # A second low-confidence reading must NOT loop back into clarify.
    second = advance(first.state, TurnInput(text="सिलाई", confidence=CLARIFY_THRESHOLD - 0.2))
    assert second.state.step == Step.confirm_intent


def test_high_confidence_skips_clarify():
    state = FsmState(step=Step.aspiration, consent_granted=True)
    transition = advance(state, TurnInput(text="सिलाई का काम", confidence=0.95))
    assert transition.state.step == Step.confirm_intent
    assert transition.state.clarified is False


def test_two_empty_asr_switches_to_menu_mode():
    """PLAN.md §4.1: "Any ASR empty-result twice -> offer keypad/menu mode"."""
    state = FsmState(step=Step.aspiration, consent_granted=True)
    first = advance(state, TurnInput(text="", had_audio=True))
    assert first.state.menu_mode is False, "menu mode must not fire on the first miss"
    assert first.state.empty_asr_streak == 1

    second = advance(first.state, TurnInput(text="", had_audio=True))
    assert second.state.menu_mode is True
    assert second.state.degraded is True
    assert second.message_key == "menu_mode"


def test_a_successful_turn_resets_the_empty_streak():
    state = FsmState(step=Step.aspiration, consent_granted=True)
    state = advance(state, TurnInput(text="", had_audio=True)).state
    assert state.empty_asr_streak == 1
    state = advance(state, TurnInput(text="सिलाई", confidence=0.9, had_audio=True)).state
    assert state.empty_asr_streak == 0


def test_empty_limit_is_exactly_two():
    assert EMPTY_ASR_LIMIT == 2


def test_rejecting_the_parsed_intent_reopens_aspiration():
    state = FsmState(step=Step.confirm_intent, consent_granted=True, concept_text="सिलाई")
    transition = advance(state, TurnInput(choice="no"))
    assert transition.state.step == Step.aspiration
    assert transition.state.clarified is False


def test_state_round_trips_through_json():
    state = FsmState(step=Step.aspiration, slots={"district_code": LATUR}, clarified=True)
    restored = FsmState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restored.step == state.step
    assert restored.slots == state.slots
    assert restored.clarified is True


# ==========================================================================
# Auth
# ==========================================================================


def test_otp_lite_issues_and_verifies(client):
    response = client.post("/auth/request-otp", json={"phone": "9876543210"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sent"] is True
    assert body["otp_hint"] == settings.mock_otp, "demo mode must surface the fixed OTP"

    verified = client.post(
        "/auth/verify-otp", json={"phone": "9876543210", "otp": settings.mock_otp}
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["role"] == "beneficiary"
    assert verified.json()["access_token"]


def test_otp_rejects_a_wrong_code(client):
    client.post("/auth/request-otp", json={"phone": "9876500011"})
    response = client.post("/auth/verify-otp", json={"phone": "9876500011", "otp": "000000"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_otp"


def test_otp_body_is_speakable(client):
    client.post("/auth/request-otp", json={"phone": "9876500012"})
    response = client.post(
        "/auth/verify-otp",
        json={"phone": "9876500012", "otp": "999999"},
        headers={"x-avsar-lang": "mr"},
    )
    detail = response.json()["detail"]
    assert detail["lang"] == "mr"
    assert detail["human"], "error must carry a speakable sentence"
    assert "human_mr" in detail


def test_beneficiary_row_has_no_name_column(client, db_session):
    """RULE 6, enforced at the API boundary too."""
    client.post("/auth/request-otp", json={"phone": "9876500013"})
    columns = db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
    ).scalars().all()
    assert not [c for c in columns if "name" in c.lower()]


def test_officer_login_with_argon2id(client):
    token = _login(client, settings.demo_officer_email, settings.demo_officer_password)
    assert token
    me = client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["role"] == "officer"


def test_password_hash_is_argon2id(db_session):
    from core.models.tables import User

    user = db_session.execute(
        select(User).where(User.email == settings.demo_officer_email)
    ).scalar_one()
    assert user.password_hash.startswith("$argon2id$"), user.password_hash[:20]


def test_login_with_a_bad_password_is_401(client):
    response = client.post(
        "/auth/login", json={"email": settings.demo_officer_email, "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_does_not_reveal_whether_an_account_exists(client):
    missing = client.post("/auth/login", json={"email": "nobody@demo", "password": "x"})
    wrong = client.post(
        "/auth/login", json={"email": settings.demo_officer_email, "password": "x"}
    )
    assert missing.status_code == wrong.status_code == 401
    assert missing.json()["detail"]["code"] == wrong.json()["detail"]["code"]


def test_refresh_token_mints_a_new_access_token(client):
    response = client.post(
        "/auth/login",
        json={"email": settings.demo_officer_email, "password": settings.demo_officer_password},
    )
    refreshed = client.post("/auth/refresh", json={"refresh_token": response.json()["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


def test_access_token_is_not_accepted_as_a_refresh_token(client):
    token = _login(client, settings.demo_officer_email, settings.demo_officer_password)
    response = client.post("/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


def test_jwt_lifetimes_match_architecture():
    """ARCHITECTURE §9: "JWT access 30 min + refresh 12 h"."""
    assert settings.jwt_access_min == 30
    assert settings.jwt_refresh_h == 12


# ==========================================================================
# RBAC — 401 and 403
# ==========================================================================


def test_admin_endpoint_without_a_token_is_401(client):
    response = client.get("/admin/crosswalk")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_admin_endpoint_with_a_garbage_token_is_401(client):
    response = client.get("/admin/crosswalk", headers=_auth("not-a-jwt"))
    assert response.status_code == 401


def test_viewer_cannot_read_the_crosswalk_console(client):
    """viewer < officer on the ladder."""
    token = _login(client, settings.demo_viewer_email, settings.demo_viewer_password)
    response = client.get("/admin/crosswalk", headers=_auth(token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"


def test_officer_can_read_but_not_write_the_crosswalk(client, db_session):
    token = _login(client, settings.demo_officer_email, settings.demo_officer_password)
    listing = client.get("/admin/crosswalk", headers=_auth(token))
    assert listing.status_code == 200
    assert listing.json()["can_edit"] is False

    entry_id = listing.json()["items"][0]["id"]
    write = client.put(
        f"/admin/crosswalk/{entry_id}", json={"status": "reviewed"}, headers=_auth(token)
    )
    assert write.status_code == 403, "an officer must not be able to edit the crosswalk"


def test_admin_can_write_the_crosswalk(client):
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    listing = client.get("/admin/crosswalk", headers=_auth(token))
    assert listing.json()["can_edit"] is True
    entry_id = listing.json()["items"][0]["id"]
    response = client.put(
        f"/admin/crosswalk/{entry_id}", json={"status": "reviewed"}, headers=_auth(token)
    )
    assert response.status_code == 200, response.text
    assert response.json()["updated"] is True


def test_beneficiary_token_cannot_reach_admin(client):
    client.post("/auth/request-otp", json={"phone": "9876500014"})
    token = client.post(
        "/auth/verify-otp", json={"phone": "9876500014", "otp": settings.mock_otp}
    ).json()["access_token"]
    response = client.get("/admin/crosswalk", headers=_auth(token))
    assert response.status_code == 403


# ==========================================================================
# Audit log — every admin mutation
# ==========================================================================


def test_admin_mutation_writes_an_audit_row(client, db_session):
    """ARCHITECTURE §9: "all admin mutations are audited"."""
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    listing = client.get("/admin/crosswalk", headers=_auth(token)).json()
    entry_id = listing["items"][0]["id"]

    before = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.entity == "crosswalk")
    ).scalar_one()

    response = client.put(
        f"/admin/crosswalk/{entry_id}", json={"status": "reviewed"}, headers=_auth(token)
    )
    assert response.status_code == 200

    db_session.rollback()  # see the committed row
    after = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.entity == "crosswalk")
    ).scalar_one()
    assert after == before + 1, "no audit_log row was written for an admin mutation"


def test_audit_row_captures_before_and_after(client, db_session):
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    listing = client.get("/admin/crosswalk", headers=_auth(token)).json()
    entry = listing["items"][0]

    client.put(
        f"/admin/crosswalk/{entry['id']}",
        json={"concept": entry["concept"], "status": "reviewed"},
        headers=_auth(token),
    )
    db_session.rollback()
    row = db_session.execute(
        select(AuditLog)
        .where(AuditLog.entity == "crosswalk", AuditLog.entity_id == str(entry["id"]))
        .order_by(AuditLog.ts.desc())
        .limit(1)
    ).scalar_one()
    assert row.before and row.after
    assert row.after["version"] > row.before["version"], "version was not bumped"
    assert row.actor is not None


def test_reembed_is_audited(client, db_session):
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    before = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "crosswalk.reembed")
    ).scalar_one()
    response = client.post("/admin/reembed", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["job_id"]
    db_session.rollback()
    after = db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "crosswalk.reembed")
    ).scalar_one()
    assert after == before + 1


def test_admin_cannot_bind_a_phrase_to_a_nonexistent_qp(client):
    """A reviewer must not be able to inject an invented course."""
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    listing = client.get("/admin/crosswalk", headers=_auth(token)).json()
    entry_id = listing["items"][0]["id"]
    response = client.put(
        f"/admin/crosswalk/{entry_id}",
        json={"qp_codes": ["ZZZ/Q9999"]},
        headers=_auth(token),
    )
    assert response.status_code == 400
    assert "unknown QP codes" in response.json()["detail"]["detail"]


def test_live_check_is_disabled_by_default(client):
    """RULE 3: the only runtime path to a portal is off unless explicitly enabled."""
    token = _login(client, settings.demo_admin_email, settings.demo_admin_password)
    response = client.get("/admin/live-check", headers=_auth(token))
    assert response.status_code == 403
    assert "ALLOW_LIVE_CHECK" in response.json()["detail"]["detail"]


# ==========================================================================
# Sessions API — the full journey
# ==========================================================================


def test_create_session_returns_state(client):
    response = client.post("/sessions", json={"channel": "pwa", "lang": "hi"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["session_id"]
    assert body["state"]["step"] == "consent"
    assert body["state"]["consent"]["line"], "the consent notice must be returned as data"


def test_create_session_is_anonymous(client, db_session):
    """RULE 6 — no login required to be helped."""
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    row = db_session.execute(
        select(SessionRow).where(SessionRow.id == __import__("uuid").UUID(sid))
    ).scalar_one()
    assert row.user_id is None


def test_unknown_session_is_404_and_speakable(client):
    response = client.post(
        "/sessions/00000000-0000-0000-0000-000000000000/turn", json={"text": "hi"}
    )
    events = sse_events(response)
    error = _last(events, "error")
    assert error["code"] == "session_not_found"
    assert error["human"]


def test_full_beneficiary_session_in_mock_mode(client, audio, db_session):
    """The Gate 6 headline: a complete journey over HTTP, mock mode, no keys."""
    created = client.post("/sessions", json={"channel": "pwa", "lang": "hi"})
    sid = created.json()["session_id"]

    # 1. consent
    events = _turn(client, sid, choice="yes")
    assert _last(events, "state")["consent_granted"] is True

    # 2-6. five profile slots
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        events = _turn(client, sid, choice=value)
    assert _last(events, "state")["step"] == "aspiration"

    # 7. aspiration spoken through the mock ASR
    events = _turn(client, sid, audio_b64=audio)
    transcript = _last(events, "transcript")
    assert transcript["text"], "mock ASR returned nothing"
    assert transcript["provider"] == "mock"
    assert _last(events, "state")["step"] == "confirm_intent"

    # 8. confirm -> recommendation
    events = _turn(client, sid, choice="yes")
    recs = _last(events, "recs")
    assert recs["items"], "no recommendation produced"
    assert recs["grounded"] is True
    assert len(recs["items"]) <= 3
    top = recs["items"][0]
    assert top["qp_code"]
    assert top["assistance"]["cap_inr"] == 50_000

    tts = [d for e, d in events if e == "tts"]
    assert tts, "nothing was spoken"
    assert all(chunk["chunk_b64"] for chunk in tts)

    # 9. replay
    replay = _turn(client, sid, choice="replay")
    assert _last(replay, "recs")["replay"] is True

    # 10. confirm the recommendation
    confirmed = client.post(f"/sessions/{sid}/confirm-rec", json={"course_id": top["course_id"]})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["summary_lang"] == "hi"
    assert top["name"] in confirmed.json()["summary_text"]

    # 11. summary
    summary = client.get(f"/sessions/{sid}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["confirmed_course_id"] == top["course_id"]
    assert body["consent_granted"] is True
    assert body["profile"]["district_code"] == LATUR
    assert body["profile"]["gender"] == "female"

    # 12. consent playback (the DPDP trail)
    playback = client.get(f"/sessions/{sid}/consent")
    assert playback.json()["granted"] is True
    assert playback.json()["records"][0]["playback_ref"]


def test_sse_event_order_matches_the_contract(client, audio):
    """ARCHITECTURE §5 enumerates: transcript | state | recs | tts | error."""
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        _turn(client, sid, choice=value)
    _turn(client, sid, audio_b64=audio)
    events = _turn(client, sid, choice="yes")

    names = [e for e, _ in events]
    assert names[0] == "transcript", names
    assert names[1] == "state", names
    assert "recs" in names
    assert names.index("recs") < names.index("tts"), names
    assert names.index("state") < names.index("recs"), names


def test_turn_emits_transcript_before_state(client, audio):
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    events = _turn(client, sid, choice="yes")
    names = [e for e, _ in events]
    assert names.index("transcript") < names.index("state")


def test_profile_slots_reach_the_database(client, db_session):
    import uuid as _uuid

    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "30_45", "male", "5th_8th", "farm_labour"]:
        _turn(client, sid, choice=value)

    db_session.rollback()
    row = db_session.execute(
        select(SessionRow).where(SessionRow.id == _uuid.UUID(sid))
    ).scalar_one()
    assert row.district_code == LATUR
    assert row.age_band == "30_45"
    assert row.gender == "male"
    assert row.edu_level == "5th_8th"
    assert row.current_work == "farm_labour"
    assert row.consent_id is not None


def test_no_slot_is_written_without_a_consent_row(client, db_session):
    """The invariant RULE 6 exists to protect, checked against the database."""
    import uuid as _uuid

    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    # Skip consent entirely and try to answer the district question.
    _turn(client, sid, choice=LATUR)
    db_session.rollback()
    row = db_session.execute(
        select(SessionRow).where(SessionRow.id == _uuid.UUID(sid))
    ).scalar_one()
    assert row.consent_id is None
    assert row.district_code is None, "a profile slot was stored without consent"


def test_consent_row_is_created_once(client, db_session):
    import uuid as _uuid

    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    db_session.rollback()
    count = db_session.execute(
        select(func.count())
        .select_from(Consent)
        .where(Consent.session_id == _uuid.UUID(sid))
    ).scalar_one()
    assert count == 1


def test_declining_consent_stores_nothing(client, db_session):
    import uuid as _uuid

    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    events = _turn(client, sid, choice="no")
    assert _last(events, "state")["step"] == "declined"
    db_session.rollback()
    row = db_session.execute(
        select(SessionRow).where(SessionRow.id == _uuid.UUID(sid))
    ).scalar_one()
    assert row.consent_id is None
    assert row.district_code is None


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_journey_works_in_every_language(client, audio, lang):
    sid = client.post("/sessions", json={"lang": lang}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        _turn(client, sid, choice=value)
    _turn(client, sid, audio_b64=audio)
    events = _turn(client, sid, choice="yes")
    recs = _last(events, "recs")
    assert recs["items"], f"{lang}: no recommendation"
    summary = client.get(f"/sessions/{sid}/summary").json()
    assert summary["lang"] == lang
    assert summary["summary_text"]


def test_two_empty_turns_offer_menu_mode_over_http(client, audio):
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        _turn(client, sid, choice=value)

    _turn(client, sid, audio_b64=audio, variant="empty")
    events = _turn(client, sid, audio_b64=audio, variant="empty")
    state = _last(events, "state")
    assert state["menu_mode"] is True
    assert state["degraded"] is True


def test_declared_gap_refuses_over_http(client, audio):
    """A poultry aspiration must produce a refusal, not another trade."""
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female", "5th_8th", "unemployed"]:
        _turn(client, sid, choice=value)
    _turn(client, sid, audio_b64=audio, variant="gap")
    events = _turn(client, sid, choice="yes")

    assert not [d for e, d in events if e == "recs"], "a gap concept must not return courses"
    error = _last(events, "error")
    assert error["refusal"] == "declared_gap"
    summary = client.get(f"/sessions/{sid}/summary").json()
    assert summary["officer_callback"] is True


def test_confirm_rec_rejects_a_course_not_recommended(client, audio):
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        _turn(client, sid, choice=value)
    _turn(client, sid, audio_b64=audio)
    _turn(client, sid, choice="yes")

    response = client.post(f"/sessions/{sid}/confirm-rec", json={"course_id": 999_999})
    assert response.status_code == 400
    assert response.json()["detail"]["human"]


def test_oversized_audio_is_rejected(client):
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    response = client.post(
        f"/sessions/{sid}/turn", json={"audio_b64": "A" * 1_300_000}
    )
    assert response.status_code == 413


def test_progress_indicator_advances(client):
    """RULE 7 — "clear progress indicators"."""
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    seen = []
    for value in [LATUR, "18_30", "female", "8th_10th", "unemployed"]:
        events = _turn(client, sid, choice=value)
        seen.append(_last(events, "state")["progress"]["current"])
    assert seen == sorted(seen), f"progress went backwards: {seen}"
    assert seen[-1] > seen[0]


def test_options_never_exceed_four_per_screen(client):
    """RULE 7 — max 4 visible options; longer lists must declare pagination."""
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    _turn(client, sid, choice="yes")
    for value in [LATUR, "18_30", "female"]:
        events = _turn(client, sid, choice=value)
        state = _last(events, "state")
        if state["options"]:
            assert state["options_per_screen"] == 4
            if len(state["options"]) > 4:
                assert state["paginate_options"] is True


def test_every_state_payload_carries_a_prompt(client):
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    events = _turn(client, sid, choice="yes")
    assert _last(events, "state")["prompt"], "a step with no spoken prompt is unusable"


def test_rate_limit_returns_a_speakable_429(client):
    from core.api import ratelimit

    ratelimit.reset()
    sid = client.post("/sessions", json={"lang": "hi"}).json()["session_id"]
    hit_limit = False
    for _ in range(settings.rate_limit_turn_per_min + 5):
        response = client.post(f"/sessions/{sid}/turn", json={"text": "x"})
        if response.status_code == 429:
            hit_limit = True
            assert response.json()["detail"]["code"] == "rate_limited"
            assert response.json()["detail"]["retryable"] is True
            break
    ratelimit.reset()
    assert hit_limit, "turn endpoint was never rate limited"
