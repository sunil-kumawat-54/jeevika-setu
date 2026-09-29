"""The guarded generation loop — LLM → regenerate once → template.

PLAN.md section 6 STEP 6, implemented literally:

    any number in output must appear in tool JSON (post-hoc check; violation ->
    regenerate once -> else fall back to canned template reading)

So there are exactly three outcomes, and each is recorded on the session and in
``recommendations.grounded``:

``llm``               first attempt passed the numeral check
``llm_regenerated``   first attempt failed, the retry passed
``template``          both attempts failed — the deterministic reader spoke

The template rung cannot fail the check, because it is built by substituting
tool values into fixed phrases. That is what makes the ladder terminate safely
rather than degrade into silence.
"""

from __future__ import annotations

import logging

from core.config import settings
from core.llm import templates
from core.llm.guardrails import check_numerals, tool_payload_for_items
from core.llm.providers import SYSTEM_PROMPT, get_provider
from core.llm.verbalizer import Verbalized
from core.metrics import incr

log = logging.getLogger("avsar.llm.guarded")

MAX_ATTEMPTS = 2  # first attempt + exactly one regeneration

USER_INSTRUCTION = (
    "Read this skilling recommendation back to the beneficiary. State only what "
    "the tool results contain. Keep it short and speakable."
)

RETRY_SUFFIX = (
    "\n\nYour previous reply contained {count} number(s) that do not appear in the "
    "tool results: {numbers}. Those are not facts you have. Write the reply again "
    "using ONLY numbers present in the tool results, or omit the number entirely."
)


def generate_grounded(
    items: list[dict],
    lang: str,
    *,
    district_name: str | None = None,
    include_alternatives: bool = False,
    db=None,
) -> Verbalized:
    """Verbalize ``items``, enforcing RULE 2 at every rung of the ladder."""
    if not items:
        return Verbalized(
            text=templates.verbalize_refusal(lang), mode="template", grounded=True
        )

    payload = tool_payload_for_items(items)
    provider = get_provider(settings.llm_provider)
    user = USER_INSTRUCTION

    last_report = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text = provider.complete(SYSTEM_PROMPT, user, payload, lang)
        except Exception as exc:
            log.warning(
                "LLM attempt %d failed (%s: %s) — falling back to template",
                attempt, type(exc).__name__, exc,
            )
            incr("verbalizer_llm_errors_total", provider=provider.name)
            return _template_fallback(items, lang, district_name, include_alternatives, degraded=True)

        report = check_numerals(text, payload)
        last_report = report

        if report.grounded:
            mode = "llm" if attempt == 1 else "llm_regenerated"
            incr("verbalizer_total", mode=mode)
            if attempt > 1:
                incr("verbalizer_regenerations_total")
            return Verbalized(
                text=text,
                mode=mode,
                grounded=True,
                degraded=attempt > 1,
                attempts=attempt,
            )

        log.warning(
            "attempt %d produced ungrounded numerals %s", attempt, report.ungrounded_list,
            extra={"event": "grounding_violation"},
        )
        incr("grounding_violations_total", attempt=str(attempt))

        if attempt < MAX_ATTEMPTS:
            # Regenerate ONCE, telling the model exactly which numbers were not
            # its to state.
            user = USER_INSTRUCTION + RETRY_SUFFIX.format(
                count=len(report.ungrounded_list), numbers=", ".join(report.ungrounded_list)
            )

    # Both attempts failed the check — speak the deterministic reading instead.
    incr("verbalizer_template_fallbacks_total")
    log.error(
        "falling back to template after %d ungrounded attempts: %s",
        MAX_ATTEMPTS,
        last_report.explain() if last_report else "unknown",
        extra={"event": "grounding_fallback"},
    )
    return _template_fallback(
        items,
        lang,
        district_name,
        include_alternatives,
        degraded=True,
        ungrounded=last_report.ungrounded_list if last_report else None,
    )


def _template_fallback(
    items: list[dict],
    lang: str,
    district_name: str | None,
    include_alternatives: bool,
    *,
    degraded: bool,
    ungrounded: list[str] | None = None,
) -> Verbalized:
    text = templates.verbalize_recommendation(
        items, lang, include_alternatives=include_alternatives, district_name=district_name
    )
    # Belt and braces: the template is grounded by construction, but assert it
    # rather than assume it — this is the rung nothing catches after.
    report = check_numerals(text, tool_payload_for_items(items))
    if not report.grounded:  # pragma: no cover - would be a template bug
        log.error("TEMPLATE ITSELF IS UNGROUNDED: %s", report.explain())
    incr("verbalizer_total", mode="template")
    return Verbalized(
        text=text,
        mode="template",
        grounded=report.grounded,
        degraded=degraded,
        attempts=MAX_ATTEMPTS,
        ungrounded_numerals=ungrounded,
    )


def answer_scheme_question(db, question: str, lang: str) -> dict:
    """RAG-backed scheme answer with citations, or an honest refusal.

    ARCHITECTURE.md section 7: *"Refusal/handoff: scheme-advice outside GIA scope
    -> polite redirect + officer-callback flag set on session."*
    """
    from core.domain import prompts
    from core.llm.tools import scheme_fact

    result = scheme_fact(db, question)
    if not result.get("found"):
        return {
            "answered": False,
            "text": prompts.error_text(lang, "out_of_scope"),
            "citations": [],
            "handoff": True,
        }

    payload = {"scheme_fact": result}
    provider = get_provider(settings.llm_provider)
    try:
        text = provider.complete(
            SYSTEM_PROMPT,
            f"Answer this in the session language, citing the source: {question}",
            payload,
            lang,
        )
        report = check_numerals(text, payload)
        if not report.grounded:
            text = result["answer"]
    except Exception:
        text = result["answer"]

    citations = result.get("citations") or ([result["citation"]] if result.get("citation") else [])
    return {
        "answered": True,
        "text": text,
        "citations": citations,
        "retrieval": result.get("retrieval"),
        "handoff": False,
    }
