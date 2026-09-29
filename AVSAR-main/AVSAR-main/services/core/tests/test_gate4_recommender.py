"""Gate 4 — recommendation engine acceptance tests.

Covers exactly what the gate demands: determinism, education -> NSQF mapping,
eligibility, scoring, top-3 behaviour and the stretch-relaxation case — with
RULE 5 (NUMERIC(3,1), never an integer cast) enforced throughout.
"""

from __future__ import annotations

import pathlib
import re
from decimal import Decimal

import pytest

from core.domain.recommender import (
    CAPABILITY_CEILING,
    TOP_N,
    WEIGHTS,
    Candidate,
    Intent,
    Profile,
    _level_fit,
    _normalise_semantic,
    capability_ceiling,
    recommend,
    score_candidate,
    spoken_level,
)

REPO = pathlib.Path(__file__).resolve().parents[3]

# Demo district codes from the real LGD seed.
LATUR = "270481"
VARANASI = "090187"
NALGONDA = "360514"
GAYA = "100196"


def _profile(**kwargs) -> Profile:
    base = {
        "district_code": LATUR,
        "age_band": "18_30",
        "gender": "female",
        "edu_level": "8th_10th",
        "current_work": "unemployed",
        "lang": "hi",
    }
    base.update(kwargs)
    return Profile(**base)


# --------------------------------------------------------------------------
# STEP 4 weights — pinned by the build brief, must not drift
# --------------------------------------------------------------------------


def test_weights_are_exactly_as_specified():
    """PLAN.md §6 STEP 4. The brief pins 0.40/0.25/0.15/0.10/0.10."""
    assert WEIGHTS["semantic_fit"] == 0.40
    assert WEIGHTS["local_supply"] == 0.25
    assert WEIGHTS["level_fit"] == 0.15
    assert WEIGHTS["placement_prior"] == 0.10
    assert WEIGHTS["equity_boost"] == 0.10


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_placement_prior_is_the_guideline_target():
    """PLAN.md §6: "sector placement prior; seed constant 0.7 = guideline target"."""
    from core.domain.scheme_constants import PLACEMENT_PRIOR, PLACEMENT_TARGET_PCT

    assert PLACEMENT_PRIOR == 0.7
    assert float(PLACEMENT_TARGET_PCT) == 70.0


# --------------------------------------------------------------------------
# STEP 1 — education -> NSQF capability ceiling
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "edu,expected",
    [
        ("none", "2"),
        ("up_to_5th", "2"),
        ("5th_8th", "3"),
        ("8th_10th", "4"),
        ("10th_12th", "4.5"),
        ("grad_plus", "7"),
    ],
)
def test_capability_ceiling_matches_plan_step_1(edu, expected):
    ceiling, softened = capability_ceiling(edu, "unemployed")
    assert ceiling == Decimal(expected)
    assert softened is False


def test_ceiling_is_decimal_not_float():
    """RULE 5 — the 10th-12th ceiling is 4.5; float drift here would be a bug."""
    ceiling, _ = capability_ceiling("10th_12th", None)
    assert isinstance(ceiling, Decimal)
    assert ceiling == Decimal("4.5")


@pytest.mark.parametrize("work", ["artisan", "small_trade", "shg_member"])
def test_experience_softens_the_ceiling_by_one(work):
    """PLAN.md §6 STEP 1: "(ceiling softens +1 if current_work indicates experience)"."""
    plain, _ = capability_ceiling("5th_8th", "unemployed")
    softened, flag = capability_ceiling("5th_8th", work)
    assert softened == plain + 1
    assert flag is True


def test_unknown_education_gets_the_lowest_ceiling():
    """Never over-promise to someone whose education was not captured."""
    ceiling, _ = capability_ceiling(None, None)
    assert ceiling == Decimal("2")


def test_every_education_option_in_the_dialogue_has_a_ceiling():
    """The UI's option list and the engine's map must not drift apart."""
    import json

    prompts = json.loads(
        (REPO / "data/prompts/dialogue.hi.json").read_text(encoding="utf-8")
    )
    ui_values = {o["value"] for o in prompts["options"]["edu_level"]}
    assert ui_values == set(CAPABILITY_CEILING), (
        f"dialogue offers {ui_values} but the ceiling map has {set(CAPABILITY_CEILING)}"
    )


# --------------------------------------------------------------------------
# RULE 5 — half levels survive the whole pipeline
# --------------------------------------------------------------------------


def test_spoken_level_floors_only_for_speech():
    """PLAN.md §7 speaks "3 स्तर का कौशल कोर्स"; RULE 5 allows a display floor."""
    assert spoken_level(Decimal("3.5")) == 3
    assert spoken_level(Decimal("4.0")) == 4
    assert spoken_level(None) is None


def test_ceiling_of_four_excludes_a_four_point_five_course(db_session):
    """The classic integer-cast bug: int(4.5) == 4 would wrongly admit it."""
    profile = _profile(edu_level="8th_10th")  # ceiling 4.0
    result = recommend(db_session, profile, Intent(concept_text="सिलाई का काम"))
    for item in result.items:
        if item["nsqf_level"] is not None and not result.stretch:
            assert item["nsqf_level"] <= 4.0, f"{item['qp_code']} at L{item['nsqf_level']} exceeds the ceiling"


def test_half_level_courses_are_recommendable(db_session):
    """23% of this corpus sits at a half level; they must not be silently lost."""
    profile = _profile(edu_level="10th_12th")  # ceiling 4.5
    result = recommend(db_session, profile, Intent(concept_text="सिलाई का काम"))
    levels = [i["nsqf_level"] for i in result.items if i["nsqf_level"] is not None]
    assert levels, "no levelled recommendation produced"
    assert any(level % 1 != 0 for level in levels), (
        f"no half-level course surfaced from {levels} — integer truncation?"
    )


def test_no_integer_cast_of_level_in_the_recommender():
    """RULE 5 — the only floor() allowed is in spoken_level()."""
    source = (REPO / "services/core/domain/recommender.py").read_text(encoding="utf-8")
    floors = re.findall(r"math\.floor\(", source)
    assert len(floors) == 1, f"expected exactly one math.floor (spoken_level), found {len(floors)}"
    assert "int(candidate.nsqf_level)" not in source
    assert "int(course.nsqf_level)" not in source


# --------------------------------------------------------------------------
# STEP 2 — candidate generation, C1 ∪ C2
# --------------------------------------------------------------------------


def test_curated_crosswalk_drives_the_primary_recommendation(db_session):
    """C1 is the curated, exact path (PLAN.md §6 STEP 2)."""
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई"))
    assert result.concept == "tailoring"
    assert result.items
    assert "crosswalk" in result.items[0]["sources"]


def test_candidate_set_is_the_union_of_c1_and_c2(db_session):
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    all_sources = {s for item in result.items for s in item["sources"]}
    assert "crosswalk" in all_sources or "semantic" in all_sources
    assert result.candidate_count > TOP_N, "candidate pool should be wider than the output"


def test_a_full_sentence_still_finds_the_curated_concept(db_session):
    """Containment matching: people speak a sentence around a curated phrase."""
    result = recommend(
        db_session, _profile(), Intent(concept_text="मैं सिलाई का काम सीखना चाहती हूँ")
    )
    assert result.concept == "tailoring"


def test_a_generic_verb_tail_does_not_hijack_the_concept(db_session):
    """Regression: "मुर्गी पालन शुरू करना है" once trigram-matched the
    micro_enterprise phrase "अपना काम शुरू करना है" on the shared verb tail and
    returned a piggery course for a poultry aspiration."""
    result = recommend(
        db_session, _profile(edu_level="5th_8th"), Intent(concept_text="मुर्गी पालन शुरू करना है")
    )
    assert result.concept == "poultry", f"concept hijacked to {result.concept}"


def test_declared_gap_refuses_instead_of_offering_another_trade(db_session):
    """A wrong confident answer is worse than an honest refusal."""
    result = recommend(
        db_session, _profile(edu_level="5th_8th"), Intent(concept_text="मुर्गी पालन")
    )
    assert result.is_refusal
    assert result.refusal == "declared_gap"
    assert result.items == []
    assert any("gap" in note for note in result.notes)


@pytest.mark.parametrize(
    "lang,utterance,expected_concept",
    [
        ("hi", "मैं सिलाई का काम सीखना चाहती हूँ", "tailoring"),
        ("mr", "मला शिवणकाम शिकायचे आहे", "tailoring"),
        ("te", "బ్యూటీ పార్లర్ కోర్సు చేయాలి", "beauty"),
        ("hi", "बिजली का काम", "electrician"),
        ("en", "I want to learn plumbing", "plumbing"),
    ],
)
def test_concept_detection_across_languages(db_session, lang, utterance, expected_concept):
    result = recommend(db_session, _profile(lang=lang), Intent(concept_text=utterance))
    assert result.concept == expected_concept


# --------------------------------------------------------------------------
# Stretch relaxation
# --------------------------------------------------------------------------


def test_stretch_relaxation_fires_when_too_few_candidates(db_session):
    """PLAN.md §6 STEP 2: "IF len(candidates) < 3: relax max_level += 1,
    re-run, flag 'stretch'".

    Data entry is the real case in this corpus: the office-assistant QPs sit at
    NSQF 3.0-3.5, so a no-education profile (ceiling 2.0) cannot reach three
    eligible candidates and the ceiling must relax to 3.0 with the flag set.
    """
    profile = _profile(edu_level="none", current_work="unemployed", district_code=VARANASI)
    result = recommend(db_session, profile, Intent(concept_text="डाटा एंट्री"))
    assert result.items, "stretch relaxation failed to produce any recommendation"
    assert result.stretch is True
    assert result.ceiling > 2.0
    assert all(item["stretch"] is True for item in result.items)
    assert any("relaxed" in note for note in result.notes)


def test_stretch_surfaces_courses_above_the_original_ceiling(db_session):
    """The point of relaxing is to reach courses the raw ceiling excluded."""
    profile = _profile(edu_level="none", current_work="unemployed")
    result = recommend(db_session, profile, Intent(concept_text="डाटा एंट्री"))
    base_ceiling, _ = capability_ceiling("none", "unemployed")
    levels = [i["nsqf_level"] for i in result.items if i["nsqf_level"] is not None]
    assert any(level > float(base_ceiling) for level in levels), (
        f"stretch flagged but every level {levels} already fit under {base_ceiling}"
    )


def test_no_stretch_when_enough_candidates_fit(db_session):
    profile = _profile(edu_level="grad_plus")
    result = recommend(db_session, profile, Intent(concept_text="सिलाई का काम"))
    assert result.stretch is False
    assert result.ceiling == 7.0


# --------------------------------------------------------------------------
# STEP 3 — eligibility; gender BOOSTS, never FILTERS
# --------------------------------------------------------------------------


def test_gender_boosts_and_never_filters(db_session):
    """PLAN.md §6 STEP 3: "gender-targeted courses BOOST not FILTER"."""
    female = recommend(db_session, _profile(gender="female"), Intent(concept_text="सिलाई का काम"))
    male = recommend(db_session, _profile(gender="male"), Intent(concept_text="सिलाई का काम"))
    assert female.items and male.items
    assert len(female.items) == len(male.items), "gender changed the number of options"
    # The same courses remain available to both; only ordering/score may differ.
    assert {i["qp_code"] for i in male.items} <= {
        i["qp_code"] for i in recommend(
            db_session, _profile(gender="male"), Intent(concept_text="सिलाई का काम")
        ).items
    }


def test_equity_boost_does_not_stereotype_trades():
    """Regression: an earlier version boosted sewing/beauty/tailor for women,
    which steered women toward assumed trades rather than scheme-targeted ones."""
    source = (REPO / "services/core/domain/recommender.py").read_text(encoding="utf-8")
    boost_fn = source.split("def _equity_boost", 1)[1].split("\ndef ", 1)[0]
    active = "\n".join(
        line for line in boost_fn.splitlines() if not line.strip().startswith("#")
    )
    for stereotype in ('"beauty"', '"sewing"', '"tailor"'):
        assert stereotype not in active, f"equity boost still keys on {stereotype}"


def test_women_note_only_appears_for_female_profiles(db_session):
    female = recommend(db_session, _profile(gender="female"), Intent(concept_text="सिलाई का काम"))
    male = recommend(db_session, _profile(gender="male"), Intent(concept_text="सिलाई का काम"))
    assert "women_note" in female.items[0]["assistance"]
    assert "women_note" not in male.items[0]["assistance"]


# --------------------------------------------------------------------------
# STEP 4 — scoring
# --------------------------------------------------------------------------


def test_semantic_fit_is_normalised_across_the_candidate_set():
    """multilingual-e5 compresses cosines into ~0.75-0.86; without min-max the
    0.40 weight would carry almost no signal."""
    candidates = [
        Candidate(i, f"X/Q{i:04d}", "n", None, None, None, None, False, False, semantic_raw=raw)
        for i, raw in enumerate([0.78, 0.81, 0.86], start=1)
    ]
    _normalise_semantic(candidates)
    fits = [c.factors["semantic_fit"] for c in candidates]
    assert min(fits) == 0.0
    assert max(fits) == 1.0


def test_level_fit_peaks_at_the_ceiling():
    assert _level_fit(Decimal("4"), Decimal("4")) == 1.0
    assert _level_fit(Decimal("2"), Decimal("4")) < 1.0
    assert _level_fit(Decimal("3.5"), Decimal("4")) > _level_fit(Decimal("2"), Decimal("4"))


def test_score_is_the_weighted_sum_of_its_factors():
    candidate = Candidate(1, "X/Q0001", "probe", "Sector", Decimal("3"), 400, 600, False, False)
    candidate.factors["semantic_fit"] = 1.0
    candidate.seats = 50
    score = score_candidate(candidate, _profile(), Decimal("3"), 50)
    expected = sum(
        WEIGHTS[k] * float(candidate.factors[k]) for k in WEIGHTS
    )
    assert abs(score - expected) < 1e-6


def test_factors_are_recorded_for_audit(db_session):
    """The officer dashboard and the grounding script both read these."""
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    factors = result.items[0]["factors"]
    for key in WEIGHTS:
        assert key in factors, f"factor {key} not recorded"
    assert "weights" in factors and "weighted" in factors


def test_local_supply_penalty_flag_is_set(db_session):
    """PLAN.md §6 STEP 4: "seats in district; 0 if none -> penalty flag"."""
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    for item in result.items:
        assert item["factors"]["no_local_supply"] is (item["seats_in_district"] == 0)


def test_local_supply_lifts_a_course_in_its_own_district(db_session):
    """The same aspiration in a district with seats must rank supply higher."""
    with_supply = recommend(
        db_session, _profile(district_code=VARANASI, edu_level="none"),
        Intent(concept_text="बिजली का काम"),
    )
    assert with_supply.items
    top = with_supply.items[0]
    assert top["seats_in_district"] > 0
    assert top["factors"]["local_supply"] > 0


# --------------------------------------------------------------------------
# STEP 5 — top-3 output schema
# --------------------------------------------------------------------------


def test_returns_at_most_three(db_session):
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    assert 0 < len(result.items) <= TOP_N == 3


def test_ranks_are_dense_and_ordered(db_session):
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    assert [i["rank"] for i in result.items] == list(range(1, len(result.items) + 1))
    scores = [i["score"] for i in result.items]
    assert scores == sorted(scores, reverse=True)


def test_output_schema_is_complete(db_session):
    """PLAN.md §6 STEP 5 fixes the fields."""
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    required = {
        "qp_code", "name", "nsqf_level", "duration_band", "hours", "sector",
        "why", "assistance", "next_step",
    }
    for item in result.items:
        missing = required - set(item)
        assert not missing, f"recommendation item missing {missing}"


def test_assistance_facts_come_from_scheme_constants(db_session):
    """RULE 4 — the loan figures must be the single-source constants."""
    from core.domain.scheme_constants import (
        LOAN_ASSISTANCE_CAP_INR,
        LOAN_ASSISTANCE_PHRASE_EN,
    )

    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    assistance = result.items[0]["assistance"]
    assert assistance["cap_inr"] == LOAN_ASSISTANCE_CAP_INR
    assert assistance["loan_support_en"] == LOAN_ASSISTANCE_PHRASE_EN
    assert assistance["pct_of_project_cost"] == 50.0


def test_synthetic_flag_reaches_the_recommendation(db_session):
    """Honesty: a synthetic catalogue row stays labelled all the way out."""
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    assert all("synthetic" in item for item in result.items)


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_output_is_localised(db_session, lang):
    result = recommend(db_session, _profile(lang=lang), Intent(concept_text="tailoring"))
    assert result.items
    assert result.items[0]["why"]
    assert result.items[0]["next_step"]


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------


def test_recommendation_is_deterministic(db_session):
    """PLAN.md §14 and the grounding script both depend on this."""
    profile = _profile()
    intent = Intent(concept_text="मैं सिलाई का काम सीखना चाहती हूँ")
    first = recommend(db_session, profile, intent)
    for _ in range(4):
        again = recommend(db_session, profile, intent)
        assert [i["qp_code"] for i in again.items] == [i["qp_code"] for i in first.items]
        assert [i["score"] for i in again.items] == [i["score"] for i in first.items]


def test_ties_break_deterministically(db_session):
    """Equal scores must not reorder between runs."""
    profile = _profile(district_code=GAYA)
    intent = Intent(concept_text="हस्तशिल्प")
    runs = [
        [i["qp_code"] for i in recommend(db_session, profile, intent).items] for _ in range(3)
    ]
    assert runs[0] == runs[1] == runs[2]


def test_different_profiles_give_different_results(db_session):
    """Determinism must not mean insensitivity to the profile."""
    low = recommend(db_session, _profile(edu_level="none"), Intent(concept_text="बिजली का काम"))
    high = recommend(db_session, _profile(edu_level="grad_plus"), Intent(concept_text="बिजली का काम"))
    assert low.ceiling != high.ceiling


def test_nonexistent_aspiration_refuses(db_session):
    """Forced-hallucination posture at the engine level: no invented course."""
    result = recommend(
        db_session, _profile(), Intent(concept_text="मुझे अंतरिक्ष यात्री बनना है क्वांटम")
    )
    if result.items:
        # Semantic recall may still surface something; it must never be fabricated.
        for item in result.items:
            assert item["qp_code"], "a recommendation without a QP code is invented"
    else:
        assert result.refusal


# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------


def test_recommendations_persist_with_factors(db_session):
    from sqlalchemy import select as sa_select

    from core.domain.recommender import persist_recommendations
    from core.models.tables import Recommendation
    from core.models.tables import Session as SessionRow

    session = db_session.execute(
        sa_select(SessionRow).where(SessionRow.synthetic.is_(True)).limit(1)
    ).scalar_one()
    result = recommend(db_session, _profile(), Intent(concept_text="सिलाई का काम"))
    persist_recommendations(db_session, session.id, result)
    rows = db_session.execute(
        sa_select(Recommendation).where(Recommendation.session_id == session.id)
    ).scalars().all()
    assert len(rows) == len(result.items)
    assert all(r.factors for r in rows)
    assert all(r.grounded for r in rows)
    db_session.rollback()
