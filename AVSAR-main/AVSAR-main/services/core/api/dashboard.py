"""Officer dashboard statistics — ARCHITECTURE.md section 5.

    GET /dashboard/stats?district&from&to
        -> {by_domain[], top_concepts[], women_pct, priority_income_pct}
    GET /dashboard/gap?district  -> [{concept, demand_n, supply_seats}]

PLAN.md section 4.2 describes what these feed:

* top-aspirations chart by GIA domain plus top activity concepts;
* a **gap panel** — *"for selected district — top aspirations vs courses
  available in catalogue for that district's centres (seed table), flagged when
  demand concept has no nearby QP supply"*;
* **compliance chips** — *"% women captured (target >=30% mandate), %
  priority-income (<= Rs 2.5L self-reported), % consent-complete"*;
* session drill-down with transcript, parsed slots, recommended QPs and consent.

Row-level access follows ARCHITECTURE section 9: *"route-level guards +
row-level (individual beneficiary rows hidden from ``viewer``)"*. A viewer sees
aggregates; only officer+ can open an individual session.

Every response carries a ``synthetic`` summary so the UI can badge the data
honestly — the dashboard must never present seeded or fallback rows as real
field intake.
"""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.orm import Session as OrmSession

from core.api.security import Principal, require_officer, require_viewer
from core.db import get_db
from core.domain.scheme_constants import (
    PRIORITY_INCOME_CEILING_INR,
    WOMEN_PARTICIPATION_FLOOR_PCT,
    gia_domain_name,
    priority_income_status,
    women_participation_status,
)
from core.errors import AvsarError
from core.models.tables import (
    CentreSupply,
    Consent,
    Course,
    Crosswalk,
    District,
    Recommendation,
    Transcript,
)
from core.models.tables import (
    Session as SessionRow,
)

log = logging.getLogger("avsar.dashboard")
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _window(db: OrmSession, district: str | None, date_from: str | None, date_to: str | None):
    """Build the shared session filter for every panel."""
    clauses = []
    if district:
        clauses.append(SessionRow.district_code == district)
    if date_from:
        clauses.append(cast(SessionRow.created_at, Date) >= dt.date.fromisoformat(date_from))
    if date_to:
        clauses.append(cast(SessionRow.created_at, Date) <= dt.date.fromisoformat(date_to))
    return and_(*clauses) if clauses else None


def _concept_of(session_state: dict | None, parsed: dict | None) -> str | None:
    if session_state and session_state.get("concept"):
        return session_state["concept"]
    if parsed and parsed.get("concept"):
        return parsed["concept"]
    return None


@router.get("/stats")
def stats(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_viewer),
    district: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="from"),
    date_to: str | None = Query(default=None, alias="to"),
) -> dict:
    """Aggregates for the charts and the compliance chips."""
    where = _window(db, district, date_from, date_to)

    base = select(SessionRow)
    if where is not None:
        base = base.where(where)
    sessions = db.execute(base).scalars().all()
    total = len(sessions)

    if total == 0:
        return {
            "total_sessions": 0,
            "by_domain": [],
            "top_concepts": [],
            "compliance": {},
            "synthetic": {"sessions": 0, "share_pct": 0.0},
            "filters": {"district": district, "from": date_from, "to": date_to},
        }

    # ---- concepts, via the crosswalk the transcripts were parsed against
    concept_rows = db.execute(
        select(Transcript.session_id, Transcript.parsed_slots).where(
            Transcript.session_id.in_([s.id for s in sessions])
        )
    ).all()
    parsed_by_session: dict = {}
    for session_id, parsed in concept_rows:
        if parsed and parsed.get("concept"):
            parsed_by_session.setdefault(session_id, parsed)

    concept_counts: dict[str, int] = {}
    for session in sessions:
        concept = _concept_of(session.state, parsed_by_session.get(session.id))
        if concept:
            concept_counts[concept] = concept_counts.get(concept, 0) + 1

    # ---- map concepts onto the 10 GIA domains
    domain_of: dict[str, int] = {}
    if concept_counts:
        for concept, domain in db.execute(
            select(Crosswalk.concept, Crosswalk.gia_domain)
            .where(Crosswalk.concept.in_(list(concept_counts)))
            .distinct()
        ):
            domain_of.setdefault(concept, domain)

    domain_counts: dict[int, int] = {}
    for concept, count in concept_counts.items():
        domain = domain_of.get(concept)
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + count

    by_domain = [
        {
            "gia_domain": domain,
            "name": gia_domain_name(domain, "en"),
            "name_hi": gia_domain_name(domain, "hi"),
            "count": count,
        }
        for domain, count in sorted(domain_counts.items(), key=lambda kv: -kv[1])
    ]

    top_concepts = [
        {"concept": concept, "count": count, "gia_domain": domain_of.get(concept)}
        for concept, count in sorted(concept_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    ]

    # ---- compliance chips
    women = sum(1 for s in sessions if s.gender == "female")
    women_pct = 100.0 * women / total
    with_income = [s for s in sessions if s.annual_income_inr is not None]
    priority = sum(
        1 for s in with_income if s.annual_income_inr <= PRIORITY_INCOME_CEILING_INR
    )
    consented = sum(1 for s in sessions if s.consent_id is not None)
    degraded = sum(1 for s in sessions if s.degraded)
    synthetic = sum(1 for s in sessions if s.synthetic)

    compliance = {
        "women": {
            **women_participation_status(women_pct),
            "count": women,
            "total": total,
        },
        "priority_income": {
            "pct": round(100.0 * priority / len(with_income), 1) if with_income else None,
            "count": priority,
            "reported": len(with_income),
            **priority_income_status(None),
        },
        "consent_complete": {
            "pct": round(100.0 * consented / total, 1),
            "count": consented,
            "total": total,
        },
        "degraded": {"pct": round(100.0 * degraded / total, 1), "count": degraded},
    }

    return {
        "total_sessions": total,
        "by_domain": by_domain,
        "top_concepts": top_concepts,
        "women_pct": round(women_pct, 1),
        "priority_income_pct": compliance["priority_income"]["pct"],
        "consent_pct": compliance["consent_complete"]["pct"],
        "compliance": compliance,
        "synthetic": {
            "sessions": synthetic,
            "share_pct": round(100.0 * synthetic / total, 1),
            "note": (
                "Synthetic sessions are seeded demo data, not real field intake. "
                "See docs/ingest-report.md."
            ),
        },
        "filters": {"district": district, "from": date_from, "to": date_to},
        "can_drill_down": principal.role in ("officer", "admin"),
    }


@router.get("/gap")
def gap(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_viewer),
    district: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Demand (captured aspirations) versus local supply (seats).

    PLAN.md §4.2: flag a concept when demand exists and there is no nearby QP
    supply. Two distinct kinds of gap are reported separately, because they need
    different fixes:

    * ``no_local_supply`` — the QPs exist but no centre in this district offers
      them. Fix: open a batch.
    * ``no_qualification`` — no QP exists in the register at all (the declared
      crosswalk gaps, e.g. poultry). Fix: NCVET has to publish one, or the real
      PM-AJAY catalogue has to become reachable.
    """
    where = _window(db, district, None, None)
    base = select(SessionRow)
    if where is not None:
        base = base.where(where)
    sessions = db.execute(base).scalars().all()

    parsed_rows = db.execute(
        select(Transcript.session_id, Transcript.parsed_slots)
    ).all() if sessions else []
    parsed_by_session: dict = {}
    for session_id, parsed in parsed_rows:
        if parsed and parsed.get("concept"):
            parsed_by_session.setdefault(session_id, parsed)

    demand: dict[str, int] = {}
    for session in sessions:
        concept = _concept_of(session.state, parsed_by_session.get(session.id))
        if concept:
            demand[concept] = demand.get(concept, 0) + 1

    if not demand:
        return {"district": district, "items": [], "note": "no captured aspirations in this window"}

    # concept -> qp codes, from the curated crosswalk
    qp_by_concept: dict[str, set[str]] = {}
    for concept, codes in db.execute(
        select(Crosswalk.concept, Crosswalk.qp_codes).where(Crosswalk.concept.in_(list(demand)))
    ):
        qp_by_concept.setdefault(concept, set()).update(codes or [])

    # seats per qp code in the district
    supply_stmt = select(CentreSupply.qp_code, func.coalesce(func.sum(CentreSupply.seats), 0))
    if district:
        supply_stmt = supply_stmt.where(CentreSupply.district_code == district)
    supply_stmt = supply_stmt.group_by(CentreSupply.qp_code)
    seats_by_qp = {code: int(seats) for code, seats in db.execute(supply_stmt)}

    items = []
    for concept, demand_n in sorted(demand.items(), key=lambda kv: -kv[1]):
        codes = qp_by_concept.get(concept, set())
        seats = sum(seats_by_qp.get(code, 0) for code in codes)
        if not codes:
            status, flag = "no_qualification", True
        elif seats == 0:
            status, flag = "no_local_supply", True
        else:
            status, flag = "supplied", False
        items.append(
            {
                "concept": concept,
                "demand_n": demand_n,
                "supply_seats": seats,
                "qp_codes": sorted(codes),
                "status": status,
                "flagged": flag,
            }
        )

    return {
        "district": district,
        "items": items[:limit],
        "flagged": sum(1 for i in items if i["flagged"]),
        "legend": {
            "no_qualification": "No QP exists in the register for this aspiration",
            "no_local_supply": "QPs exist but no centre in this district offers them",
        },
    }


@router.get("/sessions")
def list_sessions(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_officer),
    district: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Individual session rows — **officer+ only** (ARCHITECTURE §9 row-level)."""
    where = _window(db, district, None, None)
    stmt = select(SessionRow).order_by(SessionRow.created_at.desc())
    count_stmt = select(func.count()).select_from(SessionRow)
    if where is not None:
        stmt = stmt.where(where)
        count_stmt = count_stmt.where(where)

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.limit(limit).offset(offset)).scalars().all()

    names = dict(db.execute(select(District.code, District.name_en)).all())
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "session_id": str(s.id),
                "district_code": s.district_code,
                "district": names.get(s.district_code),
                "lang": s.lang,
                "channel": s.channel.value,
                "age_band": s.age_band,
                "gender": s.gender,
                "edu_level": s.edu_level,
                "current_work": s.current_work,
                "consent": s.consent_id is not None,
                "degraded": s.degraded,
                "synthetic": s.synthetic,
                "officer_callback": s.officer_callback,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                # RULE 6: there is no name to show, and phone is never listed.
            }
            for s in rows
        ],
    }


@router.get("/sessions/{session_id}")
def session_detail(
    session_id: str,
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_officer),
) -> dict:
    """Drill-down: transcript, parsed slots, recommended QPs + scores, consent."""
    import uuid as _uuid

    try:
        uid = _uuid.UUID(session_id)
    except ValueError:
        raise AvsarError(404, "session_not_found", principal.lang)

    session = db.execute(select(SessionRow).where(SessionRow.id == uid)).scalar_one_or_none()
    if session is None:
        raise AvsarError(404, "session_not_found", principal.lang)

    transcripts = db.execute(
        select(Transcript).where(Transcript.session_id == uid).order_by(Transcript.turn_no)
    ).scalars().all()
    recommendations = db.execute(
        select(Recommendation, Course)
        .join(Course, Course.id == Recommendation.course_id)
        .where(Recommendation.session_id == uid)
        .order_by(Recommendation.rank)
    ).all()
    consents = db.execute(
        select(Consent).where(Consent.session_id == uid).order_by(Consent.ts)
    ).scalars().all()
    district = (
        db.execute(select(District).where(District.code == session.district_code)).scalar_one_or_none()
        if session.district_code
        else None
    )

    return {
        "session_id": str(session.id),
        "lang": session.lang,
        "channel": session.channel.value,
        "district": {"code": session.district_code, "name": district.name_en if district else None},
        "profile": {
            "age_band": session.age_band,
            "gender": session.gender,
            "edu_level": session.edu_level,
            "current_work": session.current_work,
            "annual_income_inr": session.annual_income_inr,
        },
        "state": session.state,
        "degraded": session.degraded,
        "synthetic": session.synthetic,
        "officer_callback": session.officer_callback,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "consent": {
            "granted": any(c.granted for c in consents),
            "records": [
                {
                    "mode": c.mode.value,
                    "granted": c.granted,
                    "ts": c.ts.isoformat() if c.ts else None,
                    "playback_ref": c.playback_ref,
                }
                for c in consents
            ],
        },
        "transcript": [
            {
                "turn_no": t.turn_no,
                "provider": t.asr_provider,
                "text": t.raw_text,
                "confidence": t.confidence,
                "parsed_slots": t.parsed_slots,
                "latency_ms": t.latency_ms,
            }
            for t in transcripts
        ],
        "recommendations": [
            {
                "rank": rec.rank,
                "qp_code": course.qp_code,
                "name": course.sub_course,
                "nsqf_level": float(course.nsqf_level) if course.nsqf_level is not None else None,
                "sector": course.sector,
                "score": rec.score,
                "factors": rec.factors,
                "grounded": rec.grounded,
                "confirmed": rec.confirmed,
                "synthetic": bool(course.synthetic),
                "provenance": {
                    "source_name": getattr(course.source, "value", course.source),
                    "synthetic": bool(course.synthetic),
                },
            }
            for rec, course in recommendations
        ],
        "compliance_note": (
            f"Women participation mandate is at least {WOMEN_PARTICIPATION_FLOOR_PCT}% "
            "of skill-programme candidates."
        ),
    }


@router.get("/districts")
def district_rollup(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_viewer),
) -> dict:
    """Per-district counts for the map/list toggle (PLAN §4.2)."""
    rows = db.execute(
        select(
            SessionRow.district_code,
            func.count().label("n"),
            func.count().filter(SessionRow.gender == "female").label("women"),
            func.count().filter(SessionRow.consent_id.isnot(None)).label("consented"),
            func.count().filter(SessionRow.synthetic.is_(True)).label("synthetic"),
        )
        .where(SessionRow.district_code.isnot(None))
        .group_by(SessionRow.district_code)
    ).all()

    names = {
        code: (name, state)
        for code, name, state in db.execute(
            select(District.code, District.name_en, District.state_name)
        )
    }
    items = []
    for code, n, women, consented, synthetic in rows:
        name, state = names.get(code, (code, None))
        women_pct = round(100.0 * women / n, 1) if n else 0.0
        items.append(
            {
                "district_code": code,
                "district": name,
                "state": state,
                "sessions": n,
                "women": women,
                "women_pct": women_pct,
                "meets_women_mandate": women_pct >= float(WOMEN_PARTICIPATION_FLOOR_PCT),
                "consent_pct": round(100.0 * consented / n, 1) if n else 0.0,
                "synthetic": synthetic,
            }
        )
    items.sort(key=lambda i: -i["sessions"])
    return {"items": items, "women_mandate_pct": float(WOMEN_PARTICIPATION_FLOOR_PCT)}
