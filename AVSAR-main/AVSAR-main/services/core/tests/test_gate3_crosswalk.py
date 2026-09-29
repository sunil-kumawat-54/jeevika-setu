"""Gate 3 — crosswalk engine acceptance tests.

Requirements this gate must prove:

* ``data/crosswalk/*.yaml`` plus a loader, a schema and a validator exist;
* **malformed YAML is rejected**, not skipped;
* **>=150 crosswalk entries** are authored;
* the domains/occupations research.md §2.4 defines are covered;
* QP descriptions are embedded with multilingual-e5 **on CPU** and stored in
  ``qp_descriptions``;
* crosswalk queries work.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import func, select, text

from core.domain.crosswalk_schema import (
    CrosswalkValidationError,
    load_dir,
    load_file,
    summarise,
)
from core.models.tables import Course, Crosswalk, QpDescription

REPO = pathlib.Path(__file__).resolve().parents[3]
CROSSWALK_DIR = REPO / "data" / "crosswalk"

#: The concepts the build brief names as a minimum. research.md §2.4 is the
#: authoritative domain definition, asserted separately below.
REQUIRED_CONCEPTS = {
    "tailoring", "beauty", "electrician", "plumbing", "tractor_operator",
    "beekeeper", "poultry", "dairy", "goatery", "food_processing",
    "handicrafts", "mobile_repair", "healthcare_attendant", "data_entry", "retail",
}


@pytest.fixture(scope="module")
def rows():
    return load_dir(CROSSWALK_DIR)


# --------------------------------------------------------------------------
# Authoring volume and coverage
# --------------------------------------------------------------------------


def test_crosswalk_yaml_files_exist():
    files = sorted(CROSSWALK_DIR.glob("*.yaml"))
    assert files, "data/crosswalk/*.yaml is empty — the crosswalk is the moat artifact"


def test_at_least_150_entries(rows):
    """PLAN.md §5.1 pipeline 04: 'v0 ~= 150 entries'; the gate demands >=150."""
    assert len(rows) >= 150, f"only {len(rows)} crosswalk rows authored"


def test_all_ten_gia_domains_are_covered(rows):
    """research.md §2.4 is the authoritative domain definition — exactly 10."""
    covered = {r.gia_domain for r in rows}
    missing = set(range(1, 11)) - covered
    assert not missing, f"GIA domains not covered by any crosswalk entry: {sorted(missing)}"


def test_required_concepts_present(rows):
    concepts = {r.concept for r in rows}
    missing = REQUIRED_CONCEPTS - concepts
    assert not missing, f"required concepts missing from the crosswalk: {sorted(missing)}"


def test_every_concept_covers_all_four_languages(rows):
    """PLAN.md §7 handles hi/mr/te and ARCHITECTURE.md §1 adds en."""
    by_concept: dict[str, set[str]] = {}
    for row in rows:
        by_concept.setdefault(row.concept, set()).add(row.lang)
    incomplete = {c: sorted(langs) for c, langs in by_concept.items() if len(langs) < 4}
    assert not incomplete, f"concepts missing languages: {incomplete}"


def test_entries_are_peer_reviewed(rows):
    """PLAN.md §5.2: 'each entry reviewed by a second member'."""
    unreviewed = {r.concept for r in rows if r.status != "reviewed"}
    assert not unreviewed, f"concepts still status=auto: {sorted(unreviewed)}"


# --------------------------------------------------------------------------
# Validation — malformed YAML MUST be rejected
# --------------------------------------------------------------------------


BAD_DOCS = {
    "not_yaml_at_all": "entries: [unclosed\n  - bracket",
    "top_level_not_mapping": "- just\n- a\n- list\n",
    "missing_entries_key": "version: 1\nitems: []\n",
    "entries_not_a_list": "entries: {}\n",
    "entry_missing_keys": "entries:\n  - concept: tailoring\n",
    "unknown_key": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n    bogus: 1\n"
    ),
    "domain_out_of_range": (
        "entries:\n  - concept: tailoring\n    gia_domain: 11\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    ),
    "domain_zero": (
        "entries:\n  - concept: tailoring\n    gia_domain: 0\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    ),
    "bad_qp_code": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['not-a-qp-code']\n    phrases: {en: ['tailoring']}\n"
    ),
    "duplicate_qp_codes": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866', 'AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    ),
    "empty_qp_codes_without_gap_reason": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: []\n    phrases: {en: ['tailoring']}\n"
    ),
    "unsupported_language": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {zz: ['tailoring']}\n"
    ),
    "empty_phrase_list": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: []}\n"
    ),
    "bad_concept_name": (
        "entries:\n  - concept: 'Tailoring Work!'\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    ),
    "bad_status": (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n    status: maybe\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    ),
    "empty_file": "",
}


@pytest.mark.parametrize("name,body", sorted(BAD_DOCS.items()))
def test_malformed_yaml_is_rejected(tmp_path, name, body):
    """Gate 3: 'Malformed YAML MUST be rejected.'"""
    path = tmp_path / f"{name}.yaml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(CrosswalkValidationError):
        load_file(path)


def test_valid_yaml_loads(tmp_path):
    path = tmp_path / "good.yaml"
    path.write_text(
        "version: 1\n"
        "entries:\n"
        "  - concept: tailoring\n"
        "    gia_domain: 9\n"
        "    status: reviewed\n"
        "    qp_codes: ['AP/Q01866', 'AP/Q01868']\n"
        "    phrases:\n"
        "      hi: ['सिलाई']\n"
        "      en: ['tailoring', 'sewing']\n",
        encoding="utf-8",
    )
    doc = load_file(path)
    assert len(doc.rows) == 3
    assert {r.lang for r in doc.rows} == {"hi", "en"}
    assert doc.rows[0].qp_codes == ("AP/Q01866", "AP/Q01868")


def test_duplicate_phrase_across_files_is_rejected(tmp_path):
    """crosswalk(phrase, lang) is UNIQUE in the schema."""
    body = (
        "entries:\n  - concept: tailoring\n    gia_domain: 9\n"
        "    qp_codes: ['AP/Q01866']\n    phrases: {en: ['tailoring']}\n"
    )
    (tmp_path / "a.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(body.replace("tailoring\n    gia", "sewing\n    gia"), encoding="utf-8")
    with pytest.raises(CrosswalkValidationError, match="duplicate phrase"):
        load_dir(tmp_path)


def test_a_declared_gap_needs_a_reason(tmp_path):
    """Empty qp_codes is allowed ONLY as an explicit, explained gap."""
    good = tmp_path / "gap.yaml"
    good.write_text(
        "entries:\n  - concept: poultry\n    gia_domain: 4\n    qp_codes: []\n"
        "    gap_reason: 'No poultry qualification exists in the ingested register snapshot.'\n"
        "    phrases: {en: ['poultry farming']}\n",
        encoding="utf-8",
    )
    doc = load_file(good)
    assert doc.rows[0].is_gap is True
    assert doc.rows[0].gap_reason


def test_the_real_gap_is_declared_and_explained(rows):
    """poultry has no QP anywhere in the register; the entry must say so rather
    than silently mapping to a near-miss trade."""
    gaps = {r.concept: r.gap_reason for r in rows if r.is_gap}
    assert "poultry" in gaps, "poultry must be present, as a declared gap"
    assert "docs/ingest-report.md" in (gaps["poultry"] or ""), "gap must cite the ingest report"


# --------------------------------------------------------------------------
# Referential integrity against the real catalogue
# --------------------------------------------------------------------------


def test_every_qp_code_exists_in_the_catalogue(db_session, rows):
    """A crosswalk entry pointing at a non-existent QP is an invented fact."""
    referenced = {code for r in rows for code in r.qp_codes}
    known = {code for (code,) in db_session.execute(select(Course.qp_code))}
    missing = sorted(referenced - known)
    assert not missing, f"crosswalk references QP codes absent from courses: {missing}"


def test_crosswalk_rows_loaded_into_the_database(db_session):
    count = db_session.execute(select(func.count()).select_from(Crosswalk)).scalar_one()
    assert count >= 150, f"only {count} crosswalk rows in the database — run `make seed`"


def test_gia_domain_check_constraint_is_enforced(db_session):
    from sqlalchemy.exc import IntegrityError

    db_session.add(
        Crosswalk(phrase="__probe__", lang="en", gia_domain=99, concept="probe", qp_codes=["X/Q1"])
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


# --------------------------------------------------------------------------
# Embeddings — multilingual-e5, on CPU
# --------------------------------------------------------------------------


def test_embedding_runs_on_cpu_and_is_768_dim():
    """Gate 3: 'Embedding job MUST run on CPU.'"""
    from core.rag.embedder import get_embedder

    embedder = get_embedder()
    vector = embedder.encode_query("सिलाई का काम")
    assert len(vector) == 768
    assert embedder.name in {"e5", "hashing"}
    if embedder.name == "e5":
        device = str(next(embedder._model.parameters()).device)
        assert device == "cpu", f"multilingual-e5 is on {device}, not CPU"


def test_hashing_fallback_is_deterministic():
    """The offline fallback must give identical vectors across instances."""
    from core.rag.embedder import HashingEmbedder

    a = HashingEmbedder().encode_query("मुर्गी पालन")
    b = HashingEmbedder().encode_query("मुर्गी पालन")
    assert a == b
    assert abs(sum(v * v for v in a) - 1.0) < 1e-9, "vector is not L2-normalised"


def test_qp_descriptions_are_embedded_and_stored(db_session):
    count = db_session.execute(select(func.count()).select_from(QpDescription)).scalar_one()
    courses = db_session.execute(select(func.count()).select_from(Course)).scalar_one()
    assert count >= courses * 0.95, f"only {count} QP embeddings for {courses} courses"


def test_qp_description_vectors_have_the_right_dimension(db_session):
    dim = db_session.execute(
        text("SELECT vector_dims(embedding) FROM qp_descriptions LIMIT 1")
    ).scalar()
    assert dim == 768


def test_embedding_backend_is_uniform(db_session):
    backends = [
        b for (b,) in db_session.execute(select(QpDescription.backend).distinct())
    ]
    assert len(backends) == 1, f"qp_descriptions mixes vector spaces: {backends}"


def test_assert_compatible_refuses_to_mix_vector_spaces():
    from core.rag.embedder import assert_compatible

    assert_compatible("e5", "e5")
    with pytest.raises(RuntimeError, match="backend mismatch"):
        assert_compatible("e5", "hashing")


# --------------------------------------------------------------------------
# Crosswalk queries actually work
# --------------------------------------------------------------------------


def test_exact_phrase_lookup_returns_qp_codes(db_session):
    row = db_session.execute(
        select(Crosswalk).where(Crosswalk.phrase == "सिलाई", Crosswalk.lang == "hi")
    ).scalar_one_or_none()
    assert row is not None, "the demo's flagship phrase is missing"
    assert row.concept == "tailoring"
    assert row.qp_codes, "crosswalk row carries no QP codes"


def test_lookup_by_concept_spans_languages(db_session):
    langs = db_session.execute(
        select(Crosswalk.lang).where(Crosswalk.concept == "tailoring").distinct()
    ).scalars().all()
    assert set(langs) == {"hi", "mr", "te", "en"}


def test_trigram_fuzzy_phrase_lookup_works(db_session):
    """The pg_trgm index backs near-miss matching of a spoken phrase."""
    hit = db_session.execute(
        text(
            "SELECT concept FROM crosswalk WHERE lang = 'hi' "
            "ORDER BY phrase <-> 'सिलाई का कम' LIMIT 1"
        )
    ).scalar()
    assert hit == "tailoring", f"fuzzy lookup returned {hit}"


@pytest.mark.parametrize(
    "query,expected_concept",
    [
        ("मैं सिलाई का काम सीखना चाहती हूँ", "tailoring"),
        ("मला शिवणकाम शिकायचे आहे", "tailoring"),
        ("బ్యూటీ పార్లర్ కోర్సు చేయాలి", "beauty"),
        ("बिजली का काम सीखना है", "electrician"),
        ("I want to repair mobile phones", "mobile_repair"),
    ],
)
def test_semantic_recall_finds_the_right_trade(db_session, query, expected_concept):
    """Candidate set C2 (PLAN.md §6 STEP 2) must retrieve the right QPs from a
    colloquial utterance in any of the four languages.

    The QP description index carries the curated multilingual aliases, which is
    what makes hi/mr/te queries land on the correct English-named QP.
    """
    from core.domain.crosswalk_schema import load_dir as _load
    from core.rag.embedder import get_embedder

    vector = get_embedder().encode_query(query)
    codes = db_session.execute(
        text(
            "SELECT c.qp_code FROM qp_descriptions d JOIN courses c ON c.id = d.course_id "
            "ORDER BY d.embedding <=> CAST(:v AS vector) LIMIT 5"
        ),
        {"v": str(vector)},
    ).scalars().all()

    expected_codes = {
        code
        for row in _load(CROSSWALK_DIR)
        if row.concept == expected_concept
        for code in row.qp_codes
    }
    overlap = expected_codes & set(codes)
    assert overlap, (
        f"semantic recall for {query!r} returned {codes}, none of which belong to "
        f"concept {expected_concept} ({sorted(expected_codes)})"
    )


def test_summary_reports_coverage(rows):
    stats = summarise(rows)
    assert stats["rows"] == len(rows)
    assert stats["concepts"] >= 15
    assert stats["qp_codes_referenced"] >= 40


def test_crosswalk_method_doc_exists():
    """PLAN.md §5.2 requires docs/crosswalk-method.md for the Research slide."""
    doc = REPO / "docs" / "crosswalk-method.md"
    assert doc.is_file()
    body = doc.read_text(encoding="utf-8")
    for needle in ("embed", "review", "NCO"):
        assert needle.lower() in body.lower(), f"crosswalk-method.md never mentions {needle}"
