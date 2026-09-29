"""Phase 2 schema and privacy-safe spatial acceptance tests."""

from __future__ import annotations

import decimal
import pathlib

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from core.models.tables import (
    Opportunity,
    Programme,
    Qualification,
)

REPO = pathlib.Path(__file__).resolve().parents[3]


def test_0003_is_linear_child_of_0002():
    source = (REPO / "services/core/alembic/versions/0003_canonical_knowledge_provenance_spatial.py").read_text()
    assert 'revision: str = "0003_canonical_spatial"' in source
    assert len("0003_canonical_spatial") <= 32
    assert 'down_revision: str | None = "0002_doc_chunk_identity"' in source


def test_no_beneficiary_origin_or_home_coordinate_column(db_session):
    columns = {
        (table, column["name"])
        for table in inspect(db_session.get_bind()).get_table_names()
        for column in inspect(db_session.get_bind()).get_columns(table)
    }
    assert not any("beneficiary" in table or "home" in name for table, name in columns)
    assert not any(name in {"latitude", "longitude", "home_point", "beneficiary_point"} for _, name in columns)


def test_centre_status_and_provenance_are_explicit(db_session):
    columns = {column["name"] for column in inspect(db_session.get_bind()).get_columns("training_centres")}
    assert {"coordinate_status", "source_name", "source_record_id", "fetched_at", "last_verified_at", "freshness_at", "synthetic"} <= columns
    enum_values = set(
        db_session.execute(
            text("SELECT enumlabel FROM pg_enum WHERE enumtypid = 'coordinate_status'::regtype")
        ).scalars()
    )
    assert enum_values == {"verified", "synthetic", "missing", "stale", "rejected"}


def test_tracer_persists_verified_centre_programme_opportunity(db_session):
    qualification = Qualification(
        qp_code="TEST/TRACER-QP",
        version_id=987655,
        name="Spatial tracer",
        nsqf_level=decimal.Decimal("4.5"),
        source_name="tracer",
        source_version="v1",
        source_record_id="qualification-v1",
        verification_status="verified",
        record_fingerprint="b" * 64,
    )
    db_session.add(qualification)
    db_session.flush()
    district = db_session.execute(text("SELECT code FROM districts LIMIT 1")).scalar_one()
    db_session.execute(
        text(
            """INSERT INTO training_centres
            (district_code, centre_name, location, coordinate_status, source_name, source_version,
             source_record_id, fetched_at, last_verified_at, freshness_at, verification_status, synthetic, record_fingerprint)
            VALUES (:district, 'Tracer Centre', ST_GeogFromText('SRID=4326;POINT(77.5946 12.9716)'),
                    'verified', 'tracer', 'v1', 'centre-v1', now(), now(), now(), 'verified', false, :fingerprint)
            RETURNING id"""
        ),
        {"district": district, "fingerprint": "c" * 64},
    )
    centre_id = db_session.execute(text("SELECT id FROM training_centres WHERE source_record_id = 'centre-v1'")).scalar_one()
    db_session.add(
        Programme(
            centre_id=centre_id,
            qualification_id=qualification.id,
            programme_type="training",
            title="Tracer programme",
            seats=12,
            source_name="tracer",
            source_record_id="programme-v1",
            verification_status="verified",
            synthetic=False,
        )
    )
    db_session.add(
        Opportunity(
            district_code=district,
            opportunity_type="job",
            title="Tracer opportunity",
            qualification_id=qualification.id,
            mobility_radius_km=decimal.Decimal("12.50"),
            source_name="tracer",
            source_record_id="opportunity-v1",
            verification_status="verified",
            synthetic=False,
        )
    )
    db_session.flush()
    row = db_session.execute(
        text("SELECT c.coordinate_status, c.synthetic, p.title, o.opportunity_type FROM training_centres c JOIN programmes p ON p.centre_id = c.id JOIN opportunities o ON o.qualification_id = p.qualification_id WHERE c.source_record_id = 'centre-v1'")
    ).one()
    assert (row.coordinate_status, row.synthetic, row.title, row.opportunity_type) == ("verified", False, "Tracer programme", "job")
    spatial = db_session.execute(
        text(
            """SELECT ST_DWithin(location, ST_GeogFromText('SRID=4326;POINT(77.5946 12.9716)'), 1000) AS nearby,
                    ST_Distance(location, ST_GeogFromText('SRID=4326;POINT(77.5946 12.9716)')) AS distance_m
               FROM training_centres
              WHERE source_record_id = 'centre-v1' AND coordinate_status = 'verified' AND freshness_at >= now()"""
        )
    ).one()
    assert spatial.nearby is True
    assert spatial.distance_m == 0
    db_session.rollback()


@pytest.mark.parametrize("field,value", [("seats", -1), ("mobility_radius_km", decimal.Decimal("-0.01"))])
def test_negative_capacity_and_radius_are_rejected(db_session, field, value):
    district = db_session.execute(text("SELECT code FROM districts LIMIT 1")).scalar_one()
    kwargs = {
        "district_code": district,
        "opportunity_type": "job",
        "title": "Invalid opportunity",
        "source_name": "test",
        "source_record_id": f"invalid-{field}",
        "verification_status": "verified",
        "synthetic": True,
    }
    if field == "seats":
        db_session.add(
            Programme(
                programme_type="training",
                title="Invalid programme",
                seats=value,
                source_name="test",
                source_record_id="invalid-seats",
                verification_status="verified",
                synthetic=True,
            )
        )
    else:
        kwargs[field] = value
        db_session.add(Opportunity(**kwargs))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_spatial_policy_requires_coarse_origin_and_eligible_coordinates():
    policy = (REPO / "services/core/tests/test_gate_phase2_spatial.py").read_text()
    assert "ST_DWithin" in policy or "st_dwithin" in policy.lower()
    assert "coordinate_status" in policy
    assert "stale" in policy and "missing" in policy and "rejected" in policy


def test_grounded_spatial_read_has_typed_outcomes_and_database_distance_only():
    source = (REPO / "services/core/api/recommendations.py").read_text(encoding="utf-8")
    for outcome in ("missing_origin", "missing_coordinates", "stale_coordinates", "no_results"):
        assert outcome in source
    assert "ST_DWithin" in source
    assert "ST_Distance" in source
    assert "haversine" not in source.lower()
    assert "MAX_MOBILITY_RADIUS_KM = 100" in source


def test_grounded_spatial_query_excludes_unfresh_or_rejected_coordinates():
    source = (REPO / "services/core/api/recommendations.py").read_text(encoding="utf-8")
    assert "freshness_at >= now()" in source
    assert "coordinate_status IN ('verified', 'synthetic')" in source
    assert "coordinate_status IN ('missing', 'rejected')" in source
