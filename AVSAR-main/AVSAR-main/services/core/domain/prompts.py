"""Loader for ``data/prompts/dialogue.{hi,mr,te,en}.json``.

PLAN.md section 5.2 keeps *"every spoken prompt as data (not hardcoded strings)
so language QA is parallelizable"*. Nothing in the request path may contain a
user-facing sentence; it all comes from these files.
"""

from __future__ import annotations

import functools
import json
import logging
import pathlib

log = logging.getLogger("avsar.prompts")

REPO = pathlib.Path(__file__).resolve().parents[3]
PROMPT_DIR = REPO / "data" / "prompts"
LANGS = ("hi", "mr", "te", "en")
FALLBACK_LANG = "hi"


@functools.lru_cache(maxsize=8)
def load(lang: str) -> dict:
    lang = lang if lang in LANGS else FALLBACK_LANG
    path = PROMPT_DIR / f"dialogue.{lang}.json"
    if not path.exists():
        log.error("dialogue prompts missing for %s at %s", lang, path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def clear_cache() -> None:
    load.cache_clear()


def step_prompt(lang: str, step: str) -> dict:
    """``{prompt, short, help}`` for a dialogue step."""
    steps = load(lang).get("steps", {})
    if step in steps:
        return steps[step]
    fallback = load(FALLBACK_LANG).get("steps", {}).get(step)
    return fallback or {"prompt": "", "short": step, "help": ""}


def options(lang: str, key: str) -> list[dict]:
    """Option list for a slot (age_band, gender, edu_level, current_work…)."""
    data = load(lang).get("options", {})
    return data.get(key) or load(FALLBACK_LANG).get("options", {}).get(key, [])


def suggestions(lang: str) -> list[dict]:
    """Suggestion chips.

    research.md section 6.1 measured that pre-generated suggestion buttons drove
    **>45% of interactions** in Farmer.Chat, and that low-digital-literacy users
    struggle to phrase an open question — which is why these lead the aspiration
    screen and free speech comes second.
    """
    return load(lang).get("suggestions") or load(FALLBACK_LANG).get("suggestions", [])


def consent(lang: str) -> dict:
    return load(lang).get("consent") or load(FALLBACK_LANG).get("consent", {})


def recommendation_phrases(lang: str) -> dict:
    return load(lang).get("recommendation") or load(FALLBACK_LANG).get("recommendation", {})


def menu(lang: str) -> dict:
    return load(lang).get("menu") or load(FALLBACK_LANG).get("menu", {})


def summary_labels(lang: str) -> dict:
    return load(lang).get("summary") or load(FALLBACK_LANG).get("summary", {})


def ui(lang: str) -> dict:
    return load(lang).get("ui") or load(FALLBACK_LANG).get("ui", {})


def error_text(lang: str, code: str) -> str:
    errors = load(lang).get("errors", {})
    if code in errors:
        return errors[code]
    return load(FALLBACK_LANG).get("errors", {}).get(code, "")


def option_label(lang: str, key: str, value: str) -> str:
    for option in options(lang, key):
        if option.get("value") == value:
            return option.get("label", value)
    return value


#: Slot -> the option list that answers it. Used to render <=4 choices per
#: screen (RULE 7) and to validate an incoming choice.
SLOT_OPTIONS = {
    "age_band": "age_band",
    "gender": "gender",
    "edu_level": "edu_level",
    "current_work": "current_work",
}


def valid_values(lang: str, slot: str) -> set[str]:
    key = SLOT_OPTIONS.get(slot)
    if not key:
        return set()
    return {o["value"] for o in options(lang, key)}
