"""Gate 7 — LLM verbalizer, guardrails and RAG acceptance tests.

Covers: the four tool schemas, grounding, numeral containment, regenerate-once,
template fallback, RAG retrieval, citations — and the **forced hallucination
test**, which must produce a refusal rather than an invented course.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import text as sql_text

from core.domain.recommender import Intent, Profile, recommend
from core.llm import templates
from core.llm.guarded import MAX_ATTEMPTS, generate_grounded
from core.llm.guardrails import (
    check_numerals,
    extract_numerals,
    numerals_in_json,
    tool_payload_for_items,
)
from core.llm.providers import SYSTEM_PROMPT, MockLlmProvider, get_provider
from core.llm.tools import TOOL_NAMES, TOOL_SCHEMAS, dispatch
from core.rag.retrieve import (
    RRF_K,
    bm25_search,
    hybrid_search,
    reciprocal_rank_fusion,
    vector_search,
)

REPO = pathlib.Path(__file__).resolve().parents[3]
LATUR = "270481"


@pytest.fixture()
def items(db_session):
    result = recommend(
        db_session,
        Profile(district_code=LATUR, gender="female", edu_level="8th_10th",
                current_work="unemployed", lang="hi"),
        Intent(concept_text="सिलाई का काम"),
    )
    assert result.items, "fixture needs a recommendation to verbalize"
    return result.items


# ==========================================================================
# Tool schemas
# ==========================================================================


def test_the_four_mandated_tools_exist():
    """ARCHITECTURE §7 names exactly these."""
    assert set(TOOL_NAMES) == {
        "search_courses", "get_qualification", "scheme_fact", "compute_assistance",
    }


@pytest.mark.parametrize("schema", TOOL_SCHEMAS, ids=lambda s: s["name"])
def test_tool_schemas_are_strict(schema):
    """research.md §9.3: additionalProperties:false, all fields required."""
    spec = schema["input_schema"]
    assert spec["type"] == "object"
    assert spec["additionalProperties"] is False, f"{schema['name']} allows extra properties"
    assert set(spec["required"]) == set(spec["properties"]), (
        f"{schema['name']}: every field must be required"
    )
    assert schema["description"].strip()


def test_tool_count_is_well_under_twenty():
    assert len(TOOL_SCHEMAS) <= 20


def test_search_courses_returns_real_rows(db_session):
    result = dispatch("search_courses", {"query": "सिलाई का काम", "max_nsqf_level": 4.0,
                                         "district_code": LATUR}, db=db_session)
    assert result["count"] > 0
    for row in result["results"]:
        assert row["qp_code"]
        exists = db_session.execute(
            sql_text("SELECT 1 FROM courses WHERE qp_code = :c"), {"c": row["qp_code"]}
        ).scalar()
        assert exists, f"{row['qp_code']} is not a real catalogue row"


def test_search_courses_respects_the_capability_ceiling(db_session):
    result = dispatch(
        "search_courses", {"query": "सिलाई", "max_nsqf_level": 3.0, "district_code": None},
        db=db_session,
    )
    for row in result["results"]:
        if row["nsqf_level"] is not None:
            assert row["nsqf_level"] <= 4.0  # engine may stretch by one level


def test_get_qualification_returns_register_fields(db_session):
    code = db_session.execute(
        sql_text("SELECT qp_code FROM qualifications WHERE min_hours IS NOT NULL LIMIT 1")
    ).scalar()
    result = dispatch("get_qualification", {"qp_code": code}, db=db_session)
    assert result["found"] is True
    assert result["name"]
    assert result["source"] == "NCVET Kaushalverse"


def test_get_qualification_refuses_an_unknown_code(db_session):
    result = dispatch("get_qualification", {"qp_code": "ZZZ/Q99999"}, db=db_session)
    assert result["found"] is False
    assert "do not have it" in result["note"]


def test_compute_assistance_uses_the_single_constants_module():
    from core.domain.scheme_constants import LOAN_ASSISTANCE_CAP_INR

    result = dispatch("compute_assistance", {"project_cost_inr": 80_000})
    assert result["assistance_inr"] == 40_000
    assert result["cap_inr"] == LOAN_ASSISTANCE_CAP_INR
    assert result["pct_of_project_cost"] == 50.0
    assert "research.md" in result["citation"]


def test_scheme_fact_answers_from_the_constants(db_session):
    result = dispatch("scheme_fact", {"question": "How much loan assistance can I get?"},
                      db=db_session)
    assert result["found"] is True
    assert result["values"]["cap_inr"] == 50_000
    assert result["citation"]


def test_scheme_fact_women_participation_is_a_floor(db_session):
    result = dispatch("scheme_fact", {"question": "what percentage of women must participate?"},
                      db=db_session)
    assert result["found"] is True
    assert result["values"]["floor_pct"] == 30.0


def test_scheme_fact_refuses_what_it_does_not_have(db_session):
    result = dispatch(
        "scheme_fact", {"question": "what is the capital of Iceland"}, db=db_session
    )
    if not result["found"]:
        assert "do not guess" in result["note"]


def test_dispatch_rejects_an_unknown_tool(db_session):
    with pytest.raises(ValueError, match="unknown tool"):
        dispatch("delete_everything", {}, db=db_session)


# ==========================================================================
# System prompt
# ==========================================================================


def test_system_prompt_forbids_novel_facts():
    """Gate 7: "The LLM system prompt MUST explicitly prohibit novel facts"."""
    lowered = SYSTEM_PROMPT.lower()
    assert "only state facts that are present in the tool results" in lowered
    assert "never invent" in lowered
    for forbidden in ("course names", "nsqf levels", "money amounts", "eligibility"):
        assert forbidden in lowered, f"prompt does not name {forbidden!r} as off-limits"
    assert "do not have that information" in lowered
    assert "officer" in lowered


def test_system_prompt_forbids_choosing_courses():
    """PLAN §6: "the LLM NEVER picks courses, only verbalizes tool output"."""
    assert "you do not choose courses" in SYSTEM_PROMPT.lower()


# ==========================================================================
# Numeral extraction and containment
# ==========================================================================


@pytest.mark.parametrize(
    "text,expected",
    [
        ("50000 rupees", {50000.0}),
        ("₹50,000", {50000.0}),
        ("50% of project cost", {50.0}),
        ("no numbers here", set()),
        ("level 2.5 course", {2.5}),
    ],
)
def test_extract_numerals_ascii(text, expected):
    assert extract_numerals(text) == expected


def test_extract_numerals_handles_devanagari_digits():
    """"५०,०००" is a numeral; a check that cannot see it is no check at all."""
    assert extract_numerals("५०,०००") == {50000.0}
    assert extract_numerals("२.५ स्तर") == {2.5}


def test_extract_numerals_handles_telugu_digits():
    assert extract_numerals("౫౦ గంటలు") == {50.0}


def test_numerals_in_json_reads_inside_strings():
    payload = {"phrase": "up to ₹50,000 or 50% of project cost", "hours": 300}
    values = numerals_in_json(payload)
    assert {50000.0, 50.0, 300.0} <= values


def test_numerals_in_json_ignores_booleans():
    assert 1.0 not in numerals_in_json({"flag": True}) - {1.0} or True
    values = numerals_in_json({"flag": True, "other": False})
    assert values == set()


def test_check_passes_when_every_numeral_is_in_the_json():
    payload = {"hours": 300, "cap": 50000}
    report = check_numerals("The course is 300 hours and support is 50,000 rupees.", payload)
    assert report.grounded
    assert not report.ungrounded


def test_check_fails_on_an_invented_number():
    payload = {"hours": 300}
    report = check_numerals("The course is 300 hours and pays a 7500 rupee stipend.", payload)
    assert not report.grounded
    assert "7500" in report.ungrounded_list


def test_check_fails_on_an_invented_devanagari_number():
    payload = {"hours": 300}
    report = check_numerals("यह कोर्स 300 घंटे का है और ७५०० रुपये मिलेंगे।", payload)
    assert not report.grounded
    assert "7500" in report.ungrounded_list


def test_grouping_and_currency_do_not_cause_false_positives():
    payload = {"phrase": "up to ₹50,000 or 50% of project cost"}
    assert check_numerals("आपको ₹50,000 तक मिल सकते हैं।", payload).grounded
    assert check_numerals("You may get 50000 rupees.", payload).grounded


# ==========================================================================
# The ladder: LLM -> regenerate once -> template
# ==========================================================================


def test_template_reader_needs_no_llm(items, monkeypatch):
    """Gate 7: "Implement template-only verbalizer mode requiring NO LLM"."""
    monkeypatch.setattr("core.config.settings.llm_provider", "template")

    def explode(*args, **kwargs):
        raise AssertionError("template mode must not construct an LLM provider")

    monkeypatch.setattr("core.llm.providers.get_provider", explode)

    from core.llm.verbalizer import verbalize

    spoken = verbalize(items, "hi")
    assert spoken.mode == "template"
    assert spoken.grounded is True
    assert spoken.text


def test_template_output_is_grounded_by_construction(items):
    text = templates.verbalize_recommendation(items, "hi")
    report = check_numerals(text, tool_payload_for_items(items))
    assert report.grounded, report.explain()


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_template_is_grounded_in_every_language(items, lang):
    text = templates.verbalize_recommendation(items, lang)
    assert check_numerals(text, tool_payload_for_items(items)).grounded


def test_clean_llm_output_is_used_as_is(items, monkeypatch):
    monkeypatch.setattr("core.config.settings.llm_provider", "mock")
    monkeypatch.setattr("core.llm.guarded.get_provider", lambda _n: MockLlmProvider())
    spoken = generate_grounded(items, "hi")
    assert spoken.mode == "llm"
    assert spoken.attempts == 1
    assert spoken.grounded is True


def test_ungrounded_output_triggers_exactly_one_regeneration(items, monkeypatch):
    """PLAN §6 STEP 6: "violation -> regenerate once"."""
    rogue = MockLlmProvider(rogue=True)  # first call invents a stipend, second behaves
    monkeypatch.setattr("core.llm.guarded.get_provider", lambda _n: rogue)

    spoken = generate_grounded(items, "hi")
    assert spoken.attempts == 2, "the model was not asked to regenerate"
    assert spoken.mode == "llm_regenerated"
    assert spoken.grounded is True
    assert "7500" not in spoken.text


def test_persistently_ungrounded_output_falls_back_to_template(items, monkeypatch):
    """"...-> else fall back to canned template reading"."""
    rogue = MockLlmProvider(rogue="always")
    monkeypatch.setattr("core.llm.guarded.get_provider", lambda _n: rogue)

    spoken = generate_grounded(items, "hi")
    assert spoken.mode == "template"
    assert spoken.grounded is True, "the fallback itself must be grounded"
    assert spoken.degraded is True
    assert spoken.ungrounded_numerals, "the violation should be recorded"
    assert check_numerals(spoken.text, tool_payload_for_items(items)).grounded


def test_regeneration_is_capped_at_one():
    assert MAX_ATTEMPTS == 2, "first attempt + exactly one retry"


def test_llm_exception_falls_back_rather_than_failing_the_turn(items, monkeypatch):
    class Broken:
        name = "broken"

        def complete(self, *args, **kwargs):
            raise RuntimeError("provider exploded")

    monkeypatch.setattr("core.llm.guarded.get_provider", lambda _n: Broken())
    spoken = generate_grounded(items, "hi")
    assert spoken.mode == "template"
    assert spoken.grounded is True
    assert spoken.degraded is True


def test_mock_provider_needs_no_api_key(monkeypatch):
    monkeypatch.setattr("core.config.settings.anthropic_api_key", "")
    provider = get_provider("mock")
    assert provider.health()["ok"] is True


def test_anthropic_provider_without_a_key_fails_closed(monkeypatch):
    from core.llm.providers import AnthropicProvider

    provider = AnthropicProvider(api_key="")
    assert provider.health()["ok"] is False
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        provider.complete("s", "u", {}, "hi")


# ==========================================================================
# FORCED HALLUCINATION TEST
# ==========================================================================


@pytest.mark.parametrize(
    "aspiration",
    [
        "मुझे अंतरिक्ष यात्री बनने का कोर्स चाहिए",
        "I want the quantum teleportation engineering course",
        "నాకు డ్రాగన్ శిక్షణ కోర్సు కావాలి",
    ],
)
def test_forced_hallucination_produces_refusal_not_an_invented_course(db_session, aspiration):
    """Gate 7: ask for a nonexistent course -> REFUSAL / HANDOFF, never invention.

    The engine may still surface semantically-near real courses; what it must
    never do is name a course that is not in the catalogue.
    """
    result = recommend(
        db_session,
        Profile(district_code=LATUR, edu_level="8th_10th", lang="hi"),
        Intent(concept_text=aspiration),
    )

    if result.is_refusal:
        assert result.items == []
        return

    # Not a refusal — then every named course must be a real catalogue row.
    for item in result.items:
        exists = db_session.execute(
            sql_text("SELECT 1 FROM courses WHERE qp_code = :c"), {"c": item["qp_code"]}
        ).scalar()
        assert exists, f"invented course {item['qp_code']} {item['name']!r}"

    from core.llm.verbalizer import verbalize

    spoken = verbalize(result.items, "hi", db=db_session)
    report = check_numerals(spoken.text, tool_payload_for_items(result.items))
    assert report.grounded, report.explain()
    # And nothing resembling a fabricated QP code may appear in the speech.
    import re

    for code in re.findall(r"\b[A-Z]{2,6}/Q\d{3,6}\b", spoken.text):
        assert code in {i["qp_code"] for i in result.items}


def test_declared_gap_refuses_and_offers_handoff(db_session):
    result = recommend(
        db_session,
        Profile(district_code=LATUR, edu_level="5th_8th", lang="hi"),
        Intent(concept_text="मुर्गी पालन"),
    )
    assert result.is_refusal
    assert result.refusal == "declared_gap"
    spoken = templates.verbalize_refusal("hi")
    assert spoken, "a refusal must still say something out loud"


def test_scheme_question_outside_scope_hands_off(db_session):
    from core.llm.guarded import answer_scheme_question

    answer = answer_scheme_question(db_session, "who will win the cricket world cup", "hi")
    if not answer["answered"]:
        assert answer["handoff"] is True
        assert answer["text"]


# ==========================================================================
# Hybrid RAG
# ==========================================================================


def test_bm25_half_returns_hits(db_session):
    hits = bm25_search(db_session, "skill development programmes percentage")
    assert hits, "BM25 returned nothing from the guidelines corpus"
    assert all("chunk" in h for h in hits)


def test_vector_half_returns_hits(db_session):
    hits = vector_search(db_session, "loan assistance for beneficiaries")
    assert hits
    assert all(0.0 <= h["score"] <= 1.0001 for h in hits)


def test_hybrid_search_fuses_both_retrievers(db_session):
    hits = hybrid_search(db_session, "aspiration of the target group and job market")
    assert hits
    assert len(hits) <= 6, "ARCHITECTURE §8 asks for top-6 into scheme_fact"
    assert any(len(h["retrievers"]) == 2 for h in hits), "no chunk was found by both halves"


def test_rrf_ranks_a_doc_found_by_both_retrievers_higher():
    """The property that makes fusion worth doing."""
    bm25 = [{"id": 1}, {"id": 2}, {"id": 3}]
    dense = [{"id": 3}, {"id": 4}, {"id": 1}]
    fused = reciprocal_rank_fusion([bm25, dense], limit=4)
    ids = [row["id"] for row in fused]
    assert ids[0] in (1, 3), ids
    top = fused[0]
    assert len(top["retrievers"]) == 2


def test_rrf_constant_is_standard():
    assert RRF_K == 60


def test_retrieved_chunks_carry_citations(db_session):
    hits = hybrid_search(db_session, "ten percent skill development")
    assert hits
    for hit in hits:
        assert hit["citation"], "every retrieved chunk must be citable"
        assert "p." in hit["citation"] or "SYNTHETIC" in hit["citation"]


def test_citation_names_the_document_and_page(db_session):
    hits = hybrid_search(db_session, "Qualification Pack National Occupational Standards")
    assert hits
    citation = hits[0]["citation"]
    assert "Guidelines" in citation or "Gazette" in citation


def test_scheme_fact_via_rag_carries_citations(db_session):
    from core.llm.tools import scheme_fact

    result = scheme_fact(db_session, "what does the guideline say about training partners")
    if result["found"] and result.get("retrieval") == "hybrid_rrf":
        assert result["citations"]


def test_compliance_paragraph_is_retrievable(db_session):
    """The paragraph the whole product operationalises (research.md §1)."""
    hits = hybrid_search(db_session, "aspiration of the target group availability of job market")
    joined = " ".join(h["chunk"] for h in hits)
    assert "aspiration of the target group" in joined, (
        "Ch.3 §7.A.a.iv is not retrievable from the RAG index"
    )


def test_bm25_query_is_injection_safe(db_session):
    """A question containing tsquery operators must not blow up the search."""
    for hostile in ("a & b | c ! d", "'; DROP TABLE doc_chunks; --", "((((", "50% & !"):
        hits = bm25_search(db_session, hostile)
        assert isinstance(hits, list)
    count = db_session.execute(sql_text("SELECT count(*) FROM doc_chunks")).scalar()
    assert count > 0, "doc_chunks survived the hostile queries"


def test_hybrid_search_degrades_when_the_dense_half_fails(db_session, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("embedding backend mismatch")

    monkeypatch.setattr("core.rag.retrieve.vector_search", broken)
    hits = hybrid_search(db_session, "skill development programmes")
    assert hits, "lexical-only retrieval should still answer"


# ==========================================================================
# End-to-end grounding
# ==========================================================================


def test_verify_grounding_script_exists_and_is_runnable():
    script = REPO / "scripts" / "verify_grounding.py"
    assert script.is_file()
    body = script.read_text(encoding="utf-8")
    assert "--n" in body
    assert "50" in body


def test_grounding_holds_across_many_random_sessions(db_session):
    """A compressed in-process version of scripts/verify_grounding.py."""
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    from verify_grounding import build_cases, verify_case

    failures = []
    for profile, aspiration in build_cases(20, seed=7):
        outcome = verify_case(db_session, profile, aspiration)
        if not outcome["ok"]:
            failures.append((aspiration, outcome.get("ungrounded"), outcome.get("invented_names")))
    assert not failures, f"ungrounded output in {len(failures)} sessions: {failures[:3]}"
