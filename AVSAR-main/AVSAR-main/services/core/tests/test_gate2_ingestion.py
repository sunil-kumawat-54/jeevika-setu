"""Gate 2 — ingestion + seeds acceptance tests.

What this gate has to prove:

* pipelines 01-03 and 05-07 produce committed ``seeds/*.json`` snapshots;
* the snapshots are **idempotent** — loading twice converges;
* the ``synthetic`` flag survives seed -> database (and Gate 9 asserts it
  survives into the dashboard);
* a join report exists;
* **RULE 3** — the runtime never reaches a government portal.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import func, select, text

from core.models.tables import CentreSupply, Course, District, DocChunk, Qualification, Session

REPO = pathlib.Path(__file__).resolve().parents[3]
SEEDS = REPO / "seeds"

GOV_HOSTS = ("pmajay.dosje.gov.in", "kaushalverse.ncvet.gov.in", "nqr.gov.in")


def _seed(name: str) -> dict:
    path = SEEDS / name
    assert path.is_file(), f"seed {name} missing — run `make ingest`"
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Seeds are committed and well-formed
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["districts.json", "kaushalverse_qualifications.json", "pmajay_courses.json",
     "centre_supply.json", "doc_chunks.json", "join_report.json"],
)
def test_seed_file_is_committed(name):
    """RULE 3 — 'Those seeds MUST be committed to Git.'"""
    assert (SEEDS / name).is_file(), f"seeds/{name} not present"


@pytest.mark.parametrize(
    "name",
    ["districts.json", "kaushalverse_qualifications.json", "pmajay_courses.json",
     "centre_supply.json", "doc_chunks.json"],
)
def test_seed_has_an_honest_provenance_block(name):
    payload = _seed(name)
    prov = payload["provenance"]
    assert prov["pipeline"]
    assert prov["source_url"]
    assert prov["mode"] in {"live", "synthetic", "mixed"}
    assert prov["rows"] == len(payload["records"])
    if prov["synthetic"]:
        # A synthetic snapshot must say why and what it substituted.
        assert prov.get("failure_reason") or prov.get("fallback_note"), (
            f"{name} is synthetic but explains nothing"
        )


@pytest.mark.parametrize(
    "name",
    ["kaushalverse_qualifications.json", "pmajay_courses.json", "centre_supply.json",
     "doc_chunks.json", "districts.json"],
)
def test_synthetic_snapshots_flag_every_record(name):
    """No-fabrication policy: a synthetic snapshot marks records synthetic=true."""
    payload = _seed(name)
    if not payload["provenance"]["synthetic"]:
        return
    unflagged = [r for r in payload["records"] if not r.get("synthetic")]
    assert not unflagged, f"{name}: {len(unflagged)} synthetic records are not flagged"


def test_courses_seed_is_substantial():
    """Gate 2 wants >=2,000 course rows, OR a documented structurally
    equivalent fallback when the real source is unreachable."""
    payload = _seed("pmajay_courses.json")
    rows = payload["records"]
    prov = payload["provenance"]
    if len(rows) >= 2000:
        return
    assert prov["synthetic"], (
        f"only {len(rows)} courses and the snapshot claims to be live — "
        "a short live catalogue is a bug, not a fallback"
    )
    assert prov.get("fallback_note"), "short catalogue must carry a documented fallback note"
    assert len(rows) >= 1000, f"fallback catalogue is too small to be representative ({len(rows)})"
    report = REPO / "docs/ingest-report.md"
    assert report.is_file(), "the fallback must be documented in docs/ingest-report.md"


def test_course_rows_have_the_architecture_shape():
    rows = _seed("pmajay_courses.json")["records"]
    required = {"qp_code", "sector", "sub_sector", "course", "sub_course", "nsqf_level", "source"}
    for row in rows[:50]:
        assert required <= set(row), f"course row missing {required - set(row)}"


def test_qualification_seed_filters_to_qualifications_only():
    """PLAN.md §5.1 pipeline 02: drop Standalone NOS / Standalone MC."""
    rows = _seed("kaushalverse_qualifications.json")["records"]
    categories = {r.get("category") for r in rows}
    assert categories <= {"Qualification"}, f"unfiltered categories present: {categories}"


def test_nsqf_half_levels_survive_ingestion():
    """RULE 5 / research.md §3.2 — half levels are ~a quarter of the corpus."""
    rows = _seed("kaushalverse_qualifications.json")["records"]
    levelled = [r for r in rows if r.get("nsqf_level") is not None]
    assert levelled, "no qualification carries an NSQF level"
    half = [r for r in levelled if float(r["nsqf_level"]) % 1 != 0]
    assert half, "no half-level qualifications survived ingestion — integer truncation?"
    share = 100 * len(half) / len(levelled)
    assert 10 < share < 40, f"half-level share {share:.1f}% is implausible vs research.md's ~24%"


def test_join_report_exists_and_is_coherent():
    payload = _seed("join_report.json")
    report = payload["records"][0]
    for key in ("total_courses", "matched", "unmatched", "match_rate_pct", "strategies"):
        assert key in report, f"join report missing {key}"
    assert report["matched"] + report["unmatched"] == report["total_courses"]


def test_join_report_does_not_oversell_a_tautological_match():
    """If courses were derived from the register, the report must say the match
    rate proves nothing."""
    report = _seed("join_report.json")["records"][0]
    if report.get("courses_derived_from_register"):
        assert report.get("match_rate_is_tautological") is True
        text_report = (REPO / "docs/ingest-report.md").read_text(encoding="utf-8")
        assert "tautological" in text_report.lower()


def test_centre_supply_is_declared_synthetic():
    """PLAN.md §5.1 pipeline 05 — synthetic by design, labelled in the UI."""
    payload = _seed("centre_supply.json")
    assert payload["provenance"]["synthetic"] is True
    assert all(r["synthetic"] for r in payload["records"])


def test_doc_chunks_carry_section_paths_and_embeddings():
    """research.md §9.2 — section path must ride inside the chunk text."""
    rows = _seed("doc_chunks.json")["records"]
    assert rows, "no guideline chunks"
    for row in rows[:20]:
        assert len(row["embedding"]) == 768, "embedding is not 768-dim"
        assert row["chunk"].startswith("["), "chunk is missing its bracketed section path prefix"
        assert row["backend"] in {"e5", "hashing"}


def test_embedding_backend_is_consistent_within_the_corpus():
    """Mixing e5 and hashed vectors in one index makes cosine meaningless."""
    rows = _seed("doc_chunks.json")["records"]
    backends = {r["backend"] for r in rows}
    assert len(backends) == 1, f"doc_chunks mixes embedding backends: {backends}"


# --------------------------------------------------------------------------
# Seeds reached the database, flags intact
# --------------------------------------------------------------------------


def test_courses_loaded(db_session):
    count = db_session.execute(select(func.count()).select_from(Course)).scalar_one()
    assert count >= 1000, f"only {count} courses in the database — run `make seed`"


def test_qualifications_loaded(db_session):
    count = db_session.execute(select(func.count()).select_from(Qualification)).scalar_one()
    assert count >= 1000, f"only {count} qualifications in the database"


def test_districts_loaded(db_session):
    count = db_session.execute(select(func.count()).select_from(District)).scalar_one()
    assert count >= 700, f"only {count} districts in the database"


def test_doc_chunks_loaded(db_session):
    count = db_session.execute(select(func.count()).select_from(DocChunk)).scalar_one()
    assert count >= 100, f"only {count} doc chunks in the database"


def test_synthetic_flag_survives_into_the_database(db_session):
    """Policy: 'preserve that synthetic status through ingestion/database/UI'."""
    seeded = _seed("centre_supply.json")["records"]
    if not seeded:
        pytest.skip("no centre_supply seed")
    total = db_session.execute(select(func.count()).select_from(CentreSupply)).scalar_one()
    synthetic = db_session.execute(
        select(func.count()).select_from(CentreSupply).where(CentreSupply.synthetic.is_(True))
    ).scalar_one()
    assert total > 0 and synthetic == total, "centre_supply lost its synthetic flag on load"


def test_real_qualifications_are_not_marked_synthetic(db_session):
    """The register was fetched live — mislabelling real data as synthetic is
    as dishonest as the reverse."""
    if not _seed("kaushalverse_qualifications.json")["provenance"]["synthetic"]:
        wrongly = db_session.execute(
            select(func.count()).select_from(Qualification).where(Qualification.synthetic.is_(True))
        ).scalar_one()
        assert wrongly == 0, f"{wrongly} live qualifications are flagged synthetic"


def test_nco_code_gap_is_real(db_session):
    """research.md §3.3 — Kaushalverse publishes no NCO codes. This is the gap
    the crosswalk fills, so it must be visible in the data, not just asserted."""
    populated = db_session.execute(
        select(func.count()).select_from(Qualification).where(Qualification.nco_code.isnot(None))
    ).scalar_one()
    total = db_session.execute(select(func.count()).select_from(Qualification)).scalar_one()
    assert total > 0
    assert populated == 0, (
        f"{populated}/{total} qualifications now carry an NCO code — research.md §3.3 and "
        "docs/ingest-report.md need updating if the register has started publishing them"
    )


def test_demo_sessions_seeded_across_five_districts(db_session):
    """PLAN.md §5.1 pipeline 07 — 25 sessions over 5 districts."""
    total = db_session.execute(
        select(func.count()).select_from(Session).where(Session.synthetic.is_(True))
    ).scalar_one()
    assert total >= 25, f"only {total} synthetic sessions"
    districts = db_session.execute(
        select(func.count(func.distinct(Session.district_code))).where(Session.synthetic.is_(True))
    ).scalar_one()
    assert districts >= 5, f"synthetic sessions span only {districts} districts"


def test_consent_precedes_profile_slots(db_session):
    """RULE 6 / ARCHITECTURE §9 — no profile slot may exist without consent."""
    offenders = db_session.execute(
        text(
            "SELECT count(*) FROM sessions WHERE consent_id IS NULL AND ("
            "age_band IS NOT NULL OR gender IS NOT NULL OR edu_level IS NOT NULL "
            "OR current_work IS NOT NULL)"
        )
    ).scalar_one()
    assert offenders == 0, f"{offenders} sessions hold profile slots without a consent record"


def test_seed_load_is_idempotent(db_session):
    """Re-running the loaders must not duplicate rows."""
    from pipelines.load_to_db import load_all, table_counts

    before = table_counts(db_session)
    load_all(db_session)
    after = table_counts(db_session)
    db_session.rollback()
    assert before == after, f"loading twice changed row counts: {before} -> {after}"


# --------------------------------------------------------------------------
# RULE 3 — government portals are NOT runtime dependencies
# --------------------------------------------------------------------------


def test_runtime_never_references_a_government_portal():
    """RULE 3: 'Runtime MUST NOT call pmajay.dosje.gov.in / kaushalverse…
    except through an optional explicitly labeled live check endpoint.'"""
    http_markers = ("httpx.", "requests.", "aiohttp.", "urllib.request", "urlopen")
    offenders: list[str] = []
    for path in (REPO / "services").rglob("*.py"):
        rel = path.relative_to(REPO).as_posix()
        if "/tests/" in rel:
            continue
        body = path.read_text(encoding="utf-8")
        named = [h for h in GOV_HOSTS if h in body]
        if not named:
            continue
        # The optional, explicitly labelled "live check" endpoint is the one
        # place ARCHITECTURE.md §2 permits to reach a portal at runtime.
        if "live_check" in rel:
            continue
        # A hostname inside a citation string or docstring is not a call. It is
        # only a RULE 3 violation if the same module can also make one — e.g.
        # scheme_constants.py cites the guidelines PDF URL because that citation
        # is spoken to the beneficiary, but it imports no HTTP client.
        if any(marker in body for marker in http_markers):
            offenders.append(f"{rel} can make HTTP calls and names {named}")
    assert not offenders, "RULE 3 violated:\n" + "\n".join(offenders)


def test_runtime_settings_cannot_name_a_government_portal():
    """Stronger form of RULE 3: no runtime Settings field carries a government
    source, so nothing can even be *configured* to call one."""
    from core.config import Settings

    offenders = [
        f"{name}={field.default}"
        for name, field in Settings.model_fields.items()
        for host in GOV_HOSTS
        if host in str(field.default)
    ]
    assert not offenders, f"runtime settings name a government portal: {offenders}"


def test_runtime_does_not_import_the_pipelines_package():
    """services/core must not pull ingestion code into the request path."""
    offenders = []
    for path in (REPO / "services").rglob("*.py"):
        rel = path.relative_to(REPO).as_posix()
        if "/tests/" in rel:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import pipelines", "from pipelines")):
                offenders.append(f"{rel}: {stripped}")
    assert not offenders, "runtime imports ingestion code:\n" + "\n".join(offenders)


def test_ingest_report_documents_every_deviation():
    report = REPO / "docs/ingest-report.md"
    assert report.is_file(), "docs/ingest-report.md missing"
    body = report.read_text(encoding="utf-8")
    for heading in ("Expected:", "Actual:", "Fallback:", "Impact:", "How to switch to the real source:"):
        assert heading in body, f"ingest report never states '{heading}'"


def test_pipelines_respect_one_request_per_second():
    """RULE 3 / TECH_STACK §2.3 politeness."""
    common = (REPO / "pipelines/common.py").read_text(encoding="utf-8")
    assert "class RateLimiter" in common
    env_example = (REPO / ".env.example").read_text(encoding="utf-8")
    assert "INGEST_QPS=1" in env_example
    for name in ("00_fetch_districts.py", "01_fetch_pmajay_courses.py", "02_fetch_kaushalverse.py"):
        body = (REPO / "pipelines" / name).read_text(encoding="utf-8")
        assert "RateLimiter" in body and "limiter.wait()" in body, f"{name} does not throttle"
