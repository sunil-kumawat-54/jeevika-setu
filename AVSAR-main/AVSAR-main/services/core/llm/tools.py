"""Tool schemas — the only facts the LLM is allowed to know.

ARCHITECTURE.md section 7:
    Tools exposed to the model (strict schemas): ``search_courses(query,
    filters)``, ``get_qualification(qp_code)``, ``scheme_fact(question)``
    (RAG w/ citations), ``compute_assistance(course_cost_band)`` (returns
    guideline constants Rs 50k/50% project-cost).

research.md section 9.3 gives the schema discipline this follows:
*"strict schemas (additionalProperties:false, all fields required), enums over
boolean flags so invalid states are unrepresentable, tool_choice:'required' +
parallel_tool_calls:false for exactly zero-or-one call per turn, keep available
tools under ~20 per turn"*.

**Every tool returns real rows.** ``search_courses`` and ``get_qualification``
read the database; ``scheme_fact`` reads the RAG index and the constants module;
``compute_assistance`` does the guideline arithmetic in exactly one place. The
model never sees anything else, which is what makes RULE 2's numeral check
meaningful: the union of these results IS the set of facts that may be spoken.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.domain.scheme_constants import (
    CANONICAL_FACTS,
    GUIDELINES_TITLE,
    LOAN_ASSISTANCE_CAP_INR,
    PRIORITY_INCOME_CEILING_INR,
)
from core.domain.scheme_constants import (
    compute_assistance as _compute_assistance,
)
from core.models.tables import Course, Qualification

log = logging.getLogger("avsar.llm.tools")

MAX_SEARCH_RESULTS = 5


# --------------------------------------------------------------------------
# Schemas (Anthropic tool-use shape; the same JSON Schema works for any vendor)
# --------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_courses",
        "description": (
            "Search the NSQF course catalogue. Returns real rows from the AVSAR "
            "database. Use this to look up a course you need to mention; never "
            "state a course name that did not come from here."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job role or trade, in any of hi/mr/te/en.",
                },
                "max_nsqf_level": {
                    "type": ["number", "null"],
                    "description": "Capability ceiling. Half levels such as 4.5 are valid.",
                },
                "district_code": {
                    "type": ["string", "null"],
                    "description": "Restrict to courses with seats in this district.",
                },
            },
            "required": ["query", "max_nsqf_level", "district_code"],
        },
    },
    {
        "name": "get_qualification",
        "description": (
            "Fetch one qualification by its QP code, with NSQF level, notional "
            "hours, credits, eligibility and progression path, as published by "
            "NCVET. Use this before stating any hours or level."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "qp_code": {"type": "string", "description": "e.g. AP/Q01868"},
            },
            "required": ["qp_code"],
        },
    },
    {
        "name": "scheme_fact",
        "description": (
            "Answer a question about PM-AJAY scheme rules from the official "
            "guidelines, with a citation. Use this for any entitlement, "
            "percentage, earmark or eligibility question. If it returns nothing, "
            "say you do not know and offer to connect an officer."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "question": {"type": "string", "description": "The scheme question."},
            },
            "required": ["question"],
        },
    },
    {
        "name": "compute_assistance",
        "description": (
            "Compute the PM-AJAY loan assistance for a project cost. This is the "
            "only source of the assistance figure; never compute it yourself."
        ),
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_cost_inr": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Project cost in rupees. Use 0 to get the ceiling rule only.",
                },
            },
            "required": ["project_cost_inr"],
        },
    },
]

TOOL_NAMES = tuple(schema["name"] for schema in TOOL_SCHEMAS)


# --------------------------------------------------------------------------
# Implementations
# --------------------------------------------------------------------------


def search_courses(
    db: Session,
    query: str,
    max_nsqf_level: float | None = None,
    district_code: str | None = None,
) -> dict:
    """Real catalogue rows, via the same engine the recommender uses."""
    from decimal import Decimal

    from core.domain.recommender import Intent, Profile, recommend

    profile = Profile(district_code=district_code, lang="en")
    if max_nsqf_level is not None:
        # Map the ceiling back onto an education band so the engine's STEP 1
        # contract is respected rather than bypassed.
        ceiling = Decimal(str(max_nsqf_level))
        band = next(
            (
                key
                for key, value in sorted(
                    __import__(
                        "core.domain.recommender", fromlist=["CAPABILITY_CEILING"]
                    ).CAPABILITY_CEILING.items(),
                    key=lambda kv: kv[1],
                )
                if value >= ceiling
            ),
            "grad_plus",
        )
        profile = Profile(district_code=district_code, edu_level=band, lang="en")

    result = recommend(db, profile, Intent(concept_text=query), top_n=MAX_SEARCH_RESULTS)
    return {
        "tool": "search_courses",
        "query": query,
        "count": len(result.items),
        "results": [
            {
                "qp_code": item["qp_code"],
                "name": item["name"],
                "nsqf_level": item["nsqf_level"],
                "hours": item["hours"],
                "sector": item["sector"],
                "seats_in_district": item["seats_in_district"],
                "synthetic": item["synthetic"],
            }
            for item in result.items
        ],
        "refusal": result.refusal,
        "note": (
            "No course in the catalogue matches this query."
            if not result.items
            else "All rows are real catalogue entries."
        ),
    }


def get_qualification(db: Session, qp_code: str) -> dict:
    """One qualification, straight from the NCVET register cache."""
    qualification = db.execute(
        select(Qualification).where(Qualification.qp_code == qp_code)
    ).scalars().first()
    course = db.execute(select(Course).where(Course.qp_code == qp_code)).scalar_one_or_none()

    if qualification is None and course is None:
        return {
            "tool": "get_qualification",
            "qp_code": qp_code,
            "found": False,
            "note": "No such qualification. Do not describe it; say you do not have it.",
        }

    payload: dict[str, Any] = {"tool": "get_qualification", "qp_code": qp_code, "found": True}
    if course is not None:
        payload.update(
            {
                "name": course.sub_course,
                "sector": course.sector,
                "nsqf_level": float(course.nsqf_level) if course.nsqf_level is not None else None,
                "hours_min": course.hours_min,
                "hours_max": course.hours_max,
                "synthetic": bool(course.synthetic),
            }
        )
    if qualification is not None:
        payload.update(
            {
                "nqr_code": qualification.nqr_code,
                "name": qualification.name,
                "nsqf_level": (
                    float(qualification.nsqf_level)
                    if qualification.nsqf_level is not None
                    else payload.get("nsqf_level")
                ),
                "min_hours": qualification.min_hours,
                "max_hours": qualification.max_hours,
                "theory_hours": qualification.th_hrs,
                "practical_hours": qualification.pr_hrs,
                "ojt_hours": qualification.ojt_hrs,
                "employability_hours": qualification.es_hrs,
                "credits_min": float(qualification.credits_min) if qualification.credits_min else None,
                "credits_max": float(qualification.credits_max) if qualification.credits_max else None,
                "progression": qualification.progression_vertical,
                "awarding_body": qualification.awarding_body,
                "valid_till": qualification.valid_till.isoformat() if qualification.valid_till else None,
                "source": "NCVET Kaushalverse",
            }
        )
    return payload


def scheme_fact(db: Session | None, question: str) -> dict:
    """Answer a scheme question from the constants, then the RAG index.

    The canonical constants are checked first because they are transcribed
    verbatim from research.md section 2.3 and carry their own citation. RAG
    supplies anything the constants do not cover, with doc+page citations.
    """
    lowered = (question or "").lower()

    # Money needles are DERIVED from the constants (RULE 4): hardcoding the
    # figures here would silently go stale the day a guideline is revised.
    cap = LOAN_ASSISTANCE_CAP_INR
    income = PRIORITY_INCOME_CEILING_INR
    cap_forms = (str(cap), f"{cap:,}")
    income_forms = (str(income), f"{income:,}", f"{income // 100_000} lakh")

    keyword_map = {
        "loan_assistance": ("loan", "assistance", "ऋण", "कर्ज", *cap_forms, "money", "support"),
        "women_earmark": ("earmark", "15%", "women's schemes", "महिला"),
        "women_participation": ("women", "30%", "participation", "quota"),
        "skilling_floor": ("10%", "skill development floor", "minimum spend", "sca"),
        "priority_income": ("income", *income_forms, "eligib", "bpl", "poor"),
        "placement_target": ("placement", "70%", "job guarantee"),
        "infra_ceiling": ("infrastructure", "30%"),
        "standalone_assets": ("asset", "distribution", "standalone"),
        "training_components": ("financial literacy", "bank", "proposal"),
        "aspiration_mandate": ("aspiration", "job market", "skill gap", "nsdc", "endors"),
    }
    for key, needles in keyword_map.items():
        if any(needle in lowered for needle in needles):
            fact = CANONICAL_FACTS[key]
            return {
                "tool": "scheme_fact",
                "question": question,
                "found": True,
                "answer": fact["answer_en"],
                "values": fact["values"],
                "citation": fact["citation"],
                "source": fact["source"],
                "retrieval": "canonical_constant",
            }

    if db is not None:
        try:
            from core.rag.retrieve import hybrid_search

            hits = hybrid_search(db, question, limit=6)
            if hits:
                return {
                    "tool": "scheme_fact",
                    "question": question,
                    "found": True,
                    "answer": hits[0]["chunk"],
                    "values": {},
                    "citation": hits[0]["citation"],
                    "source": GUIDELINES_TITLE,
                    "retrieval": "hybrid_rrf",
                    "citations": [h["citation"] for h in hits],
                    "chunks": hits,
                }
        except Exception as exc:
            log.warning("scheme_fact RAG failed: %s", exc)

    return {
        "tool": "scheme_fact",
        "question": question,
        "found": False,
        "answer": None,
        "note": (
            "Not found in the guidelines. Say you do not know and offer an officer "
            "handoff; do not guess."
        ),
    }


def compute_assistance(project_cost_inr: int = 0) -> dict:
    """The guideline arithmetic, from the single constants module (RULE 4)."""
    result = _compute_assistance(int(project_cost_inr))
    return {
        "tool": "compute_assistance",
        "project_cost_inr": result.project_cost_inr,
        "cap_inr": result.cap_inr,
        "pct_of_project_cost": result.pct_of_project_cost,
        "pct_based_amount_inr": result.pct_based_amount_inr,
        "assistance_inr": result.assistance_inr,
        "binding_rule": result.binding_rule,
        "phrase_en": result.phrase_en,
        "citation": result.citation,
    }


def dispatch(name: str, arguments: dict, db: Session | None = None) -> dict:
    """Execute one tool call by name. Unknown tools fail loudly."""
    if name == "search_courses":
        return search_courses(
            db,
            arguments.get("query", ""),
            arguments.get("max_nsqf_level"),
            arguments.get("district_code"),
        )
    if name == "get_qualification":
        return get_qualification(db, arguments.get("qp_code", ""))
    if name == "scheme_fact":
        return scheme_fact(db, arguments.get("question", ""))
    if name == "compute_assistance":
        return compute_assistance(arguments.get("project_cost_inr", 0))
    raise ValueError(f"unknown tool {name!r}; available: {TOOL_NAMES}")
