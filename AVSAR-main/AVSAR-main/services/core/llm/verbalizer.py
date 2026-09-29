"""Verbalizer entry point — PLAN.md section 6 STEP 6.

    STEP 6 — Verbalize: LLM receives ONLY the structured objects + dialogue
    history; system prompt forbids new facts; any number in output must appear
    in tool JSON (post-hoc check; violation -> regenerate once -> else fall back
    to canned template reading).

This module owns the *ladder*; Gate 7 fills in the LLM providers, the tool
schemas and the RAG. The ladder itself is the safety property:

    LLM + tools  ->  regenerate once  ->  template reader (no LLM)

Every rung produces text whose numerals are a subset of the tool JSON, so the
guarantee RULE 2 asks for holds no matter how far down we fall.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.config import settings
from core.llm import templates
from core.metrics import incr

log = logging.getLogger("avsar.llm.verbalizer")


@dataclass(slots=True)
class Verbalized:
    """What was said, and how much we trust the path that produced it."""

    text: str
    mode: str  # "llm" | "llm_regenerated" | "template"
    grounded: bool
    degraded: bool = False
    attempts: int = 1
    ungrounded_numerals: list[str] | None = None


def verbalize(
    items: list[dict],
    lang: str,
    *,
    district_name: str | None = None,
    include_alternatives: bool = False,
    db=None,
) -> Verbalized:
    """Speak a recommendation set, grounded.

    ``LLM_PROVIDER=template`` (or ``mock`` without a fixture) short-circuits to
    the deterministic template reader, which is what makes the whole journey run
    with no API key at all (RULE 1).
    """
    provider = (settings.llm_provider or "mock").lower()

    if provider in ("template", "none", ""):
        return _template(items, lang, district_name, include_alternatives)

    try:
        from core.llm.guarded import generate_grounded

        return generate_grounded(
            items,
            lang,
            district_name=district_name,
            include_alternatives=include_alternatives,
            db=db,
        )
    except ImportError:
        # Gate 7 has not landed yet — the template rung is always available.
        return _template(items, lang, district_name, include_alternatives)
    except Exception as exc:
        log.warning("verbalizer fell back to template: %s: %s", type(exc).__name__, exc)
        incr("verbalizer_fallbacks_total", reason=type(exc).__name__)
        result = _template(items, lang, district_name, include_alternatives)
        result.degraded = True
        return result


def _template(
    items: list[dict], lang: str, district_name: str | None, include_alternatives: bool
) -> Verbalized:
    text = templates.verbalize_recommendation(
        items, lang, include_alternatives=include_alternatives, district_name=district_name
    )
    incr("verbalizer_total", mode="template")
    return Verbalized(text=text, mode="template", grounded=True, degraded=False)
