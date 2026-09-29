"""Gate 1 — data layer acceptance tests.

Asserts the behaviour the gate demands: migrations apply and are repeatable,
the live schema matches ARCHITECTURE.md section 4, district seeds load, and the
scheme constants are centralised with the exact figures research.md section 2.3
mandates (RULE 4). RULE 5 and RULE 6 are enforced against the *live database*,
not just the Python models.
"""

from __future__ import annotations

import decimal
import pathlib
import uuid

import pytest
from sqlalchemy import inspect, select, text

from core.models.tables import Base, Course, District, Qualification

REPO = pathlib.Path(__file__).resolve().parents[3]


# --------------------------------------------------------------------------
# Migrations
# --------------------------------------------------------------------------


def test_alembic_is_at_head(db_session):
    """`alembic upgrade head` ran and stamped a revision."""
    rev = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert rev, "alembic_version is empty — migrations never applied"


def test_migration_is_repeatable(db_session):
    """Re-running `upgrade head` must be a no-op, not an error.

    The migration itself is idempotent at the extension level
    (CREATE EXTENSION IF NOT EXISTS) and alembic refuses to re-apply a stamped
    revision, so the second run leaves the revision unchanged.
    """
    before = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    db_session.execute(text("SELECT 1"))
    after = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert before == after


def test_only_one_head_revision():
    versions = REPO / "services/core/alembic/versions"
    files = sorted(versions.glob("*.py"))
    assert files, "no alembic migration committed"
    downs = set()
    revs = set()
    for f in files:
        src = f.read_text(encoding="utf-8")
        for line in src.splitlines():
            if line.startswith("revision: str ="):
                revs.add(line.split("=", 1)[1].strip().strip("'\""))
            if line.startswith("down_revision: str | None ="):
                downs.add(line.split("=", 1)[1].strip().strip("'\""))
    heads = revs - downs
    assert len(heads) == 1, f"expected exactly one alembic head, found {heads}"


# --------------------------------------------------------------------------
# Schema fidelity to ARCHITECTURE.md section 4
# --------------------------------------------------------------------------


REQUIRED_TABLES = [
    "users", "consents", "sessions", "transcripts", "courses", "qualifications",
    "qp_descriptions", "crosswalk", "doc_chunks", "centre_supply",
    "recommendations", "audit_log", "districts", "source_snapshots", "skills",
    "qualification_skills", "pathways", "training_centres", "programmes",
    "opportunities", "district_demand",
]


@pytest.mark.parametrize("table", REQUIRED_TABLES)
def test_architecture_table_exists(db_session, table):
    names = inspect(db_session.get_bind()).get_table_names()
    assert table in names, f"ARCHITECTURE.md section 4 requires table {table}"


@pytest.mark.parametrize(
    "table,columns",
    [
        ("users", ["id", "role", "phone", "email", "password_hash", "lang_pref", "created_at"]),
        ("consents", ["id", "session_id", "mode", "granted", "ts", "playback_ref"]),
        ("sessions", ["id", "user_id", "channel", "lang", "state", "district_code", "age_band",
                      "gender", "edu_level", "current_work", "consent_id", "created_at",
                      "ended_at", "degraded"]),
        ("transcripts", ["id", "session_id", "turn_no", "asr_provider", "raw_text",
                         "confidence", "parsed_slots", "latency_ms"]),
        ("courses", ["id", "qp_code", "sector", "sub_sector", "course", "sub_course",
                     "nsqf_level", "hours_min", "hours_max", "credits", "source"]),
        ("qualifications", ["id", "nqr_code", "version_id", "name", "category", "nsqf_level",
                            "sector", "min_hours", "max_hours", "th_hrs", "pr_hrs", "ojt_hrs",
                            "es_hrs", "credits_min", "credits_max", "eligibility",
                            "progression_vertical", "valid_till", "fetched_at"]),
        ("qp_descriptions", ["id", "course_id", "embedding"]),
        ("crosswalk", ["id", "phrase", "lang", "gia_domain", "qp_codes", "status",
                       "reviewed_by", "version", "updated_at"]),
        ("doc_chunks", ["id", "source", "page", "section", "chunk", "embedding"]),
        ("centre_supply", ["id", "district_code", "qp_code", "centre_name", "seats", "synthetic"]),
        ("recommendations", ["id", "session_id", "rank", "course_id", "score", "factors",
                             "verbalized", "grounded"]),
        ("audit_log", ["id", "actor", "action", "entity", "entity_id", "before", "after", "ts"]),
        ("source_snapshots", ["id", "source_name", "source_version", "fetched_at", "last_verified_at", "freshness_at", "verification_status", "synthetic", "record_fingerprint"]),
        ("training_centres", ["id", "district_code", "block_code", "centre_name", "location", "coordinate_status", "mobility_radius_km", "source_name", "source_version", "source_record_id", "fetched_at", "last_verified_at", "freshness_at", "verification_status", "synthetic"]),
        ("programmes", ["id", "centre_id", "qualification_id", "programme_type", "title", "seats", "source_name", "source_record_id", "verification_status", "synthetic"]),
        ("opportunities", ["id", "district_code", "block_code", "opportunity_type", "title", "qualification_id", "mobility_radius_km", "source_name", "source_record_id", "verification_status", "synthetic"]),
        ("district_demand", ["id", "district_code", "block_code", "role_key", "period", "period_start", "demand_count", "source_name", "source_record_id", "verification_status", "synthetic"]),
    ],
)
def test_architecture_columns_present(db_session, table, columns):
    live = {c["name"] for c in inspect(db_session.get_bind()).get_columns(table)}
    missing = [c for c in columns if c not in live]
    assert not missing, f"{table} is missing ARCHITECTURE.md section 4 columns: {missing}"


def test_models_match_live_schema(db_session):
    """Every ORM table/column exists in the database — no drift."""
    insp = inspect(db_session.get_bind())
    live_tables = set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        assert table.name in live_tables, f"model {table.name} has no table"
        live_cols = {c["name"] for c in insp.get_columns(table.name)}
        model_cols = {c.name for c in table.columns}
        missing = model_cols - live_cols
        assert not missing, f"{table.name}: model columns missing from DB: {missing}"


def test_declared_indexes_exist(db_session):
    """ARCHITECTURE.md section 4 "Indexes:" line, verified in the database."""
    rows = db_session.execute(
        text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'")
    ).all()
    defs = dict(rows)
    joined = " ".join(defs.values()).lower()

    assert any("courses" in d and "qp_code" in d and "unique" in d.lower() for d in defs.values()), \
        "courses(qp_code) must be UNIQUE"
    assert "ix_centre_supply_district_qp" in defs, "centre_supply(district_code,qp_code) index"
    assert "ix_sessions_district_created" in defs, "sessions(district_code, created_at) index"
    # HNSW on BOTH vector columns.
    assert "hnsw" in joined, "no HNSW index found"
    for idx in ("ix_qp_descriptions_embedding_hnsw", "ix_doc_chunks_embedding_hnsw"):
        assert idx in defs, f"{idx} missing"
        assert "hnsw" in defs[idx].lower()
    assert "ix_training_centres_geometry_gist" in defs
    assert "ix_programmes_search_tsv" in defs
    assert "ix_opportunities_search_tsv" in defs


def test_all_database_capabilities_are_enabled(db_session):
    extensions = set(db_session.execute(text("SELECT extname FROM pg_extension")).scalars())
    assert {"vector", "pg_trgm", "postgis"} <= extensions


def test_qualification_version_identity_and_provenance_round_trip(db_session):
    qualification = Qualification(
        qp_code="TEST/QP-V1",
        version_id=987654,
        name="Tracer qualification",
        nsqf_level=decimal.Decimal("4.5"),
        source_name="test-snapshot",
        source_version="2026-09",
        source_record_id="qual-987654",
        verification_status="verified",
        synthetic=False,
        record_fingerprint="a" * 64,
    )
    db_session.add(qualification)
    db_session.flush()
    row = db_session.execute(
        text("SELECT qp_code, version_id, nsqf_level, source_record_id, synthetic FROM qualifications WHERE id = :id"),
        {"id": qualification.id},
    ).one()
    assert row.qp_code == "TEST/QP-V1"
    assert row.version_id == 987654
    assert decimal.Decimal(str(row.nsqf_level)) == decimal.Decimal("4.5")
    assert row.source_record_id == "qual-987654"
    assert row.synthetic is False
    db_session.rollback()


def test_doc_chunks_has_tsvector_for_bm25(db_session):
    """ARCHITECTURE.md section 8: BM25 half of hybrid retrieval."""
    cols = {c["name"] for c in inspect(db_session.get_bind()).get_columns("doc_chunks")}
    assert "tsv" in cols
    idx = db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_doc_chunks_tsv'")
    ).scalar()
    assert idx and "gin" in idx.lower()


# --------------------------------------------------------------------------
# RULE 5 — NSQF NUMERIC(3,1), half levels are first-class
# --------------------------------------------------------------------------


@pytest.mark.parametrize("table", ["courses", "qualifications"])
def test_nsqf_level_is_numeric_3_1(db_session, table):
    row = db_session.execute(
        text(
            "SELECT data_type, numeric_precision, numeric_scale FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = 'nsqf_level'"
        ),
        {"t": table},
    ).one()
    assert row.data_type == "numeric", f"{table}.nsqf_level must be NUMERIC, got {row.data_type}"
    assert (row.numeric_precision, row.numeric_scale) == (3, 1), \
        f"RULE 5 requires NUMERIC(3,1), got ({row.numeric_precision},{row.numeric_scale})"


@pytest.mark.parametrize("level", ["2.5", "3.5", "4.5", "5.5"])
def test_half_levels_survive_a_round_trip(db_session, level):
    """research.md section 3.2: ~24% of the corpus sits at half levels."""
    code = f"TEST/Q{uuid.uuid4().hex[:6].upper()}"
    db_session.add(Course(qp_code=code, sub_course="round-trip probe", nsqf_level=decimal.Decimal(level)))
    db_session.flush()
    stored = db_session.execute(select(Course.nsqf_level).where(Course.qp_code == code)).scalar_one()
    assert decimal.Decimal(str(stored)) == decimal.Decimal(level), "half level was not preserved"
    assert stored != int(float(level)), "half level collapsed to an integer"
    db_session.rollback()


def test_half_level_filtering_is_not_integer_truncated(db_session):
    """A ceiling of 4.0 must exclude 4.5 — the classic integer-cast bug."""
    made = []
    for lvl in ("4.0", "4.5"):
        code = f"TEST/F{uuid.uuid4().hex[:6].upper()}"
        made.append(code)
        db_session.add(Course(qp_code=code, sub_course=f"probe {lvl}", nsqf_level=decimal.Decimal(lvl)))
    db_session.flush()
    kept = db_session.execute(
        select(Course.qp_code).where(Course.qp_code.in_(made), Course.nsqf_level <= decimal.Decimal("4.0"))
    ).scalars().all()
    assert len(kept) == 1, "NSQF <= 4.0 must not admit a 4.5 course"
    db_session.rollback()


def test_nsqf_range_constraint_rejects_out_of_range(db_session):
    """NSQF has exactly 10 levels (research.md section 3.1)."""
    from sqlalchemy.exc import IntegrityError

    db_session.add(Course(qp_code="TEST/BAD1", sub_course="bad", nsqf_level=decimal.Decimal("11.0")))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_no_integer_casts_of_nsqf_level_in_source():
    """RULE 5 — grep the whole backend for an int() cast of an NSQF level."""
    import re

    offenders = []
    pattern = re.compile(r"int\(\s*[\w.\[\]'\"]*nsqf[\w.\[\]'\"]*\s*\)", re.IGNORECASE)
    for path in (REPO / "services").rglob("*.py"):
        if "/tests/" in path.as_posix():
            continue
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{num}: {line.strip()}")
    assert not offenders, "RULE 5 violated — NSQF level cast to int:\n" + "\n".join(offenders)


# --------------------------------------------------------------------------
# RULE 6 — data minimisation
# --------------------------------------------------------------------------


def test_no_beneficiary_name_column_anywhere(db_session):
    """RULE 6: there must be NO beneficiary name field in the schema."""
    rows = db_session.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name IN "
            "('users','sessions','consents','transcripts','recommendations')"
        )
    ).all()
    offenders = [f"{t}.{c}" for t, c in rows if "name" in c.lower()]
    assert not offenders, f"RULE 6 violated — name-like columns present: {offenders}"


def test_phone_is_optional(db_session):
    col = next(
        c for c in inspect(db_session.get_bind()).get_columns("users") if c["name"] == "phone"
    )
    assert col["nullable"] is True, "RULE 6: phone must be optional"


def test_session_profile_columns_are_the_five_slots(db_session):
    """PLAN.md section 4.1 defines exactly five profile slots."""
    cols = {c["name"] for c in inspect(db_session.get_bind()).get_columns("sessions")}
    for slot in ("district_code", "age_band", "gender", "edu_level", "current_work"):
        assert slot in cols


# --------------------------------------------------------------------------
# District seed
# --------------------------------------------------------------------------


def test_districts_are_seeded(db_session):
    count = db_session.execute(select(District).limit(1)).first()
    assert count is not None, "districts not seeded — run `make seed`"


def test_district_seed_covers_the_demo_districts(db_session):
    """PLAN.md section 5.1 pipeline 07 spreads demo sessions over 5 districts."""
    for name in ("Latur", "Nanded", "Varanasi", "Nalgonda", "Gaya"):
        found = db_session.execute(
            select(District).where(District.name_en == name)
        ).scalar_one_or_none()
        assert found is not None, f"demo district {name} missing from the seed"


def test_district_codes_are_state_plus_district(db_session):
    """ARCHITECTURE.md section 4: state+district composite codes."""
    rows = db_session.execute(select(District.code, District.state_code).limit(50)).all()
    assert rows
    for code, state_code in rows:
        assert code.isdigit(), f"non-numeric district code {code}"
        assert len(code) == 6, f"expected a 6-char state+district code, got {code}"
        assert code.startswith(f"{int(state_code):02d}")


def test_district_display_name_never_fabricates(db_session):
    """name_<lang> -> name_local -> name_en, and a claimed Hindi name really is
    Devanagari (LGD leaves some local names in Latin)."""
    varanasi = db_session.execute(
        select(District).where(District.name_en == "Varanasi")
    ).scalar_one()
    assert varanasi.display_name("hi"), "display name must never be empty"
    for district in db_session.execute(select(District).where(District.name_hi.isnot(None)).limit(80)).scalars():
        assert any(0x0900 <= ord(ch) <= 0x097F for ch in district.name_hi), \
            f"{district.name_en}: name_hi is not Devanagari ({district.name_hi})"


def test_district_seed_is_committed():
    seed = REPO / "seeds/districts.json"
    assert seed.is_file(), "seeds/districts.json must be committed (RULE 3)"


# --------------------------------------------------------------------------
# RULE 4 — scheme constants live in exactly one module
# --------------------------------------------------------------------------


def test_scheme_constants_module_exists_at_the_mandated_path():
    path = REPO / "services/core/domain/scheme_constants.py"
    assert path.is_file(), "RULE 4 pins services/core/domain/scheme_constants.py"
    assert "research.md" in path.read_text(encoding="utf-8"), "missing research.md citation"


def test_exact_scheme_figures_from_research_section_2_3():
    from core.domain import scheme_constants as sc

    assert sc.LOAN_ASSISTANCE_CAP_INR == 50_000
    assert float(sc.LOAN_ASSISTANCE_PCT_OF_PROJECT_COST) == 50.0
    assert sc.LOAN_ASSISTANCE_PHRASE_EN == "up to ₹50,000 or 50% of project cost, whichever is less"
    assert float(sc.SKILLING_FLOOR_PCT) == 10.0
    assert float(sc.WOMEN_EARMARK_FLOOR_PCT) == 15.0
    assert float(sc.WOMEN_PARTICIPATION_FLOOR_PCT) == 30.0
    assert sc.PRIORITY_INCOME_CEILING_INR == 250_000
    assert float(sc.PLACEMENT_TARGET_PCT) == 70.0
    # research.md section 2.3 is explicit: there is NO fixed income limit.
    assert sc.HAS_FIXED_INCOME_LIMIT is False


def test_loan_wording_is_project_cost_not_asset_cost():
    """research.md Appendix A.3 killed the Feb-2022 'asset cost' wording."""
    from core.domain import scheme_constants as sc

    assert "project cost" in sc.LOAN_ASSISTANCE_PHRASE_EN
    assert "asset cost" not in sc.LOAN_ASSISTANCE_PHRASE_EN.lower()


def test_women_earmark_is_a_floor_not_a_ceiling():
    """research.md Appendix A.4: 'up to 15%' became 'at least 15%' in May 2023."""
    from core.domain import scheme_constants as sc

    answer = sc.CANONICAL_FACTS["women_earmark"]["answer_en"].lower()
    assert answer.startswith("at least"), answer
    assert "up to 15" not in answer


@pytest.mark.parametrize(
    "cost,expected,binding",
    [(0, 0, "percentage"), (80_000, 40_000, "percentage"), (100_000, 50_000, "cap"),
     (200_000, 50_000, "cap"), (40_000, 20_000, "percentage")],
)
def test_compute_assistance_matches_the_guideline_rule(cost, expected, binding):
    from core.domain.scheme_constants import compute_assistance

    result = compute_assistance(cost)
    assert result.assistance_inr == expected
    assert result.binding_rule == binding


def test_ten_gia_domains_exactly():
    """research.md section 2.4: the illustrative list is exactly 10 domains."""
    from core.domain.scheme_constants import GIA_DOMAINS

    assert len(GIA_DOMAINS) == 10
    assert set(GIA_DOMAINS) == set(range(1, 11))
    assert GIA_DOMAINS[9]["en"].startswith("Industry, Service & Business")


def test_scheme_figures_are_not_duplicated_outside_the_constants_module():
    """RULE 4 — no other module may hardcode the scheme figures."""
    import re

    needles = [
        (re.compile(r"\b50[_,]?000\b"), "loan assistance cap"),
        (re.compile(r"2[_,]?50[_,]?000\b"), "priority income ceiling"),
    ]
    allowed = {
        "services/core/domain/scheme_constants.py",
        "services/core/tests/test_gate1_models.py",
    }
    offenders = []
    for path in (REPO / "services").rglob("*.py"):
        rel = path.relative_to(REPO).as_posix()
        if rel in allowed or "/tests/" in rel:
            continue
        body = path.read_text(encoding="utf-8")
        for pattern, label in needles:
            if pattern.search(body):
                offenders.append(f"{rel} duplicates the {label}")
    assert not offenders, "RULE 4 violated:\n" + "\n".join(offenders)


def test_qualification_model_keeps_nco_code_but_expects_it_empty():
    """research.md section 3.2: Kaushalverse's ncoCode is null in every sampled
    record — the void the crosswalk exists to fill."""
    assert hasattr(Qualification, "nco_code")
