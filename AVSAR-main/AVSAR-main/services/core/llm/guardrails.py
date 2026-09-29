"""Numeral post-check — the mechanical enforcement of RULE 2.

PLAN.md section 6 STEP 6:
    system prompt forbids new facts; any number in output must appear in tool
    JSON (post-hoc check; violation -> regenerate once -> else fall back to
    canned template reading).

ARCHITECTURE.md section 7 states the same rule as an invariant:
    Output post-check enforces numerals ⊆ tool JSON (regex extract + compare).

The check has to survive real Indic output, which is why it is more than a
``\\d+`` regex:

* **Devanagari and Telugu digits.** "५०,०००" and "౫౦" are numerals. They are
  transliterated to ASCII before comparison, or the check would pass by simply
  failing to see them.
* **Indian digit grouping.** "1,20,000" and "₹1,20,000" and "120000" are the
  same number; the comparison is on the numeric value, not the glyph string.
* **Spelled-out numbers are deliberately NOT policed.** "पचास हज़ार" carries no
  digit, so the numeral check cannot see it. That gap is covered by the system
  prompt and by the template fallback being the only path that composes such
  phrases — an honest limitation, recorded here rather than papered over.
* **Years and ordinals inside a course name** ("Class 10 to 12") are part of a
  tool-supplied string, so they are grounded by virtue of appearing in the JSON.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field

log = logging.getLogger("avsar.llm.guardrails")

#: Any run of digits (ASCII, Devanagari, Telugu, …) optionally containing
#: grouping separators or a decimal point.
_NUMERAL_RE = re.compile(r"\d[\d,\.٫٬]*", re.UNICODE)

#: Numerals that are never facts about the scheme and would otherwise force
#: spurious regenerations. Rank markers and small ordinals appear in stock
#: dialogue phrases ("1. फिर सुनें").
_ALWAYS_ALLOWED = {0, 1, 2, 3}


def _to_ascii_digits(text: str) -> str:
    """Map any Unicode decimal digit onto its ASCII equivalent."""
    out = []
    for char in text:
        if char.isdigit():
            try:
                out.append(str(unicodedata.decimal(char)))
                continue
            except (TypeError, ValueError):
                pass
        out.append(char)
    return "".join(out)


def extract_numerals(text: str) -> set[float]:
    """Every number present in ``text``, as float values."""
    normalised = _to_ascii_digits(text or "")
    values: set[float] = set()
    for match in _NUMERAL_RE.findall(normalised):
        cleaned = match.replace(",", "").rstrip(".")
        if not cleaned:
            continue
        try:
            values.add(float(cleaned))
        except ValueError:
            continue
    return values


def numerals_in_json(payload) -> set[float]:
    """Every number reachable in a tool result, including inside strings.

    Strings matter: a course named "Class 10 to 12" legitimises "10" and "12",
    and the loan-assistance phrase from ``scheme_constants`` legitimises both
    the rupee cap and the percentage it contains.
    """
    values: set[float] = set()

    def walk(node) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int | float):
            values.add(float(node))
            return
        if isinstance(node, str):
            values.update(extract_numerals(node))
            return
        if isinstance(node, dict):
            for key, value in node.items():
                values.update(extract_numerals(str(key)))
                walk(value)
            return
        if isinstance(node, list | tuple | set):
            for item in node:
                walk(item)

    walk(payload)
    return values


@dataclass
class GroundingReport:
    """Outcome of one post-check."""

    grounded: bool
    spoken: set[float] = field(default_factory=set)
    allowed: set[float] = field(default_factory=set)
    ungrounded: set[float] = field(default_factory=set)

    @property
    def ungrounded_list(self) -> list[str]:
        return [_fmt(v) for v in sorted(self.ungrounded)]

    def explain(self) -> str:
        if self.grounded:
            return "all numerals are present in the tool JSON"
        return (
            f"ungrounded numerals {self.ungrounded_list} are absent from the tool JSON "
            f"(tool JSON supplies {sorted(_fmt(v) for v in self.allowed)[:12]}…)"
        )


def _fmt(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def check_numerals(text: str, tool_payload, *, extra_allowed: set[float] | None = None) -> GroundingReport:
    """Assert ``numerals(text) ⊆ numerals(tool_payload)``."""
    spoken = extract_numerals(text)
    allowed = numerals_in_json(tool_payload) | set(_ALWAYS_ALLOWED)
    if extra_allowed:
        allowed |= extra_allowed

    ungrounded = set()
    for value in spoken:
        if value in allowed:
            continue
        # A percentage written as "50" against a tool value of 50.0, or a rupee
        # figure written unseparated against a grouped one, must not be flagged.
        if any(abs(value - candidate) < 1e-9 for candidate in allowed):
            continue
        ungrounded.add(value)

    report = GroundingReport(
        grounded=not ungrounded, spoken=spoken, allowed=allowed, ungrounded=ungrounded
    )
    if not report.grounded:
        log.warning("grounding violation: %s", report.explain(), extra={"event": "ungrounded"})
    return report


def assert_grounded(text: str, tool_payload) -> None:
    """Raise when the text is not grounded. Used by tests and the drill."""
    report = check_numerals(text, tool_payload)
    if not report.grounded:
        raise ValueError(report.explain())


def tool_payload_for_items(items: list[dict]) -> dict:
    """The exact JSON a recommendation reading is allowed to draw numerals from.

    Kept as one function so the verbalizer, the guardrail and
    ``scripts/verify_grounding.py`` all compare against the *same* payload —
    a grounding check that compares against a different object than the one the
    model saw proves nothing.
    """
    return {"recommendations": items}


def serialise(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
