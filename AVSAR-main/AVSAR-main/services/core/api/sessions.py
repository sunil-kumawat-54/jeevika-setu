"""Sessions API — ARCHITECTURE.md section 5.

    POST /sessions {channel, lang}                     -> {session_id, state}
    POST /sessions/{id}/turn {text?|audio_b64?, dtmf?} -> SSE stream:
         transcript{...} | state{step,slots} | recs[{qp_code,...}] |
         tts{url|chunk_b64} | error{code}
    POST /sessions/{id}/confirm-rec {course_id}        -> {summary_text, summary_lang}
    GET  /sessions/{id}/summary                        -> printable/text summary

The turn endpoint is the heart of the product, and the order of the SSE events
is part of the contract: a client must be able to paint the caption before the
state moves, and start audio before the recommendation card finishes rendering.

Consent is a hard gate. ARCHITECTURE section 9: *"Consent record bound to
session before any profile slot is stored."* The FSM refuses to leave the
consent step, and this router refuses to write a slot column until a `consents`
row exists — belt and braces, because RULE 6 is the one rule a demo must never
be caught bending.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from core.api.ratelimit import rate_limit
from core.api.security import Principal, optional_principal
from core.config import settings
from core.db import SessionLocal, get_db
from core.domain import prompts
from core.domain.fsm import (
    MAX_OPTIONS,
    SLOT_FOR_STEP,
    Action,
    FsmState,
    Step,
    TurnInput,
    advance,
    is_terminal,
)
from core.domain.recommender import Intent, Profile, persist_recommendations, recommend
from core.errors import AvsarError, error_payload
from core.llm import templates
from core.metrics import incr, timed
from core.models.tables import (
    Channel,
    Consent,
    ConsentMode,
    District,
    Recommendation,
    Transcript,
)
from core.models.tables import (
    Session as SessionRow,
)

log = logging.getLogger("avsar.sessions")
router = APIRouter(prefix="/sessions", tags=["sessions"])

#: TECH_STACK §4: "16 kHz mono WAV, <=15 s per turn". 15 s of 16-bit mono PCM is
#: ~480 KB, ~640 KB base64; allow headroom but refuse anything absurd.
MAX_AUDIO_B64_BYTES = 1_200_000


class CreateSession(BaseModel):
    channel: str = "pwa"
    lang: str = "hi"
    phone: str | None = None


class TurnRequest(BaseModel):
    text: str | None = None
    audio_b64: str | None = None
    dtmf: str | None = None
    choice: str | None = None
    #: Forces a mock fixture variant (``empty`` / ``low_confidence`` / ``unknown``
    #: / ``gap``) so the kill-drill and tests can reproduce a failure mode
    #: without patching code. Ignored by real providers.
    variant: str | None = None


class ConfirmRec(BaseModel):
    course_id: int = Field(gt=0)


def _lang_of(request: Request, fallback: str = "hi") -> str:
    lang = request.headers.get("x-avsar-lang") or request.query_params.get("lang") or fallback
    return lang if lang in ("hi", "mr", "te", "en") else fallback


def _get_session(db: OrmSession, session_id: str, lang: str = "hi") -> SessionRow:
    try:
        uid = uuid.UUID(str(session_id))
    except (ValueError, AttributeError):
        raise AvsarError(404, "session_not_found", lang)
    row = db.execute(select(SessionRow).where(SessionRow.id == uid)).scalar_one_or_none()
    if row is None:
        raise AvsarError(404, "session_not_found", lang)
    return row


def _district_name(db: OrmSession, code: str | None, lang: str) -> str | None:
    if not code:
        return None
    district = db.execute(select(District).where(District.code == code)).scalar_one_or_none()
    return district.display_name(lang) if district else None


def _options_for_step(lang: str, step: Step) -> list[dict]:
    """<=4 visible options per screen (RULE 7).

    Education and current-work have six values, so they paginate behind a
    "more" affordance rather than being truncated — a hidden option is a lost
    beneficiary.
    """
    slot = SLOT_FOR_STEP.get(step)
    if not slot:
        return []
    key = prompts.SLOT_OPTIONS.get(slot)
    if not key:
        return []
    return prompts.options(lang, key)


def _state_payload(db: OrmSession, session: SessionRow, state: FsmState) -> dict:
    lang = session.lang
    current, total = state.progress
    step_text = prompts.step_prompt(lang, state.step.value)
    options = _options_for_step(lang, state.step)
    payload = {
        "session_id": str(session.id),
        "step": state.step.value,
        "slots": dict(state.slots),
        "prompt": step_text.get("prompt", ""),
        "help": step_text.get("help", ""),
        "options": options,
        "options_per_screen": MAX_OPTIONS,
        "paginate_options": len(options) > MAX_OPTIONS,
        "progress": {"current": current, "total": total},
        "menu_mode": state.menu_mode,
        "consent_granted": state.consent_granted,
        "degraded": state.degraded or session.degraded,
        "lang": lang,
        "turn_no": state.turn_no,
        "terminal": is_terminal(state),
        "officer_callback": state.officer_callback,
    }
    if state.step == Step.consent:
        payload["consent"] = prompts.consent(lang)
    if state.step == Step.aspiration:
        payload["suggestions"] = prompts.suggestions(lang)
    if state.step == Step.recommendation:
        payload["menu"] = prompts.menu(lang)
    return payload


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# --------------------------------------------------------------------------
# Create
# --------------------------------------------------------------------------


@router.post("")
@router.post("/")
def create_session(
    payload: CreateSession,
    request: Request,
    db: OrmSession = Depends(get_db),
    principal: Principal | None = Depends(optional_principal),
) -> dict:
    """Start a conversation. Anonymous is fine — RULE 6 wants minimal PII."""
    lang = payload.lang if payload.lang in ("hi", "mr", "te", "en") else "hi"
    try:
        channel = Channel(payload.channel)
    except ValueError:
        channel = Channel.pwa

    state = FsmState(step=Step.consent, slots={"lang": lang})
    session = SessionRow(
        user_id=principal.user_id if principal else None,
        channel=channel,
        lang=lang,
        state=state.to_dict(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    incr("sessions_created_total", channel=channel.value)
    log.info("session created", extra={"session_id": str(session.id), "event": "session_created"})
    return {"session_id": str(session.id), "state": _state_payload(db, session, state)}


# --------------------------------------------------------------------------
# Turn — the SSE stream
# --------------------------------------------------------------------------


@router.post("/{session_id}/turn")
async def turn(
    session_id: str,
    payload: TurnRequest,
    request: Request,
    _: None = Depends(rate_limit("turn", settings.rate_limit_turn_per_min)),
) -> StreamingResponse:
    """Advance the conversation by one turn, streaming SSE events.

    Event order is contractual:
    ``transcript`` -> ``state`` -> [``recs``] -> ``tts`` (one per sentence),
    with ``error`` emitted in place of whatever failed.
    """
    if payload.audio_b64 and len(payload.audio_b64) > MAX_AUDIO_B64_BYTES:
        raise AvsarError(
            413, "bad_request", _lang_of(request), "audio exceeds the 15-second turn limit"
        )

    async def stream():
        db = SessionLocal()
        started = time.monotonic()
        try:
            lang_hint = _lang_of(request)
            try:
                session = _get_session(db, session_id, lang_hint)
            except AvsarError as exc:
                yield _sse("error", exc.detail)
                return

            lang = session.lang
            state = FsmState.from_dict(session.state)

            # ---- 1. ASR (or a typed/tapped input) -----------------------
            transcript_text = payload.text
            confidence = 1.0
            asr_provider = None
            had_audio = bool(payload.audio_b64)

            if payload.audio_b64:
                from core.speech.router import get_router

                step_key = state.step.value + (f":{payload.variant}" if payload.variant else "")
                with timed("asr", str(session.id)):
                    asr = get_router().transcribe(
                        payload.audio_b64, lang, step=step_key, session_id=str(session.id)
                    )
                transcript_text = asr.text
                confidence = asr.confidence
                asr_provider = asr.provider
                if asr.degraded:
                    state.degraded = True
                yield _sse(
                    "transcript",
                    {
                        "text": asr.text,
                        "confidence": round(asr.confidence, 3),
                        "provider": asr.provider,
                        "is_final": asr.is_final,
                        "empty": asr.is_empty,
                        "latency_ms": round(asr.latency_ms, 1),
                    },
                )
            elif payload.text or payload.choice or payload.dtmf:
                yield _sse(
                    "transcript",
                    {
                        "text": payload.text or payload.choice or payload.dtmf,
                        "confidence": 1.0,
                        "provider": "typed",
                        "is_final": True,
                        "empty": False,
                        "latency_ms": 0.0,
                    },
                )

            turn_input = TurnInput(
                text=transcript_text,
                choice=payload.choice,
                dtmf=payload.dtmf,
                confidence=confidence,
                had_audio=had_audio,
            )

            # ---- 2. FSM --------------------------------------------------
            previous_step = state.step
            transition = advance(state, turn_input)
            state = transition.state

            db.add(
                Transcript(
                    session_id=session.id,
                    turn_no=state.turn_no,
                    asr_provider=asr_provider or "typed",
                    raw_text=transcript_text,
                    confidence=confidence,
                    parsed_slots={
                        "step": previous_step.value,
                        "slot": transition.slot,
                        "value": transition.value,
                    },
                    latency_ms=int((time.monotonic() - started) * 1000),
                )
            )

            # ---- 3. Consent gate ----------------------------------------
            if transition.has(Action.record_consent):
                consent_row = Consent(
                    session_id=session.id,
                    mode=ConsentMode.tapped if payload.choice else ConsentMode.spoken,
                    granted=True,
                    playback_ref=prompts.consent(lang).get("playback_ref"),
                )
                db.add(consent_row)
                db.flush()
                session.consent_id = consent_row.id
                incr("consents_granted_total")

            if transition.has(Action.persist_slot) and transition.slot:
                # Belt and braces: never write a profile column without consent.
                if session.consent_id is None:
                    yield _sse("error", error_payload("consent_required", lang))
                    state.step = Step.consent
                else:
                    _apply_slot(session, transition.slot, transition.value)

            speak_text: str | None = None
            # Buffered so the SSE order stays exactly as ARCHITECTURE §5
            # enumerates it: transcript -> state -> recs -> tts -> error.
            pending_recs: dict | None = None
            pending_error: dict | None = None

            # ---- 4. Recommendation --------------------------------------
            if transition.has(Action.build_recommendation):
                with timed("retrieval", str(session.id)):
                    result = recommend(
                        db,
                        Profile(
                            district_code=session.district_code,
                            age_band=session.age_band,
                            gender=session.gender,
                            edu_level=session.edu_level,
                            current_work=session.current_work,
                            annual_income_inr=session.annual_income_inr,
                            lang=lang,
                        ),
                        Intent(
                            concept_text=state.concept_text or "",
                            concept=state.concept,
                            gia_domain=state.gia_domain,
                        ),
                    )
                state.concept = result.concept
                state.gia_domain = result.gia_domain

                if result.is_refusal:
                    # No invented course, ever. Offer the officer instead.
                    state.officer_callback = True
                    session.officer_callback = True
                    speak_text = templates.verbalize_refusal(lang, result.refusal)
                    pending_error = {
                        **error_payload("out_of_scope", lang),
                        "refusal": result.refusal,
                        "concept": result.concept,
                        "notes": result.notes,
                    }
                    incr("recommendation_refusals_total", reason=result.refusal or "unknown")
                else:
                    persist_recommendations(db, session.id, result)
                    district_name = _district_name(db, session.district_code, lang)
                    from core.llm.verbalizer import verbalize

                    with timed("llm_first_token", str(session.id)):
                        spoken = verbalize(
                            result.items, lang, district_name=district_name, db=db
                        )
                    speak_text = spoken.text
                    if spoken.degraded:
                        state.degraded = True
                    _mark_grounded(db, session.id, spoken.grounded)
                    pending_recs = {
                        "items": result.items,
                        "stretch": result.stretch,
                        "ceiling": result.ceiling,
                        "concept": result.concept,
                        "gia_domain": result.gia_domain,
                        "grounded": spoken.grounded,
                        "verbalizer": spoken.mode,
                        "notes": result.notes,
                    }
                    incr("recommendations_built_total")

            if transition.has(Action.replay) or transition.has(Action.speak_alternatives):
                stored = _stored_items(db, session.id, lang)
                district_name = _district_name(db, session.district_code, lang)
                speak_text = templates.verbalize_recommendation(
                    stored,
                    lang,
                    include_alternatives=transition.has(Action.speak_alternatives),
                    district_name=district_name,
                )
                if stored:
                    pending_recs = {"items": stored, "replay": True}

            if transition.has(Action.render_summary):
                stored = _stored_items(db, session.id, lang)
                district_name = _district_name(db, session.district_code, lang)
                speak_text = templates.summary_text(stored, lang, district_name=district_name)

            if transition.has(Action.end_session):
                import datetime as dt

                session.ended_at = dt.datetime.now(dt.UTC)
                if state.step == Step.declined:
                    speak_text = prompts.consent(lang).get("declined_ack", "")

            if transition.has(Action.offer_menu_mode):
                speak_text = prompts.step_prompt(lang, Step.menu_mode.value).get("prompt", "")

            # ---- 5. Persist state ---------------------------------------
            session.state = state.to_dict()
            session.degraded = session.degraded or state.degraded
            db.commit()
            db.refresh(session)

            # ---- 6. state event ------------------------------------------
            yield _sse("state", _state_payload(db, session, state))

            if pending_recs is not None:
                yield _sse("recs", pending_recs)
            if pending_error is not None:
                yield _sse("error", pending_error)
            if transition.error_code:
                yield _sse("error", error_payload(transition.error_code, lang))

            # ---- 7. TTS, one event per sentence --------------------------
            if speak_text is None and transition.has(Action.ask):
                speak_text = prompts.step_prompt(lang, transition.message_key or state.step.value).get(
                    "prompt", ""
                )
            if speak_text is None and transition.has(Action.clarify):
                speak_text = prompts.step_prompt(lang, Step.clarify.value).get("prompt", "")

            if speak_text:
                from core.speech.router import get_router

                chunks = get_router().synthesize(
                    speak_text, lang, step=state.step.value, session_id=str(session.id)
                )
                for chunk in chunks:
                    yield _sse(
                        "tts",
                        {
                            "index": chunk.index,
                            "text": chunk.text,
                            "chunk_b64": chunk.audio_b64,
                            "mime": chunk.mime,
                            "provider": chunk.provider,
                            "degraded": chunk.degraded,
                        },
                    )
                    # Yield to the loop so the client can start playing chunk 0
                    # while later chunks are still being produced.
                    await asyncio.sleep(0)
                if not chunks:
                    yield _sse("error", error_payload("provider_unavailable", lang))

            incr("session_turns_total")
        except Exception as exc:  # never leave the client hanging
            log.exception("turn failed", extra={"session_id": session_id})
            yield _sse("error", error_payload("network_error", "hi", str(exc)))
        finally:
            from core.metrics import observe

            observe("turn_total", (time.monotonic() - started) * 1000.0, session_id)
            db.close()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # nginx must not buffer an SSE stream
            "Connection": "keep-alive",
        },
    )


def _apply_slot(session: SessionRow, slot: str, value: Any) -> None:
    if slot == "district_code":
        session.district_code = value
    elif slot == "age_band":
        session.age_band = value
    elif slot == "gender":
        session.gender = value
    elif slot == "edu_level":
        session.edu_level = value
    elif slot == "current_work":
        session.current_work = value


def _mark_grounded(db: OrmSession, session_id, grounded: bool) -> None:
    for row in db.execute(
        select(Recommendation).where(Recommendation.session_id == session_id)
    ).scalars():
        row.grounded = grounded


def _stored_items(db: OrmSession, session_id, lang: str) -> list[dict]:
    """Rebuild the recommendation payload from the database.

    Replay must read what was actually stored, not re-run the engine — otherwise
    "फिर सुनें" could speak something different from what the beneficiary was
    told the first time.
    """
    from core.domain.recommender import spoken_level
    from core.domain.scheme_constants import LOAN_ASSISTANCE_PHRASE, compute_assistance
    from core.models.tables import Course

    rows = db.execute(
        select(Recommendation, Course)
        .join(Course, Course.id == Recommendation.course_id)
        .where(Recommendation.session_id == session_id)
        .order_by(Recommendation.rank)
    ).all()
    assistance = compute_assistance(0)
    items = []
    for rec, course in rows:
        items.append(
            {
                "rank": rec.rank,
                "course_id": course.id,
                "qp_code": course.qp_code,
                "name": course.sub_course,
                "nsqf_level": float(course.nsqf_level) if course.nsqf_level is not None else None,
                "nsqf_level_spoken": spoken_level(course.nsqf_level),
                "hours": course.hours_min,
                "sector": course.sector,
                "score": rec.score,
                "factors": rec.factors,
                "seats_in_district": (rec.factors or {}).get("seats", 0),
                "synthetic": bool(course.synthetic),
                "grounded": rec.grounded,
                "confirmed": rec.confirmed,
                "assistance": {
                    "loan_support": LOAN_ASSISTANCE_PHRASE.get(lang, assistance.phrase_en),
                    "loan_support_en": assistance.phrase_en,
                    "cap_inr": assistance.cap_inr,
                    "pct_of_project_cost": assistance.pct_of_project_cost,
                },
                "next_step": prompts.recommendation_phrases(lang).get("next_step", ""),
            }
        )
    return items


# --------------------------------------------------------------------------
# Confirm + summary
# --------------------------------------------------------------------------


@router.post("/{session_id}/confirm-rec")
def confirm_rec(
    session_id: str,
    payload: ConfirmRec,
    request: Request,
    db: OrmSession = Depends(get_db),
) -> dict:
    """ARCHITECTURE §5: ``-> {summary_text, summary_lang}``."""
    lang_hint = _lang_of(request)
    session = _get_session(db, session_id, lang_hint)
    lang = session.lang

    rows = db.execute(
        select(Recommendation).where(Recommendation.session_id == session.id)
    ).scalars().all()
    if not rows:
        raise AvsarError(404, "session_not_found", lang, "no recommendations on this session")

    chosen = next((r for r in rows if r.course_id == payload.course_id), None)
    if chosen is None:
        raise AvsarError(400, "bad_request", lang, "course_id is not one of the recommendations")

    for row in rows:
        row.confirmed = row.course_id == payload.course_id

    state = FsmState.from_dict(session.state)
    state.step = Step.summary
    session.state = state.to_dict()
    db.commit()

    items = _stored_items(db, session.id, lang)
    district_name = _district_name(db, session.district_code, lang)
    text = templates.summary_text(
        items, lang, district_name=district_name, confirmed_course_id=payload.course_id
    )
    incr("recommendations_confirmed_total")
    return {
        "summary_text": text,
        "summary_lang": lang,
        "course_id": payload.course_id,
        "session_id": str(session.id),
    }


@router.get("/{session_id}/summary")
def summary(
    session_id: str,
    request: Request,
    db: OrmSession = Depends(get_db),
) -> dict:
    """Printable/text summary (ARCHITECTURE §5)."""
    lang_hint = _lang_of(request)
    session = _get_session(db, session_id, lang_hint)
    lang = session.lang
    items = _stored_items(db, session.id, lang)
    district_name = _district_name(db, session.district_code, lang)
    confirmed = next((i["course_id"] for i in items if i.get("confirmed")), None)
    state = FsmState.from_dict(session.state)

    return {
        "session_id": str(session.id),
        "lang": lang,
        "summary_text": templates.summary_text(
            items, lang, district_name=district_name, confirmed_course_id=confirmed
        ),
        "labels": prompts.summary_labels(lang),
        "recommendations": items,
        "confirmed_course_id": confirmed,
        "district": district_name,
        "profile": {
            "district_code": session.district_code,
            "age_band": session.age_band,
            "gender": session.gender,
            "edu_level": session.edu_level,
            "current_work": session.current_work,
        },
        "consent_granted": session.consent_id is not None,
        "degraded": session.degraded,
        "synthetic": session.synthetic,
        "officer_callback": session.officer_callback,
        "step": state.step.value,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


@router.get("/{session_id}/consent")
def consent_playback(
    session_id: str, request: Request, db: OrmSession = Depends(get_db)
) -> dict:
    """Consent playback endpoint (ARCHITECTURE §9) — the DPDP audit trail.

    research.md §8.1: notice must accompany the consent request and, per DPDP
    s.5(3), be available in English **and** Eighth Schedule languages. The
    recorded line is returned verbatim so it can be replayed for verification.
    """
    lang_hint = _lang_of(request)
    session = _get_session(db, session_id, lang_hint)
    rows = db.execute(
        select(Consent).where(Consent.session_id == session.id).order_by(Consent.ts)
    ).scalars().all()
    return {
        "session_id": str(session.id),
        "lang": session.lang,
        "granted": any(c.granted for c in rows),
        "records": [
            {
                "mode": c.mode.value,
                "granted": c.granted,
                "ts": c.ts.isoformat() if c.ts else None,
                "playback_ref": c.playback_ref,
            }
            for c in rows
        ],
        "notice": prompts.consent(session.lang),
    }
