"""canonical knowledge, provenance, opportunities, and privacy-safe spatial facts

Revision ID: 0003_canonical_spatial
Revises: 0002_doc_chunk_identity
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

revision: str = "0003_canonical_spatial"
down_revision: str | None = "0002_doc_chunk_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Geography(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "geography(POINT,4326)"


def _enum(name: str, values: str) -> None:
    op.execute(
        f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({values}); "
        f"EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )


def _provenance_columns() -> list[sa.Column]:
    return [
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("source_version", sa.String(120), nullable=True),
        sa.Column("source_record_id", sa.String(160), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("record_fingerprint", sa.String(64), nullable=True),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    _enum("verification_status", "'unverified', 'verified', 'rejected'")
    _enum("coordinate_status", "'verified', 'synthetic', 'missing', 'stale', 'rejected'")
    _enum("programme_type", "'training', 'rpl', 'workshop'")
    _enum("opportunity_type", "'training', 'workshop', 'job', 'self_employment'")
    _enum("demand_period", "'monthly', 'quarterly', 'annual'")

    op.add_column("qualifications", sa.Column("source_name", sa.String(120), nullable=True))
    op.add_column("qualifications", sa.Column("source_version", sa.String(120), nullable=True))
    op.add_column("qualifications", sa.Column("source_record_id", sa.String(160), nullable=True))
    op.add_column("qualifications", sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("qualifications", sa.Column("freshness_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "qualifications",
        sa.Column("verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=True),
    )
    op.add_column("qualifications", sa.Column("verification_note", sa.Text(), nullable=True))
    op.add_column("qualifications", sa.Column("record_fingerprint", sa.String(64), nullable=True))
    op.execute("UPDATE qualifications SET verification_status = 'unverified' WHERE verification_status IS NULL")
    op.alter_column("qualifications", "verification_status", nullable=False, server_default="unverified")
    op.create_unique_constraint("uq_qualifications_qp_version", "qualifications", ["qp_code", "version_id"])

    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("source_version", sa.String(120), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=False, server_default="unverified"),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("record_fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint("source_name", "source_version", name="uq_source_snapshots_identity"),
    )
    op.create_index("ix_source_snapshots_source", "source_snapshots", ["source_name", "source_version"])

    op.create_table(
        "skills",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("skill_key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_snapshot_id", sa.BigInteger(), sa.ForeignKey("source_snapshots.id", ondelete="SET NULL")),
        sa.Column("source_record_id", sa.String(160), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("skill_key", name="uq_skills_key"),
    )
    op.create_index("ix_skills_name", "skills", ["name"])

    op.create_table(
        "qualification_skills",
        sa.Column("qualification_id", sa.BigInteger(), sa.ForeignKey("qualifications.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skill_id", sa.BigInteger(), sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_snapshot_id", sa.BigInteger(), sa.ForeignKey("source_snapshots.id", ondelete="SET NULL")),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("qualification_id", "skill_id", name="uq_qualification_skills_pair"),
    )

    op.create_table(
        "pathways",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("qualification_id", sa.BigInteger(), sa.ForeignKey("qualifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pathway_type", postgresql.ENUM(name="programme_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=True),
        sa.Column("source_snapshot_id", sa.BigInteger(), sa.ForeignKey("source_snapshots.id", ondelete="SET NULL")),
        sa.Column("source_record_id", sa.String(160), nullable=False),
        sa.Column("verification_status", postgresql.ENUM(name="verification_status", create_type=False), nullable=False, server_default="unverified"),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("duration_hours IS NULL OR duration_hours >= 0", name="ck_pathways_duration_nonnegative"),
        sa.UniqueConstraint("qualification_id", "pathway_type", "source_record_id", name="uq_pathways_identity"),
    )

    op.create_table(
        "training_centres",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("district_code", sa.String(8), sa.ForeignKey("districts.code", ondelete="CASCADE"), nullable=False),
        sa.Column("block_code", sa.String(32), nullable=True),
        sa.Column("centre_name", sa.String(240), nullable=False),
        sa.Column("location", Geography(), nullable=True),
        sa.Column("coordinate_status", postgresql.ENUM(name="coordinate_status", create_type=False), nullable=False, server_default="missing"),
        sa.Column("mobility_radius_km", sa.Numeric(6, 2), nullable=True),
        *_provenance_columns(),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_name", "source_record_id", name="uq_training_centres_source_identity"),
        sa.CheckConstraint("mobility_radius_km IS NULL OR mobility_radius_km >= 0", name="ck_centres_radius_nonnegative"),
    )
    op.create_index("ix_training_centres_district", "training_centres", ["district_code"])
    op.execute("CREATE INDEX ix_training_centres_geometry_gist ON training_centres USING gist (location)")

    op.create_table(
        "programmes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("centre_id", sa.BigInteger(), sa.ForeignKey("training_centres.id", ondelete="SET NULL"), nullable=True),
        sa.Column("qualification_id", sa.BigInteger(), sa.ForeignKey("qualifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("programme_type", postgresql.ENUM(name="programme_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("seats", sa.Integer(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        *_provenance_columns(),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_name", "source_record_id", name="uq_programmes_source_identity"),
        sa.CheckConstraint("seats IS NULL OR seats >= 0", name="ck_programmes_seats_nonnegative"),
    )
    op.execute("ALTER TABLE programmes ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', title)) STORED")
    op.execute("CREATE INDEX ix_programmes_search_tsv ON programmes USING gin (search_tsv)")

    op.create_table(
        "opportunities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("district_code", sa.String(8), sa.ForeignKey("districts.code", ondelete="CASCADE"), nullable=False),
        sa.Column("block_code", sa.String(32), nullable=True),
        sa.Column("opportunity_type", postgresql.ENUM(name="opportunity_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("qualification_id", sa.BigInteger(), sa.ForeignKey("qualifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mobility_radius_km", sa.Numeric(6, 2), nullable=True),
        *_provenance_columns(),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.UniqueConstraint("source_name", "source_record_id", name="uq_opportunities_source_identity"),
        sa.CheckConstraint("mobility_radius_km IS NULL OR mobility_radius_km >= 0", name="ck_opportunities_radius_nonnegative"),
    )
    op.execute("ALTER TABLE opportunities ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', title)) STORED")
    op.execute("CREATE INDEX ix_opportunities_search_tsv ON opportunities USING gin (search_tsv)")

    op.create_table(
        "district_demand",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("district_code", sa.String(8), sa.ForeignKey("districts.code", ondelete="CASCADE"), nullable=False),
        sa.Column("block_code", sa.String(32), nullable=True),
        sa.Column("role_key", sa.String(120), nullable=False),
        sa.Column("period", postgresql.ENUM(name="demand_period", create_type=False), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("demand_count", sa.Integer(), nullable=False),
        *_provenance_columns(),
        sa.UniqueConstraint("district_code", "block_code", "role_key", "period", "period_start", name="uq_district_demand_identity"),
        sa.CheckConstraint("demand_count >= 0", name="ck_district_demand_nonnegative"),
    )
    op.create_index("ix_district_demand_lookup", "district_demand", ["district_code", "block_code", "role_key"])


def downgrade() -> None:
    for table in ("district_demand", "opportunities", "programmes", "training_centres", "pathways", "qualification_skills", "skills", "source_snapshots"):
        op.drop_table(table)
    op.drop_constraint("uq_qualifications_qp_version", "qualifications", type_="unique")
    for column in (
        "record_fingerprint", "verification_note", "verification_status", "freshness_at",
        "last_verified_at", "source_record_id", "source_version", "source_name",
    ):
        op.drop_column("qualifications", column)
    for name in ("demand_period", "opportunity_type", "programme_type", "coordinate_status", "verification_status"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
    op.execute("DROP EXTENSION IF EXISTS postgis")
