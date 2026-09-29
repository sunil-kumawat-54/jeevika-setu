"""THE single source of truth for every PM-AJAY scheme fact in AVSAR.

RULE 4 - no scheme figure may be duplicated anywhere else in the codebase, and
the LLM may never invent one.  Every constant below is transcribed from
``research.md`` section 2.3 ("GIA component mechanics - what the guidelines
actually mandate"), which in turn quotes the operative **PM-AJAY Guidelines,
May 2023 Revised** (valid to 31 Dec 2030):

    https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf
    (byte-identical mirror:
     https://socialjustice.gov.in/writereaddata/UploadFile/36851753087331.pdf)

Wording traps recorded in ``research.md`` Appendix A that this module encodes
deliberately:

* Loan assistance is **"50% of *project* cost"** (May 2023), NOT "asset cost"
  (Feb 2022 wording, killed claim A.3).
* The women earmark is a **floor** ("at least 15%"), NOT a ceiling
  ("up to 15%", Feb 2022 wording, killed claim A.4).
* There is **no fixed income limit**; Rs 2.5 lakh is a *priority* threshold, not
  an eligibility cut-off (killed claim A.2 - the "BPL only" story survives only
  on a frozen pre-merger legacy page).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

# --------------------------------------------------------------------------
# Citation strings (used verbatim in RAG answers and slide exports)
# --------------------------------------------------------------------------

GUIDELINES_TITLE: Final[str] = "PM-AJAY Guidelines (May 2023 Revised)"
GUIDELINES_URL: Final[str] = (
    "https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf"
)
GUIDELINES_PAGES: Final[int] = 43  # research.md Appendix A.1: pdfinfo = 43 pp, NOT 20
GUIDELINES_VALID_TILL: Final[str] = "2030-12-31"

#: The paragraph the whole product operationalises (research.md section 1, 11 play 1).
COMPLIANCE_CITATION: Final[str] = "PM-AJAY Guidelines (May 2023), Ch. 3, Sec. 7.A.a.iv"
COMPLIANCE_QUOTE: Final[str] = (
    "The Skill Gap Analysis report of National Skill Development Corporation (NSDC) "
    "shall be factored while proposing the skilling areas/job roles to be implemented "
    "in different States/Districts. The same are to be duly endorsed by relevant "
    "District Skilling Authority or authorized functionary of State Skill Development "
    "Mission, confirming that the proposals are relevant to the District/State, in "
    "terms of aspiration of the target group and availability of job market."
)

# --------------------------------------------------------------------------
# Spending earmarks - research.md section 2.3, "Spending earmarks (per year)"
# --------------------------------------------------------------------------

#: ">= 10% of Special Central Assistance -> skill development programmes (hard floor)".
SKILLING_FLOOR_PCT: Final[Decimal] = Decimal("10")

#: ">= 15% of total Grants -> income-generating schemes EXCLUSIVELY for SC women".
#: The Feb 2022 text said "up to 15%"; the 2023 revision turned the ceiling into a
#: floor (research.md Appendix A.4).
WOMEN_EARMARK_FLOOR_PCT: Final[Decimal] = Decimal("15")

#: "<= 30% -> infrastructural development".
INFRA_CEILING_PCT: Final[Decimal] = Decimal("30")

#: ">= 30% women candidates participation in skill development programmes".
WOMEN_PARTICIPATION_FLOOR_PCT: Final[Decimal] = Decimal("30")

# --------------------------------------------------------------------------
# Beneficiary eligibility & assistance norms - research.md section 2.3
# --------------------------------------------------------------------------

#: "Priority to SC families/persons with annual income <= Rs 2.50 lakh."
#: NOTE: this is a PRIORITY threshold. research.md section 2.3 states explicitly
#: "No fixed income limit." Never use it as an eligibility filter.
PRIORITY_INCOME_CEILING_INR: Final[int] = 250_000
HAS_FIXED_INCOME_LIMIT: Final[bool] = False

#: "Assistance toward such loans: up to Rs 50,000 or 50% of project cost,
#:  whichever is less, per beneficiary/household."
LOAN_ASSISTANCE_CAP_INR: Final[int] = 50_000
LOAN_ASSISTANCE_PCT_OF_PROJECT_COST: Final[Decimal] = Decimal("50")

#: The exact phrase that must be spoken/printed. RULE 4 pins this string.
LOAN_ASSISTANCE_PHRASE_EN: Final[str] = (
    "up to ₹50,000 or 50% of project cost, whichever is less"
)
LOAN_ASSISTANCE_PHRASE: Final[dict[str, str]] = {
    "en": LOAN_ASSISTANCE_PHRASE_EN,
    "hi": "अधिकतम ₹50,000 या प्रोजेक्ट लागत का 50%, जो भी कम हो",
    "mr": "जास्तीत जास्त ₹50,000 किंवा प्रकल्प खर्चाच्या 50%, यापैकी जे कमी असेल",
    "te": "గరిష్ఠంగా ₹50,000 లేదా ప్రాజెక్టు ఖర్చులో 50%, ఏది తక్కువైతే అది",
}

#: "No standalone individual asset distribution" - assets must sit inside an
#: appraised bundled livelihood project (Project Appraisal Committee).
STANDALONE_ASSET_DISTRIBUTION_ALLOWED: Final[bool] = False

#: "Every training programme must include financial literacy + preparation of a
#:  basic bank-linkable project proposal."
MANDATORY_TRAINING_COMPONENTS: Final[tuple[str, ...]] = (
    "financial literacy",
    "basic bank-linkable project proposal",
)

#: "Outcome target: 70% placement in wage/self-employment for short-term, EDP
#:  and long-term training." Also the seed constant for `placement_prior`
#:  in the scoring function (PLAN.md section 6 STEP 4).
PLACEMENT_TARGET_PCT: Final[Decimal] = Decimal("70")
PLACEMENT_PRIOR: Final[float] = 0.7

#: SC-majority SHGs are eligible entities (research.md section 2.3).
SHG_ELIGIBLE: Final[bool] = True

# --------------------------------------------------------------------------
# Skilling duration bands - research.md section 2.3 table
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DurationBand:
    """One of the four GIA skilling structures pegged to NOS/QPs."""

    key: str
    label_en: str
    hours_min: int
    hours_max: int
    note_en: str


DURATION_BANDS: Final[tuple[DurationBand, ...]] = (
    DurationBand("rpl", "RPL / up-skilling", 32, 80, "up to 1 month"),
    DurationBand(
        "stt",
        "Short-term course",
        200,
        600,
        "up to 5 months, focus on women & self-employment, "
        "or as stipulated in National Occupational Standards (NOS) and Qualification Packs (QPs)",
    ),
    DurationBand("edp", "Entrepreneurship Development Programme", 80, 80, "about 10 days"),
    DurationBand(
        "long_term",
        "Long-term course",
        960,
        1920,
        "6 months to 1 year; curriculum per NSQF/NCVT/AICTE/MSME certifications",
    ),
)

DURATION_BAND_LABELS: Final[dict[str, dict[str, str]]] = {
    "rpl": {
        "en": "RPL / up-skilling (32-80 hours, up to 1 month)",
        "hi": "आरपीएल / कौशल सुधार (32-80 घंटे, एक महीने तक)",
        "mr": "आरपीएल / कौशल्य सुधारणा (32-80 तास, एक महिन्यापर्यंत)",
        "te": "ఆర్‌పీఎల్ / నైపుణ్య మెరుగుదల (32-80 గంటలు, ఒక నెల వరకు)",
    },
    "stt": {
        "en": "Short-term course (200-600 hours, up to 5 months)",
        "hi": "अल्पावधि कोर्स (200-600 घंटे, पाँच महीने तक)",
        "mr": "अल्पमुदतीचा अभ्यासक्रम (200-600 तास, पाच महिन्यांपर्यंत)",
        "te": "స్వల్పకాలిక కోర్సు (200-600 గంటలు, ఐదు నెలల వరకు)",
    },
    "edp": {
        "en": "Entrepreneurship Development Programme (about 80 hours, 10 days)",
        "hi": "उद्यमिता विकास कार्यक्रम (लगभग 80 घंटे, 10 दिन)",
        "mr": "उद्योजकता विकास कार्यक्रम (सुमारे 80 तास, 10 दिवस)",
        "te": "వ్యవసాయకత్వ అభివృద్ధి కార్యక్రమం (సుమారు 80 గంటలు, 10 రోజులు)",
    },
    "long_term": {
        "en": "Long-term course (6 months to 1 year)",
        "hi": "दीर्घावधि कोर्स (6 महीने से 1 साल)",
        "mr": "दीर्घमुदतीचा अभ्यासक्रम (6 महिने ते 1 वर्ष)",
        "te": "దీర్ఘకాలిక కోర్సు (6 నెలల నుండి 1 సంవత్సరం)",
    },
}


def duration_band_for_hours(hours: float | int | None) -> str:
    """Map notional hours onto one of the four GIA bands (research.md section 2.3)."""
    if hours is None:
        return "stt"
    h = float(hours)
    if h < 80:
        return "rpl"
    if h == 80:
        return "edp"
    if h <= 600:
        return "stt"
    return "long_term"


# --------------------------------------------------------------------------
# The canonical livelihood taxonomy - research.md section 2.4
# https://pmajay.dosje.gov.in/illustrative-list  (= Annexure-I of the guidelines)
# Exactly 10 domains. `crosswalk.gia_domain` is CHECK(1..10) against this list.
# --------------------------------------------------------------------------

GIA_DOMAINS: Final[dict[int, dict[str, str]]] = {
    1: {
        "en": "Agriculture & Soil Conservation",
        "hi": "कृषि और मृदा संरक्षण",
        "mr": "शेती आणि मृदा संवर्धन",
        "te": "వ్యవసాయం మరియు నేల సంరక్షణ",
    },
    2: {
        "en": "Horticulture",
        "hi": "बागवानी",
        "mr": "फलोत्पादन",
        "te": "ఉద్యానవన శాస్త్రం",
    },
    3: {
        "en": "Minor Irrigation",
        "hi": "लघु सिंचाई",
        "mr": "लघु सिंचन",
        "te": "చిన్న నీటిపారుదల",
    },
    4: {
        "en": "Animal Husbandry",
        "hi": "पशुपालन",
        "mr": "पशुसंवर्धन",
        "te": "పశుసంవర్ధకం",
    },
    5: {
        "en": "Fisheries",
        "hi": "मत्स्य पालन",
        "mr": "मत्स्यपालन",
        "te": "మత్స్య పరిశ్రమ",
    },
    6: {
        "en": "Food Processing",
        "hi": "खाद्य प्रसंस्करण",
        "mr": "अन्न प्रक्रिया",
        "te": "ఆహార శుద్ధీకరణ",
    },
    7: {
        "en": "Forestry / Ecology & Environment",
        "hi": "वानिकी / पर्यावरण",
        "mr": "वनीकरण / पर्यावरण",
        "te": "అటవీ శాస్త్రం / పర్యావరణం",
    },
    8: {
        "en": "Handicrafts & Handlooms",
        "hi": "हस्तशिल्प और हथकरघा",
        "mr": "हस्तकला आणि हातमाग",
        "te": "హస్తకళలు మరియు చేనేత మగ్గాలు",
    },
    9: {
        "en": "Industry, Service & Business (ISB)",
        "hi": "उद्योग, सेवा और व्यवसाय",
        "mr": "उद्योग, सेवा आणि व्यवसाय",
        "te": "పరిశ్రమ, సేవ మరియు వ్యాపారం",
    },
    10: {
        "en": "Cooperatives",
        "hi": "सहकारिता",
        "mr": "सहकार",
        "te": "సహకార సంఘాలు",
    },
}

GIA_DOMAIN_MIN: Final[int] = 1
GIA_DOMAIN_MAX: Final[int] = 10


def gia_domain_name(domain: int, lang: str = "en") -> str:
    entry = GIA_DOMAINS.get(int(domain))
    if entry is None:
        return "Unknown"
    return entry.get(lang, entry["en"])


# --------------------------------------------------------------------------
# Scheme context facts (research.md 2.1, 2.5, 2.6) - used by `scheme_fact`
# --------------------------------------------------------------------------

SCHEME_FULL_NAME: Final[str] = "Pradhan Mantri Anusuchit Jaati Abhyuday Yojana"
SCHEME_SHORT_NAME: Final[str] = "PM-AJAY"
SC_POPULATION_SHARE_PCT: Final[Decimal] = Decimal("16.6")  # Census 2011
GIA_STATES_UT_COUNT: Final[int] = 28

#: research.md section 2.5 - the absorption story. Rupees crore.
BUDGET_ACTUAL_2024_25_CR: Final[Decimal] = Decimal("736.28")
BUDGET_BE_2024_25_CR: Final[Decimal] = Decimal("2140.00")
BUDGET_BE_2025_26_CR: Final[Decimal] = Decimal("2140.00")
BUDGET_RE_2025_26_CR: Final[Decimal] = Decimal("1250.00")
BUDGET_BE_2026_27_CR: Final[Decimal] = Decimal("2140.00")
BUDGET_RE_2025_26_CUT_PCT: Final[Decimal] = Decimal("41.6")

#: research.md section 2.6 - route trainees to PMKVY/MSDE, not PM-DAKSH.
PM_DAKSH_MERGED_INTO: Final[str] = "PMKVY"
PM_DAKSH_MERGER_EFFECTIVE_FY: Final[str] = "FY2026-27"


# --------------------------------------------------------------------------
# Assistance computation - the ONLY place the arithmetic lives
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssistanceResult:
    """Outcome of :func:`compute_assistance`.

    Every number here is either an input the caller supplied or derived from the
    constants above, so the guardrail numeral post-check (RULE 2) always finds
    them in the tool JSON.
    """

    project_cost_inr: int
    cap_inr: int
    pct_of_project_cost: float
    pct_based_amount_inr: int
    assistance_inr: int
    binding_rule: str
    phrase_en: str
    citation: str


def compute_assistance(project_cost_inr: int) -> AssistanceResult:
    """Return the GIA loan assistance for a given project cost.

    Implements research.md section 2.3: *"Assistance toward such loans: up to
    Rs 50,000 or 50% of project cost, whichever is less, per
    beneficiary/household."*

    >>> compute_assistance(80_000).assistance_inr
    40000
    >>> compute_assistance(200_000).assistance_inr
    50000
    """
    if project_cost_inr < 0:
        raise ValueError("project_cost_inr must be non-negative")
    pct_amount = int(project_cost_inr * LOAN_ASSISTANCE_PCT_OF_PROJECT_COST / Decimal(100))
    assistance = min(LOAN_ASSISTANCE_CAP_INR, pct_amount)
    binding = "cap" if pct_amount >= LOAN_ASSISTANCE_CAP_INR else "percentage"
    return AssistanceResult(
        project_cost_inr=project_cost_inr,
        cap_inr=LOAN_ASSISTANCE_CAP_INR,
        pct_of_project_cost=float(LOAN_ASSISTANCE_PCT_OF_PROJECT_COST),
        pct_based_amount_inr=pct_amount,
        assistance_inr=assistance,
        binding_rule=binding,
        phrase_en=LOAN_ASSISTANCE_PHRASE_EN,
        citation=f"{GUIDELINES_TITLE}, research.md 2.3",
    )


def women_participation_status(women_pct: float) -> dict:
    """Compare a captured women-percentage against the >=30% mandate."""
    target = float(WOMEN_PARTICIPATION_FLOOR_PCT)
    return {
        "women_pct": round(float(women_pct), 1),
        "target_pct": target,
        "meets_mandate": float(women_pct) >= target,
        "gap_pct": round(max(0.0, target - float(women_pct)), 1),
        "citation": f"{GUIDELINES_TITLE}, research.md 2.3",
    }


def priority_income_status(annual_income_inr: int | None) -> dict:
    """Priority (not eligibility) check against the Rs 2.5 lakh threshold."""
    note = "No fixed income limit under PM-AJAY GIA; Rs 2.5 lakh marks priority only."
    if annual_income_inr is None:
        return {
            "priority": None,
            "threshold_inr": PRIORITY_INCOME_CEILING_INR,
            "has_fixed_income_limit": HAS_FIXED_INCOME_LIMIT,
            "note": note,
        }
    return {
        "priority": annual_income_inr <= PRIORITY_INCOME_CEILING_INR,
        "threshold_inr": PRIORITY_INCOME_CEILING_INR,
        "has_fixed_income_limit": HAS_FIXED_INCOME_LIMIT,
        "note": note,
    }


#: Facts the `scheme_fact` tool may return WITHOUT touching the RAG index.
#: Keyed by a stable id so the guardrail can diff numerals against the source.
CANONICAL_FACTS: Final[dict[str, dict]] = {
    "loan_assistance": {
        "answer_en": (
            f"Assistance toward beneficiary loans is {LOAN_ASSISTANCE_PHRASE_EN}, "
            "per beneficiary or household."
        ),
        "values": {
            "cap_inr": LOAN_ASSISTANCE_CAP_INR,
            "pct_of_project_cost": float(LOAN_ASSISTANCE_PCT_OF_PROJECT_COST),
        },
        "citation": f"{GUIDELINES_TITLE}, Ch. 3 assistance norms",
        "source": "research.md 2.3",
    },
    "skilling_floor": {
        "answer_en": (
            f"At least {SKILLING_FLOOR_PCT}% of the Special Central Assistance released each "
            "year must be spent on skill development programmes."
        ),
        "values": {"floor_pct": float(SKILLING_FLOOR_PCT)},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "women_earmark": {
        "answer_en": (
            f"At least {WOMEN_EARMARK_FLOOR_PCT}% of total grants must go to income-generating "
            "economic development schemes exclusively for Scheduled Caste women."
        ),
        "values": {"floor_pct": float(WOMEN_EARMARK_FLOOR_PCT)},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "women_participation": {
        "answer_en": (
            f"At least {WOMEN_PARTICIPATION_FLOOR_PCT}% of candidates in skill development "
            "programmes must be women."
        ),
        "values": {"floor_pct": float(WOMEN_PARTICIPATION_FLOOR_PCT)},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "priority_income": {
        "answer_en": (
            "There is no fixed income limit. Priority goes to Scheduled Caste families or "
            f"persons with annual income up to Rs {PRIORITY_INCOME_CEILING_INR:,}."
        ),
        "values": {"threshold_inr": PRIORITY_INCOME_CEILING_INR},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "placement_target": {
        "answer_en": (
            f"The outcome target is {PLACEMENT_TARGET_PCT}% placement in wage or self-employment "
            "for short-term, EDP and long-term training."
        ),
        "values": {"target_pct": float(PLACEMENT_TARGET_PCT)},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "infra_ceiling": {
        "answer_en": (
            f"No more than {INFRA_CEILING_PCT}% of grants may go to infrastructural development."
        ),
        "values": {"ceiling_pct": float(INFRA_CEILING_PCT)},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "standalone_assets": {
        "answer_en": (
            "Standalone individual asset distribution is not allowed. Assets must sit inside an "
            "appraised bundled livelihood project."
        ),
        "values": {},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "training_components": {
        "answer_en": (
            "Every training programme must include financial literacy and preparation of a basic "
            "bank-linkable project proposal."
        ),
        "values": {},
        "citation": f"{GUIDELINES_TITLE}, Ch. 3",
        "source": "research.md 2.3",
    },
    "aspiration_mandate": {
        "answer_en": COMPLIANCE_QUOTE,
        "values": {},
        "citation": COMPLIANCE_CITATION,
        "source": "research.md 1, 2.3",
    },
}
