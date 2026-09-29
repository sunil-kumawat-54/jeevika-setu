"""Canonical, provenance-aware read paths for grounded recommendations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from core.db import get_db
from core.models.tables import Opportunity, Pathway, Programme, Qualification
from core.rag.retrieve import hybrid_search

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

MAX_MOBILITY_RADIUS_KM = 100


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _provenance(row: object) -> dict:
    return {
        "source_name": getattr(row, "source_name", None),
        "source_version": getattr(row, "source_version", None),
        "source_record_id": getattr(row, "source_record_id", None),
        "fetched_at": getattr(row, "fetched_at", None),
        "last_verified_at": getattr(row, "last_verified_at", None),
        "freshness_at": getattr(row, "freshness_at", None),
        "verification_status": _enum_value(getattr(row, "verification_status", None)),
        "synthetic": bool(getattr(row, "synthetic", False)),
        "record_fingerprint": getattr(row, "record_fingerprint", None),
    }


def _iso(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _qualification_payload(qualification: Qualification, pathways: list[Pathway], programmes: list[Programme], opportunities: list[Opportunity]) -> dict:
    return {
        "id": qualification.id,
        "qp_code": qualification.qp_code,
        "version_id": qualification.version_id,
        "name": qualification.name,
        "nsqf_level": str(qualification.nsqf_level) if isinstance(qualification.nsqf_level, Decimal) else qualification.nsqf_level,
        "sector": qualification.sector,
        "duration_hours": {
            "min": qualification.min_hours,
            "max": qualification.max_hours,
        },
        "provenance": _provenance(qualification),
        "pathways": [
            {
                "type": _enum_value(pathway.pathway_type),
                "title": pathway.title,
                "duration_hours": pathway.duration_hours,
                "synthetic": bool(pathway.synthetic),
            }
            for pathway in pathways
        ],
        "programmes": [
            {
                "id": programme.id,
                "type": _enum_value(programme.programme_type),
                "title": programme.title,
                "seats": programme.seats,
                "centre_id": programme.centre_id,
                "provenance": _provenance(programme),
            }
            for programme in programmes
        ],
        "opportunities": [
            {
                "id": opportunity.id,
                "type": _enum_value(opportunity.opportunity_type),
                "title": opportunity.title,
                "mobility_radius_km": str(opportunity.mobility_radius_km) if isinstance(opportunity.mobility_radius_km, Decimal) else opportunity.mobility_radius_km,
                "provenance": _provenance(opportunity),
            }
            for opportunity in opportunities
        ],
    }


def _nearby_centres(db: Session, district_code: str | None, latitude: float | None, longitude: float | None, radius_km: float) -> dict:
    """Return only database-calculated distances for an explicit coarse origin."""
    if not district_code or latitude is None or longitude is None:
        return {"status": "missing_origin", "items": []}
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return {"status": "missing_origin", "items": []}
    if not 0 < radius_km <= MAX_MOBILITY_RADIUS_KM:
        return {"status": "no_results", "items": []}

    origin = "ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography"
    eligible = "coordinate_status IN ('verified', 'synthetic') AND location IS NOT NULL AND freshness_at >= now()"
    rows = db.execute(
        text(
            f"SELECT id, centre_name, district_code, coordinate_status, synthetic, "
            f"source_name, source_version, source_record_id, freshness_at, "
            f"ST_Distance(location, {origin}) AS distance_m "
            f"FROM training_centres "
            f"WHERE district_code = :district_code AND {eligible} "
            f"AND ST_DWithin(location, {origin}, :radius_m) "
            f"ORDER BY ST_Distance(location, {origin}) ASC, id ASC"
        ),
        {
            "district_code": district_code,
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_km * 1000,
        },
    ).mappings().all()
    if rows:
        return {
            "status": "ok",
            "items": [
                {
                    "id": row["id"],
                    "name": row["centre_name"],
                    "district_code": row["district_code"],
                    "distance_m": row["distance_m"],
                    "coordinate_status": _enum_value(row["coordinate_status"]),
                    "synthetic": bool(row["synthetic"]),
                    "provenance": {
                        "source_name": row["source_name"],
                        "source_version": row["source_version"],
                        "source_record_id": row["source_record_id"],
                        "freshness_at": _iso(row["freshness_at"]),
                    },
                }
                for row in rows
            ],
        }

    status = db.execute(
        text(
            "SELECT CASE "
            "WHEN bool_or(coordinate_status = 'stale') THEN 'stale_coordinates' "
            "WHEN bool_or(location IS NULL OR coordinate_status IN ('missing', 'rejected')) THEN 'missing_coordinates' "
            "ELSE 'no_results' END "
            "FROM training_centres WHERE district_code = :district_code"
        ),
        {"district_code": district_code},
    ).scalar_one_or_none() or "no_results"
    return {"status": status, "items": []}


def grounded_read(
    db: Session,
    question: str,
    *,
    district_code: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float = 15,
) -> dict:
    """Resolve retrieval candidates to canonical rows before constructing facts."""
    candidates = hybrid_search(db, question, limit=20)
    qp_codes = {str(candidate["qp_code"]) for candidate in candidates if candidate.get("qp_code")}
    pattern = f"%{question.strip()}%" if question and question.strip() else None
    filters = [Qualification.qp_code.in_(qp_codes)] if qp_codes else []
    if pattern:
        filters.append(or_(Qualification.name.ilike(pattern), Qualification.qp_code.ilike(pattern)))
    qualifications = db.execute(select(Qualification).where(or_(*filters))).scalars().unique().all() if filters else []
    qualification_ids = [qualification.id for qualification in qualifications]
    pathways = db.execute(select(Pathway).where(Pathway.qualification_id.in_(qualification_ids))).scalars().all() if qualification_ids else []
    programmes = db.execute(select(Programme).where(Programme.qualification_id.in_(qualification_ids))).scalars().all() if qualification_ids else []
    opportunities = db.execute(select(Opportunity).where(Opportunity.qualification_id.in_(qualification_ids))).scalars().all() if qualification_ids else []
    pathway_by_qp = {qualification.id: [row for row in pathways if row.qualification_id == qualification.id] for qualification in qualifications}
    programme_by_qp = {qualification.id: [row for row in programmes if row.qualification_id == qualification.id] for qualification in qualifications}
    opportunity_by_qp = {qualification.id: [row for row in opportunities if row.qualification_id == qualification.id] for qualification in qualifications}
    return {
        "status": "ok" if qualifications else "no_results",
        "candidates": [_qualification_payload(qualification, pathway_by_qp[qualification.id], programme_by_qp[qualification.id], opportunity_by_qp[qualification.id]) for qualification in qualifications],
        "nearby_centres": _nearby_centres(db, district_code, latitude, longitude, radius_km),
        "retrieval": {"candidate_count": len(candidates), "authorized_count": len(qualifications)},
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/grounded")
def grounded_recommendation(
    q: str = Query(min_length=1, max_length=500),
    district_code: str | None = Query(default=None, max_length=8),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    radius_km: float = Query(default=15, gt=0, le=MAX_MOBILITY_RADIUS_KM),
    db: Session = Depends(get_db),
) -> dict:
    return grounded_read(
        db,
        q,
        district_code=district_code,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
