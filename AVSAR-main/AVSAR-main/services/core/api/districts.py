"""District lookup for the profile step.

PLAN.md section 4.1 slot 1: *"District (dropdown by state; type-ahead)"*.

The list is served from the committed LGD seed (RULE 3 — no runtime call to any
government source), and names come back in the session language when a
script-verified local name exists, otherwise in English. The API never invents a
transliteration; see ``District.display_name``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as OrmSession

from core.db import get_db
from core.models.tables import District

router = APIRouter(prefix="/districts", tags=["districts"])

#: The five districts the demo is seeded across, surfaced first so a judge can
#: complete the journey without typing.
DEMO_DISTRICTS = ("Latur", "Nanded", "Varanasi", "Nalgonda", "Gaya")


def _serialise(district: District, lang: str) -> dict:
    return {
        "code": district.code,
        "name": district.display_name(lang),
        "name_en": district.name_en,
        "state": district.state_name,
        "demo": district.name_en in DEMO_DISTRICTS,
    }


@router.get("")
@router.get("/")
def list_districts(
    db: OrmSession = Depends(get_db),
    q: str | None = Query(default=None, description="type-ahead prefix"),
    lang: str = Query(default="hi"),
    limit: int = Query(default=8, ge=1, le=50),
) -> dict:
    """Type-ahead search; with no query, the demo districts lead."""
    lang = lang if lang in ("hi", "mr", "te", "en") else "hi"
    stmt = select(District)

    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(District.name_en).like(needle),
                func.lower(func.coalesce(District.name_local, "")).like(needle),
                func.lower(func.coalesce(District.name_hi, "")).like(needle),
                func.lower(func.coalesce(District.name_mr, "")).like(needle),
                func.lower(func.coalesce(District.name_te, "")).like(needle),
                func.lower(District.state_name).like(needle),
            )
        )
    else:
        stmt = stmt.where(District.name_en.in_(DEMO_DISTRICTS))

    rows = db.execute(stmt.order_by(District.name_en).limit(limit)).scalars().all()
    return {"items": [_serialise(d, lang) for d in rows], "lang": lang}


@router.get("/{code}")
def get_district(
    code: str, db: OrmSession = Depends(get_db), lang: str = Query(default="hi")
) -> dict:
    district = db.execute(select(District).where(District.code == code)).scalar_one_or_none()
    if district is None:
        return {"found": False, "code": code}
    return {"found": True, **_serialise(district, lang)}
