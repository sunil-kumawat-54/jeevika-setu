"""Template verbalizer — the no-LLM rung of the fallback ladder.

PLAN.md section 6 STEP 6 ends: *"violation -> regenerate once -> else fall back
to canned template reading"*, and the fallback ladder in the same section is
*"LLM+tools -> template reader (no LLM) -> static 'top courses in your district'
menu"*.

This module is that template reader. It is **grounded by construction**: every
sentence is a phrase from ``data/prompts/dialogue.<lang>.json`` with values
substituted from the recommendation tool JSON, so no numeral can appear that the
tool did not supply. Gate 7's numeral post-check therefore passes trivially
here — which is exactly why it is a safe floor to fall back to.
"""

from __future__ import annotations

import logging

from core.domain import prompts
from core.domain.scheme_constants import LOAN_ASSISTANCE_PHRASE

log = logging.getLogger("avsar.llm.templates")


def _fmt(template: str, **kwargs) -> str:
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template


def verbalize_recommendation(
    items: list[dict],
    lang: str,
    *,
    include_alternatives: bool = False,
    district_name: str | None = None,
) -> str:
    """Speak the top recommendation (and optionally the alternates).

    PLAN.md section 7: *"Every turn <= 2 spoken sentences before yielding"* — the
    primary reading is kept to a short, chunked sequence and the alternatives
    are a separate menu action rather than a wall of speech.
    """
    if not items:
        return prompts.error_text(lang, "no_match")

    phrases = prompts.recommendation_phrases(lang)
    primary = items[0]
    parts: list[str] = []

    parts.append(_fmt(phrases.get("primary_intro", "{course}"), course=primary["name"]))

    if primary.get("nsqf_level_spoken") is not None:
        # Spoken as "3 स्तर का कौशल कोर्स", never "NSQF level 3" (PLAN.md §7).
        parts.append(_fmt(phrases.get("level_phrase", ""), level=primary["nsqf_level_spoken"]))

    if primary.get("hours"):
        parts.append(_fmt(phrases.get("duration_phrase", ""), hours=primary["hours"]))

    seats = primary.get("seats_in_district") or 0
    if seats > 0:
        parts.append(_fmt(phrases.get("centre_phrase", ""), seats=seats))
    else:
        parts.append(phrases.get("no_centre_phrase", ""))

    assistance = primary.get("assistance") or {}
    loan_phrase = assistance.get("loan_support") or LOAN_ASSISTANCE_PHRASE.get(lang, "")
    if loan_phrase:
        parts.append(_fmt(phrases.get("assistance_phrase", "{assistance}"), assistance=loan_phrase))

    if assistance.get("women_note"):
        parts.append(assistance["women_note"])

    if primary.get("stretch") and phrases.get("stretch_note"):
        parts.append(phrases["stretch_note"])

    if include_alternatives and len(items) > 1:
        parts.append(phrases.get("alternatives_intro", ""))
        for item in items[1:]:
            parts.append(_fmt(phrases.get("primary_intro", "{course}"), course=item["name"]))
            if item.get("nsqf_level_spoken") is not None:
                parts.append(
                    _fmt(phrases.get("level_phrase", ""), level=item["nsqf_level_spoken"])
                )

    parts.append(primary.get("next_step") or phrases.get("next_step", ""))
    return " ".join(p.strip() for p in parts if p and p.strip())


def verbalize_refusal(lang: str, reason: str | None = None) -> str:
    """Say we do not have it, and offer the officer — never invent a course.

    research.md section 8.5 records Malaysia's MyGOV AI chatbot being shut down
    in Aug 2025 after inaccurate answers, and notes that its surviving
    mitigations were exactly this: redirect to a human instead of guessing.
    """
    return prompts.error_text(lang, "no_match") or prompts.error_text(lang, "out_of_scope")


def verbalize_static_menu(courses: list[dict], lang: str, district_name: str | None = None) -> str:
    """The last rung: 'top courses in your district', no scoring, no LLM."""
    if not courses:
        return prompts.error_text(lang, "no_match")
    phrases = prompts.recommendation_phrases(lang)
    names = [c["name"] for c in courses[:3]]
    intro = phrases.get("alternatives_intro", "")
    return " ".join([intro, " · ".join(names), phrases.get("next_step", "")]).strip()


def summary_text(
    items: list[dict],
    lang: str,
    *,
    district_name: str | None = None,
    confirmed_course_id: int | None = None,
) -> str:
    """The SMS-style summary shown at the end (PLAN.md section 4.1)."""
    labels = prompts.summary_labels(lang)
    if not items:
        return prompts.error_text(lang, "no_match")

    chosen = items[0]
    if confirmed_course_id is not None:
        for item in items:
            if item["course_id"] == confirmed_course_id:
                chosen = item
                break

    lines = [f"{labels.get('sms_prefix', 'AVSAR:')} {chosen['name']}"]
    if chosen.get("nsqf_level_spoken") is not None:
        lines.append(f"{labels.get('level_label', 'Level')}: {chosen['nsqf_level_spoken']}")
    if chosen.get("hours"):
        lines.append(f"{labels.get('duration_label', 'Duration')}: {chosen['hours']}")
    if chosen.get("sector"):
        lines.append(f"{labels.get('sector_label', 'Sector')}: {chosen['sector']}")
    if district_name:
        lines.append(f"{labels.get('district_label', 'District')}: {district_name}")

    assistance = chosen.get("assistance") or {}
    if assistance.get("loan_support"):
        lines.append(f"{labels.get('assistance_label', 'Support')}: {assistance['loan_support']}")
    if chosen.get("next_step"):
        lines.append(f"{labels.get('next_step_label', 'Next')}: {chosen['next_step']}")

    lines.append(labels.get("disclaimer", ""))
    return "\n".join(line for line in lines if line.strip())
