"""Exports — ARCHITECTURE.md section 5.

    GET /exports/sessions.csv | /exports/aap.xlsx    # officer+

PLAN.md section 4.2:
    **Export**: CSV of filtered sessions; "AAP annexure" XLSX grouping by GIA
    domain with counts — mimics what an Annual Action Plan needs.

The AAP framing is the point. research.md section 2.3 records that Annual Action
Plans are *"prepared per local requirements and uploaded on
pmajay.dosje.gov.in"*, and section 2.5 shows chronic under-absorption
(Rs 736.28 cr actual against Rs 2,140 cr BE in 2024-25). An officer who can
export a district's captured aspirations already grouped by GIA domain is one
step closer to a submittable plan — which is the absorption story the product
claims.

RULE 6 governs every column: there is no name to export, and phone numbers are
not exported even though a phone may exist on the user row.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from core.api.security import Principal, require_officer
from core.db import get_db
from core.domain.scheme_constants import (
    COMPLIANCE_CITATION,
    GUIDELINES_TITLE,
    SKILLING_FLOOR_PCT,
    WOMEN_PARTICIPATION_FLOOR_PCT,
    gia_domain_name,
)
from core.models.tables import (
    Course,
    Crosswalk,
    District,
    Recommendation,
    Transcript,
)
from core.models.tables import (
    Session as SessionRow,
)

log = logging.getLogger("avsar.exports")
router = APIRouter(prefix="/exports", tags=["exports"])

#: Hard cap on rows per export. An arbitrary paging limit, chosen so it does
#: not collide with any PM-AJAY scheme figure — that keeps the RULE 4 guard
#: (which greps for duplicated scheme constants) maximally strict rather than
#: teaching it exceptions.
MAX_EXPORT_ROWS = 20_000

CSV_COLUMNS = [
    "session_id",
    "created_at",
    "district_code",
    "district",
    "state",
    "lang",
    "channel",
    "age_band",
    "gender",
    "edu_level",
    "current_work",
    "aspiration_concept",
    "gia_domain",
    "gia_domain_name",
    "recommended_qp_1",
    "recommended_course_1",
    "nsqf_level_1",
    "score_1",
    "recommended_qp_2",
    "recommended_qp_3",
    "confirmed_qp",
    "consent_granted",
    "degraded",
    "synthetic",
    "officer_callback",
]


def _rows(db: OrmSession, district: str | None, limit: int) -> list[dict]:
    stmt = select(SessionRow).order_by(SessionRow.created_at.desc()).limit(limit)
    if district:
        stmt = stmt.where(SessionRow.district_code == district)
    sessions = db.execute(stmt).scalars().all()
    if not sessions:
        return []

    ids = [s.id for s in sessions]
    districts = {
        code: (name, state)
        for code, name, state in db.execute(
            select(District.code, District.name_en, District.state_name)
        )
    }

    concepts: dict = {}
    for session_id, parsed in db.execute(
        select(Transcript.session_id, Transcript.parsed_slots).where(
            Transcript.session_id.in_(ids)
        )
    ):
        if parsed and parsed.get("concept"):
            concepts.setdefault(session_id, parsed["concept"])

    domain_of = dict(
        db.execute(select(Crosswalk.concept, Crosswalk.gia_domain).distinct()).all()
    )

    recs: dict = {}
    for rec, course in db.execute(
        select(Recommendation, Course)
        .join(Course, Course.id == Recommendation.course_id)
        .where(Recommendation.session_id.in_(ids))
        .order_by(Recommendation.rank)
    ):
        recs.setdefault(rec.session_id, []).append((rec, course))

    out = []
    for session in sessions:
        concept = (session.state or {}).get("concept") or concepts.get(session.id)
        domain = domain_of.get(concept) if concept else None
        mine = recs.get(session.id, [])
        name, state = districts.get(session.district_code, (None, None))
        confirmed = next((c.qp_code for r, c in mine if r.confirmed), None)

        row = {
            "session_id": str(session.id),
            "created_at": session.created_at.isoformat() if session.created_at else "",
            "district_code": session.district_code or "",
            "district": name or "",
            "state": state or "",
            "lang": session.lang,
            "channel": session.channel.value,
            "age_band": session.age_band or "",
            "gender": session.gender or "",
            "edu_level": session.edu_level or "",
            "current_work": session.current_work or "",
            "aspiration_concept": concept or "",
            "gia_domain": domain or "",
            "gia_domain_name": gia_domain_name(domain, "en") if domain else "",
            "confirmed_qp": confirmed or "",
            "consent_granted": "yes" if session.consent_id else "no",
            "degraded": "yes" if session.degraded else "no",
            "synthetic": "yes" if session.synthetic else "no",
            "officer_callback": "yes" if session.officer_callback else "no",
        }
        for index in range(3):
            if index < len(mine):
                rec, course = mine[index]
                row[f"recommended_qp_{index + 1}"] = course.qp_code
                if index == 0:
                    row["recommended_course_1"] = course.sub_course
                    row["nsqf_level_1"] = (
                        float(course.nsqf_level) if course.nsqf_level is not None else ""
                    )
                    row["score_1"] = round(rec.score, 4)
            else:
                row[f"recommended_qp_{index + 1}"] = ""
        row.setdefault("recommended_course_1", "")
        row.setdefault("nsqf_level_1", "")
        row.setdefault("score_1", "")
        out.append(row)
    return out


@router.get("/sessions.csv")
def sessions_csv(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_officer),
    district: str | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=MAX_EXPORT_ROWS),
) -> StreamingResponse:
    """CSV of filtered sessions. No name column exists to export (RULE 6)."""
    rows = _rows(db, district, limit)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    body = buffer.getvalue()
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    filename = f"avsar-sessions-{district or 'all'}-{stamp}.csv"
    log.info("exported %d session rows as CSV", len(rows), extra={"event": "export_csv"})
    return StreamingResponse(
        # BOM so Excel opens Devanagari/Telugu correctly on a Windows desktop —
        # the officer's actual tool.
        iter([("﻿" + body).encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/aap.xlsx")
def aap_xlsx(
    db: OrmSession = Depends(get_db),
    principal: Principal = Depends(require_officer),
    district: str | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=MAX_EXPORT_ROWS),
) -> Response:
    """AAP annexure: aspirations grouped by GIA domain, plus the raw rows.

    Three sheets so the file is usable as-is:
      1. **AAP Annexure** — counts by GIA domain, the shape a plan needs.
      2. **Sessions** — the underlying rows, for audit.
      3. **Compliance** — the mandate figures with their citation, so a
         reviewer can check the numbers against the guidelines.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    rows = _rows(db, district, limit)
    workbook = Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4338CA")

    def style_header(sheet, width_map: dict[int, int]):
        for cell in sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(vertical="center")
        for index, width in width_map.items():
            sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.freeze_panes = "A2"

    # ---- Sheet 1: AAP annexure
    annexure = workbook.active
    annexure.title = "AAP Annexure"
    annexure.append(
        ["GIA Domain", "Domain Name", "Aspirations Captured", "Women", "Women %", "Districts"]
    )
    grouped: dict = {}
    for row in rows:
        domain = row["gia_domain"] or 0
        bucket = grouped.setdefault(domain, {"n": 0, "women": 0, "districts": set()})
        bucket["n"] += 1
        if row["gender"] == "female":
            bucket["women"] += 1
        if row["district"]:
            bucket["districts"].add(row["district"])

    for domain in sorted(grouped, key=lambda d: -grouped[d]["n"]):
        bucket = grouped[domain]
        annexure.append(
            [
                domain or "",
                gia_domain_name(domain, "en") if domain else "(unclassified)",
                bucket["n"],
                bucket["women"],
                round(100.0 * bucket["women"] / bucket["n"], 1) if bucket["n"] else 0.0,
                ", ".join(sorted(bucket["districts"])),
            ]
        )
    style_header(annexure, {1: 12, 2: 34, 3: 20, 4: 10, 5: 10, 6: 40})

    # ---- Sheet 2: raw sessions
    sheet = workbook.create_sheet("Sessions")
    sheet.append(CSV_COLUMNS)
    for row in rows:
        sheet.append([row.get(column, "") for column in CSV_COLUMNS])
    style_header(sheet, {1: 38, 2: 22, 4: 16, 12: 20, 14: 30, 16: 30})

    # ---- Sheet 3: compliance, with citations
    compliance = workbook.create_sheet("Compliance")
    compliance.append(["Metric", "Value", "Mandate", "Meets mandate", "Source"])
    total = len(rows)
    women = sum(1 for r in rows if r["gender"] == "female")
    women_pct = round(100.0 * women / total, 1) if total else 0.0
    consent = sum(1 for r in rows if r["consent_granted"] == "yes")
    synthetic = sum(1 for r in rows if r["synthetic"] == "yes")

    compliance.append(
        [
            "Women participation",
            f"{women_pct}%",
            f">= {WOMEN_PARTICIPATION_FLOOR_PCT}%",
            "YES" if women_pct >= float(WOMEN_PARTICIPATION_FLOOR_PCT) else "NO",
            GUIDELINES_TITLE,
        ]
    )
    compliance.append(
        [
            "Skilling spend floor",
            "n/a (finance system)",
            f">= {SKILLING_FLOOR_PCT}% of SCA",
            "-",
            GUIDELINES_TITLE,
        ]
    )
    compliance.append(
        [
            "Consent completeness",
            f"{round(100.0 * consent / total, 1) if total else 0.0}%",
            "100% before profiling",
            "YES" if consent == total else "NO",
            "DPDP Act 2023 s.6",
        ]
    )
    compliance.append(
        [
            "Aspiration + job-market endorsement",
            f"{total} aspirations captured",
            "Required per job role",
            "-",
            COMPLIANCE_CITATION,
        ]
    )
    compliance.append(
        [
            "Synthetic rows in this export",
            f"{synthetic} of {total}",
            "Must be labelled, never presented as real",
            "LABELLED",
            "docs/ingest-report.md",
        ]
    )
    style_header(compliance, {1: 38, 2: 26, 3: 30, 4: 16, 5: 46})

    stream = io.BytesIO()
    workbook.save(stream)
    stream.seek(0)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    filename = f"avsar-aap-annexure-{district or 'all'}-{stamp}.xlsx"
    log.info("exported %d session rows as XLSX", len(rows), extra={"event": "export_xlsx"})
    return Response(
        content=stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
