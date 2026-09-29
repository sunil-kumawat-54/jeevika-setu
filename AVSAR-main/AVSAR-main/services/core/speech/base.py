"""Speech provider contract.

ARCHITECTURE.md section 6:
    **SpeechRouter** picks provider per call: ``VOICE_PROVIDER=mock|bhashini|
    sarvam|azure|whisper``; runtime health probe demotes a failing provider
    automatically (Jugalbandi failover pattern).

Every provider — real or mock — implements exactly this interface, which is why
``VOICE_PROVIDER=mock`` can carry the entire beneficiary journey with no network
and no credentials (RULE 1), and why RULE 8 holds: all provider egress happens
inside ``services/core``, never in the browser.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Literal

#: ISO-639 codes the product supports (TECH_STACK section 2.1: "Language codes
#: ISO-639 (hi, en, ...)").
SupportedLang = Literal["hi", "mr", "te", "en"]
LANGS: tuple[str, ...] = ("hi", "mr", "te", "en")

#: TECH_STACK section 4: "16 kHz mono WAV, <=15 s per turn".
SAMPLE_RATE_HZ = 16_000
CHANNELS = 1
MAX_UTTERANCE_S = 15


@dataclass(slots=True)
class AsrResult:
    """One transcription."""

    text: str
    confidence: float
    lang: str
    provider: str
    latency_ms: float = 0.0
    is_final: bool = True
    degraded: bool = False
    raw: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """Empty ASR drives the two-strikes -> menu-mode rule (PLAN.md §4.1)."""
        return not self.text.strip()


@dataclass(slots=True)
class TtsChunk:
    """One synthesised sentence.

    ARCHITECTURE.md section 6 streaming rule: *"TTS synthesized per-sentence;
    first sentence dispatches while later ones generate"*, so TTS returns a
    sequence of these rather than one blob.
    """

    text: str
    audio_b64: str
    mime: str
    lang: str
    provider: str
    index: int = 0
    latency_ms: float = 0.0
    degraded: bool = False


class ProviderError(RuntimeError):
    """A provider failed. Two of these demote it (PROVIDER_DEMOTE_AFTER)."""

    def __init__(self, provider: str, message: str, *, retryable: bool = True):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.retryable = retryable


class SpeechProvider(abc.ABC):
    """The contract every adapter implements (TECH_STACK.md section 2.1)."""

    name: str = "base"

    @abc.abstractmethod
    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        """base64 WAV (16 kHz mono) -> transcript."""

    @abc.abstractmethod
    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        """Text -> one chunk per sentence, in order."""

    def health(self) -> dict:
        """Cheap liveness signal for ``/readyz``. Must not perform inference."""
        return {"ok": True, "provider": self.name}

    # -- helpers shared by adapters ---------------------------------------

    @staticmethod
    def split_sentences(text: str) -> list[str]:
        """Split for per-sentence streaming.

        Devanagari uses the danda (।) and Telugu uses the full stop; W3C's
        Devanagari layout requirements also note a line must never *start* with
        a danda, so the delimiter stays attached to the sentence it ends.
        """
        import re

        parts = re.split(r"(?<=[।.!?])\s+", (text or "").strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def normalise_lang(lang: str | None) -> str:
        value = (lang or "hi").lower().split("-")[0]
        return value if value in LANGS else "hi"
