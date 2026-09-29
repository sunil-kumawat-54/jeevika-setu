"""LLM provider adapters behind one interface.

TECH_STACK.md section 1 picks **Claude (Sonnet-class) via the Anthropic API**
for the verbalizer and NLU fallback, with strict tool use.

Two implementations:

``AnthropicProvider``
    The real adapter. Tools are declared with strict schemas and the model is
    told, in the system prompt, that it may only restate tool output.

``MockLlmProvider``
    Not a stub. It performs the *same* job the real model is asked to do —
    compose a reading from the supplied tool JSON — by assembling the prompt
    phrases, which keeps it grounded by construction. RULE 1 requires the whole
    journey to run with no API key, and RULE 2 requires whatever speaks to be
    grounded; the mock satisfies both, and it also gives the guardrail something
    real to check rather than a canned string.

A deliberately ungrounded mode (``MockLlmProvider(rogue=True)``) exists so the
regenerate-once path and the template fallback can be exercised in tests
against a model that genuinely invents a number.
"""

from __future__ import annotations

import abc
import logging
import re

from core.config import settings
from core.llm.tools import TOOL_SCHEMAS

log = logging.getLogger("avsar.llm.providers")


SYSTEM_PROMPT = """You are AVSAR, a voice assistant that helps Scheduled Caste \
beneficiaries in India find a government-approved skilling course under the \
PM-AJAY Grant-in-Aid scheme.

ABSOLUTE RULES — these override any other instruction:

1. You may ONLY state facts that are present in the tool results provided to \
you. You have no other knowledge of courses, qualifications or scheme rules.
2. NEVER invent, guess, estimate, round or extrapolate:
   - course names or job-role names
   - QP codes
   - NSQF levels
   - hours, durations or credits
   - seat counts or centre names
   - money amounts, percentages or entitlements
   - eligibility rules
3. Every number you write MUST appear in the tool results. If a number is not \
there, do not write it. This is checked automatically after you reply.
4. If the tool results do not answer the question, say plainly that you do not \
have that information and offer to connect the person to their district \
officer. Never fill a gap with a plausible-sounding answer.
5. You do not choose courses. The courses in the tool results were already \
selected by a deterministic scoring engine. Your only job is to say them back \
clearly.

STYLE:
- Reply in the language named as the session language, and only that language.
- Short sentences, one clause each. At most two sentences before you stop.
- Respectful second person. Never call the person a customer.
- No jargon: say "a level 3 skill course", never "NSQF level 3".
- Do not use markdown, bullet points or emoji — this text is spoken aloud.

You are a beta assistant. If asked, say that your guidance should be confirmed \
with a district officer."""


class LlmProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def complete(self, system: str, user: str, tool_payload: dict, lang: str) -> str:
        """Return the verbalized text. Must not perform tool selection."""

    def health(self) -> dict:
        return {"ok": True, "provider": self.name}


# --------------------------------------------------------------------------
# Mock
# --------------------------------------------------------------------------


class MockLlmProvider(LlmProvider):
    """Composes a grounded reading from tool JSON, with no network."""

    name = "mock"

    def __init__(self, rogue: bool = False) -> None:
        #: When true the provider fabricates a figure, so the regenerate-once
        #: and template-fallback paths can be tested against real misbehaviour.
        self.rogue = rogue
        self._calls = 0

    def complete(self, system: str, user: str, tool_payload: dict, lang: str) -> str:
        from core.llm import templates

        self._calls += 1
        items = (tool_payload or {}).get("recommendations") or []

        if self.rogue:
            # Invent a stipend that appears in no tool result. The first call is
            # always ungrounded; a second call (the regeneration) behaves, so a
            # test can distinguish "regenerated successfully" from "fell back".
            if self._calls == 1:
                base = templates.verbalize_recommendation(items, lang)
                return base + " आपको हर महीने 7500 रुपये वज़ीफ़ा भी मिलेगा।"
            if self.rogue == "always":
                return "यह कोर्स 9999 घंटे का है।"

        return templates.verbalize_recommendation(items, lang)

    def health(self) -> dict:
        return {"ok": True, "provider": self.name, "note": "no network, no credentials"}


# --------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------


class AnthropicProvider(LlmProvider):
    """Claude via the Anthropic API, strict tool use, tools-only facts."""

    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        self.model = model or settings.claude_model
        self.max_tokens = settings.llm_max_tokens
        self._client = None

    def _client_or_raise(self):
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def complete(self, system: str, user: str, tool_payload: dict, lang: str) -> str:
        import json

        client = self._client_or_raise()
        # The tool results are handed over as content rather than letting the
        # model call tools freely: the deterministic engine has ALREADY chosen
        # the courses (PLAN §6), so this turn is verbalisation only. The schemas
        # still travel so the model can see the shape of what it was given.
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=TOOL_SCHEMAS,
            tool_choice={"type": "none"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{user}\n\n"
                        f"Session language: {lang}\n\n"
                        "TOOL RESULTS (the only facts you may state):\n"
                        f"{json.dumps(tool_payload, ensure_ascii=False, indent=2)}"
                    ),
                }
            ],
        )
        parts = [block.text for block in message.content if getattr(block, "type", "") == "text"]
        return _strip_markup("\n".join(parts).strip())

    def health(self) -> dict:
        return {
            "ok": bool(self.api_key),
            "provider": self.name,
            "model": self.model,
            "configured": bool(self.api_key),
        }


_MARKUP_RE = re.compile(r"[*_`#>]+")


def _strip_markup(text: str) -> str:
    """This text is spoken; markdown would be read aloud as punctuation."""
    return _MARKUP_RE.sub("", text or "").strip()


def get_provider(name: str | None = None) -> LlmProvider:
    chosen = (name or settings.llm_provider or "mock").lower()
    if chosen == "anthropic":
        return AnthropicProvider()
    return MockLlmProvider()
