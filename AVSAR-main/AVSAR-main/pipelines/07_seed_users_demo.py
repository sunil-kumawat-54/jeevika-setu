"""Pipeline 07 — demo accounts and synthetic beneficiary sessions.

PLAN.md section 5.1:
    07 | seed_users_demo.py | demo accounts: officer@demo / viewer@demo
       (password from env at bootstrap), 25 synthetic beneficiary sessions spread
       over 5 districts | users, sessions | Dashboard looks alive immediately

Everything written here is marked ``sessions.synthetic = true`` so the officer
dashboard can badge it, and the badge is visible in the footer (Gate 9).

RULE 6 is respected even for synthetic rows: no name is generated, phone is left
NULL, and a ``consents`` row is created **before** any profile slot is written —
the same ordering the live FSM enforces.

Distribution is deterministic (seeded RNG) and deliberately shaped so the
dashboard tells a true-to-life story:

* women share is set above the >=30% mandate so the compliance chip reads green,
  while one district sits below it so the gap panel has something to flag;
* a few sessions are ``degraded`` to show the fallback ladder having fired;
* a few have no consent, so the consent-completeness chip is not a flat 100%.
"""

from __future__ import annotations

import datetime as dt
import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "services"))

from core.models.tables import (  # noqa: E402
    Channel,
    Consent,
    ConsentMode,
    District,
    Session,
    Transcript,
)
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session as OrmSession  # noqa: E402

from pipelines.common import stable_rng  # noqa: E402

log = logging.getLogger("07_demo")

NAME = "07_seed_users_demo"

#: PLAN.md section 5.1 pipeline 07: "25 synthetic beneficiary sessions spread
#: over 5 districts".
TARGET_SESSIONS = 25
DEMO_DISTRICT_NAMES = ("Latur", "Nanded", "Varanasi", "Nalgonda", "Gaya")

#: Language per district — matches the state's language so the transcripts are
#: plausible (Marathi in Maharashtra, Telugu in Telangana, Hindi elsewhere).
DISTRICT_LANG = {
    "Latur": "mr",
    "Nanded": "mr",
    "Varanasi": "hi",
    "Nalgonda": "te",
    "Gaya": "hi",
}

AGE_BANDS = ("under_18", "18_30", "30_45", "45_plus")
EDU_LEVELS = ("none", "up_to_5th", "5th_8th", "8th_10th", "10th_12th", "grad_plus")
WORK = ("unemployed", "farm_labour", "artisan", "shg_member", "small_trade", "other")

#: Spoken aspirations per language, keyed by the crosswalk concept they express.
#: These are the phrases the synthetic transcripts contain, so the dashboard's
#: "top concepts" chart is driven by real crosswalk concepts.
ASPIRATIONS = {
    "hi": [
        ("tailoring", "मैं सिलाई का काम सीखना चाहती हूँ"),
        ("beauty", "ब्यूटी पार्लर का कोर्स करना है"),
        ("electrician", "बिजली का काम सीखना है"),
        ("mobile_repair", "मोबाइल रिपेयरिंग सीखनी है"),
        ("dairy", "दूध डेयरी का काम करना चाहता हूँ"),
        ("poultry", "मुर्गी पालन शुरू करना है"),
        ("food_processing", "अचार पापड़ का काम करना है"),
        ("retail", "दुकान पर काम करना चाहता हूँ"),
    ],
    "mr": [
        ("tailoring", "मला शिवणकाम शिकायचे आहे"),
        ("beauty", "ब्युटी पार्लरचा कोर्स करायचा आहे"),
        ("goatery", "शेळीपालन सुरू करायचे आहे"),
        ("dairy", "दूध डेअरीचे काम करायचे आहे"),
        ("handicrafts", "हस्तकला शिकायची आहे"),
        ("plumbing", "प्लंबिंगचे काम शिकायचे आहे"),
    ],
    "te": [
        ("tailoring", "నాకు కుట్టు పని నేర్చుకోవాలని ఉంది"),
        ("beauty", "బ్యూటీ పార్లర్ కోర్సు చేయాలి"),
        ("poultry", "కోళ్ల పెంపకం ప్రారంభించాలి"),
        ("data_entry", "డేటా ఎంట్రీ పని నేర్చుకోవాలి"),
        ("healthcare_attendant", "ఆసుపత్రిలో సహాయకురాలిగా పని చేయాలి"),
    ],
}


def _confirm_line(lang: str) -> str:
    return {
        "hi": "हाँ, सही है",
        "mr": "होय, बरोबर आहे",
        "te": "అవును, సరైనదే",
        "en": "Yes, that is right",
    }[lang]


def seed_sessions(db: OrmSession, target: int = TARGET_SESSIONS) -> int:
    """Create (idempotently) ``target`` synthetic sessions across 5 districts.

    Idempotent by count: if at least ``target`` synthetic sessions already exist
    the function is a no-op, so ``make seed`` can be run repeatedly.
    """
    existing = db.execute(
        select(func.count()).select_from(Session).where(Session.synthetic.is_(True))
    ).scalar_one()
    if existing >= target:
        log.info("%d synthetic sessions already present — nothing to do", existing)
        return existing

    districts = {
        d.name_en: d
        for d in db.execute(
            select(District).where(District.name_en.in_(DEMO_DISTRICT_NAMES))
        ).scalars()
    }
    missing = [n for n in DEMO_DISTRICT_NAMES if n not in districts]
    if missing:
        log.warning("demo districts missing from the seed: %s", missing)
    usable = [districts[n] for n in DEMO_DISTRICT_NAMES if n in districts]
    if not usable:
        log.error("no demo districts available — run pipeline 00 and `make seed` first")
        return existing

    rng = stable_rng("avsar-demo-sessions-v1")
    now = dt.datetime.now(dt.UTC)
    to_create = target - existing
    created = 0

    for idx in range(to_create):
        district = usable[idx % len(usable)]
        lang = DISTRICT_LANG.get(district.name_en, "hi")
        concept, utterance = rng.choice(ASPIRATIONS[lang])

        # Women share: 60% female overall so the >=30% mandate chip reads green,
        # except Gaya which is deliberately held at a low share so the dashboard
        # has a district that FAILS the mandate and the gap panel is not empty.
        if district.name_en == "Gaya":
            gender = "female" if rng.random() < 0.18 else "male"
        else:
            gender = "female" if rng.random() < 0.62 else rng.choice(["male", "other"])

        edu = rng.choice(EDU_LEVELS)
        # A handful of sessions used the fallback ladder.
        degraded = idx % 9 == 0
        # A couple never completed consent — the consent chip must not read 100%.
        consent_given = idx % 12 != 0

        created_at = now - dt.timedelta(days=rng.randint(0, 27), hours=rng.randint(0, 23))

        session = Session(
            channel=Channel.demo,
            lang=lang,
            state={
                "step": "summary" if consent_given else "consent",
                "slots": {
                    "district_code": district.code,
                    "age_band": None,
                    "gender": None,
                    "edu_level": None,
                    "current_work": None,
                },
                "retries": 0,
                "concept": concept if consent_given else None,
                "synthetic": True,
            },
            district_code=district.code,
            created_at=created_at,
            ended_at=created_at + dt.timedelta(minutes=rng.randint(2, 6)),
            degraded=degraded,
            synthetic=True,
        )
        db.add(session)
        db.flush()

        # RULE 6 / ARCHITECTURE section 9: consent is recorded BEFORE any profile
        # slot is persisted. A session without consent keeps its slots NULL.
        if consent_given:
            consent = Consent(
                session_id=session.id,
                mode=rng.choice([ConsentMode.spoken, ConsentMode.tapped]),
                granted=True,
                ts=created_at,
                playback_ref=f"dialogue.{lang}.json#consent.line",
            )
            db.add(consent)
            db.flush()
            session.consent_id = consent.id

            session.age_band = rng.choice(AGE_BANDS)
            session.gender = gender
            session.edu_level = edu
            session.current_work = rng.choice(WORK)
            # Self-reported annual income; most below the priority threshold.
            session.annual_income_inr = rng.choice(
                [48_000, 72_000, 96_000, 120_000, 180_000, 240_000, 310_000]
            )
            session.state["slots"] = {
                "district_code": district.code,
                "age_band": session.age_band,
                "gender": session.gender,
                "edu_level": session.edu_level,
                "current_work": session.current_work,
            }

            turns = [
                (1, utterance, rng.uniform(0.62, 0.94)),
                (2, _confirm_line(lang), rng.uniform(0.80, 0.97)),
            ]
            for turn_no, text, conf in turns:
                db.add(
                    Transcript(
                        session_id=session.id,
                        turn_no=turn_no,
                        asr_provider="mock",
                        raw_text=text,
                        confidence=round(conf, 3),
                        parsed_slots={"concept": concept} if turn_no == 1 else {"confirm": True},
                        latency_ms=rng.randint(1400, 4200),
                        created_at=created_at + dt.timedelta(seconds=30 * turn_no),
                    )
                )
        else:
            db.add(
                Transcript(
                    session_id=session.id,
                    turn_no=1,
                    asr_provider="mock",
                    raw_text=None,
                    confidence=0.0,
                    parsed_slots={"consent": "declined"},
                    latency_ms=rng.randint(900, 2000),
                    created_at=created_at + dt.timedelta(seconds=20),
                )
            )

        created += 1

    db.flush()
    total = db.execute(
        select(func.count()).select_from(Session).where(Session.synthetic.is_(True))
    ).scalar_one()
    log.info("created %d synthetic sessions (%d total)", created, total)
    return total


def attach_recommendations(db: OrmSession) -> int:
    """Attach top-3 recommendations to every consented synthetic session.

    Deferred to the recommendation engine so the seeded rows go through exactly
    the same deterministic scoring path a live session uses — a seeded
    recommendation a judge drills into must be reproducible, not decorative.
    Returns the number of sessions that now carry recommendations.
    """
    try:
        from core.domain.recommender import backfill_synthetic_recommendations
    except ImportError:
        log.info("recommendation engine not built yet — skipping (Gate 4 completes this)")
        return 0
    return backfill_synthetic_recommendations(db)


def run() -> int:
    from core.db import session_scope

    with session_scope() as db:
        total = seed_sessions(db)
        attach_recommendations(db)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
