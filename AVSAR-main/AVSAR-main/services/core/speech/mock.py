"""Mock speech provider — the one that has to carry the demo.

ARCHITECTURE.md section 6:
    **Mock provider**: replays fixture WAVs/transcripts from ``seeds/fixtures/``
    keyed by dialogue step — full flow works airplane-mode.

RULE 1 makes this provider load-bearing rather than decorative:
``VOICE_PROVIDER=mock`` plus ``LLM_PROVIDER=mock`` must complete the **entire**
beneficiary journey on a clean machine with zero API keys and no internet. So
this is not a stub that echoes a fixed string — it replays a scripted
conversation, per dialogue step and per language, and it can deliberately
reproduce the failure modes the FSM is required to handle:

* ``empty`` — silence, to drive the two-empty-ASR -> menu-mode rule (PLAN §4.1);
* ``low_confidence`` — below threshold, to drive the clarify-once branch;
* ``unknown`` — an out-of-crosswalk aspiration, to drive refusal/handoff.

Audio honesty: the fixture WAVs are generated 16 kHz mono tones, not recorded
human speech. They exist so the audio path (encode -> transport -> decode ->
play) is genuinely exercised offline. The spoken *content* travels as the
caption text, and the UI labels mock mode. Real audio arrives by switching to a
real provider with `make mock-off`; nothing else changes.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import pathlib
import struct
import time

from core.speech.base import (
    CHANNELS,
    SAMPLE_RATE_HZ,
    AsrResult,
    SpeechProvider,
    TtsChunk,
)

log = logging.getLogger("avsar.speech.mock")

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = REPO / "seeds" / "fixtures"
ASR_FIXTURES = FIXTURES / "asr"
TTS_CACHE = FIXTURES / "tts"

#: Below this, the FSM runs its clarify-once branch (PLAN.md section 4.1).
CLARIFY_THRESHOLD = 0.55


def _wav_bytes(duration_s: float, *, freq: float = 196.0, volume: float = 0.16) -> bytes:
    """A 16 kHz mono PCM WAV of the requested length.

    Shaped with a soft attack/decay envelope and a light second harmonic so it
    reads as a deliberate UI tone rather than a glitch. Pure stdlib — the mock
    path must not need numpy, soundfile or any codec.
    """
    frames = max(1, int(SAMPLE_RATE_HZ * max(0.05, duration_s)))
    samples = bytearray()
    attack = int(frames * 0.08) or 1
    release = int(frames * 0.18) or 1
    for i in range(frames):
        if i < attack:
            envelope = i / attack
        elif i > frames - release:
            envelope = max(0.0, (frames - i) / release)
        else:
            envelope = 1.0
        t = i / SAMPLE_RATE_HZ
        value = math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(4 * math.pi * freq * t)
        samples += struct.pack("<h", int(max(-1.0, min(1.0, value)) * volume * envelope * 32767))

    data = bytes(samples)
    byte_rate = SAMPLE_RATE_HZ * CHANNELS * 2
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, CHANNELS, SAMPLE_RATE_HZ, byte_rate, CHANNELS * 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    return header + data


class MockSpeechProvider(SpeechProvider):
    """Replays ``seeds/fixtures/asr/<lang>.json`` keyed by dialogue step."""

    name = "mock"

    def __init__(self, fixtures_dir: pathlib.Path | None = None) -> None:
        self._dir = fixtures_dir or ASR_FIXTURES
        self._cache: dict[str, dict] = {}

    # -- fixtures ---------------------------------------------------------

    def _fixtures(self, lang: str) -> dict:
        lang = self.normalise_lang(lang)
        if lang in self._cache:
            return self._cache[lang]
        path = self._dir / f"{lang}.json"
        if not path.exists():
            log.warning("no ASR fixtures for %s at %s", lang, path)
            payload: dict = {"steps": {}}
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
        self._cache[lang] = payload
        return payload

    def available_steps(self, lang: str = "hi") -> list[str]:
        return sorted(self._fixtures(lang).get("steps", {}))

    # -- ASR --------------------------------------------------------------

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        """Return the scripted transcript for this dialogue step.

        ``step`` may carry a ``:variant`` suffix (``aspiration:empty``) so a
        drill or a test can force a specific failure mode without patching code.
        """
        started = time.monotonic()
        lang = self.normalise_lang(lang)
        step_name, _, variant = (step or "aspiration").partition(":")
        steps = self._fixtures(lang).get("steps", {})
        entry = steps.get(step_name) or {}

        variants = entry.get("variants") or {}
        if variant and variant in variants:
            chosen = variants[variant]
        else:
            chosen = {"text": entry.get("text", ""), "confidence": entry.get("confidence", 0.9)}

        # Exercise the real decode path so a malformed payload fails here, in
        # mock mode, rather than only against a paid provider.
        decoded_bytes = 0
        if audio_b64:
            try:
                decoded_bytes = len(base64.b64decode(audio_b64, validate=False))
            except Exception as exc:
                log.warning("mock ASR received undecodable audio: %s", exc)

        return AsrResult(
            text=chosen.get("text", ""),
            confidence=float(chosen.get("confidence", 0.9)),
            lang=lang,
            provider=self.name,
            latency_ms=(time.monotonic() - started) * 1000.0,
            is_final=True,
            degraded=True,
            raw={
                "fixture_step": step_name,
                "fixture_variant": variant or "default",
                "audio_bytes": decoded_bytes,
                "note": "mock provider — scripted fixture, no inference performed",
            },
        )

    # -- TTS --------------------------------------------------------------

    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        started = time.monotonic()
        lang = self.normalise_lang(lang)
        chunks: list[TtsChunk] = []
        for index, sentence in enumerate(self.split_sentences(text) or [""]):
            # ~14 characters per second of speech — long enough that barge-in
            # and the replay control have something real to act on.
            duration = min(8.0, max(0.45, len(sentence) / 14.0))
            audio = _wav_bytes(duration, freq=196.0 if index % 2 == 0 else 233.0)
            chunks.append(
                TtsChunk(
                    text=sentence,
                    audio_b64=base64.b64encode(audio).decode("ascii"),
                    mime="audio/wav",
                    lang=lang,
                    provider=self.name,
                    index=index,
                    latency_ms=(time.monotonic() - started) * 1000.0,
                    degraded=True,
                )
            )
        return chunks

    def health(self) -> dict:
        langs = sorted(p.stem for p in self._dir.glob("*.json")) if self._dir.exists() else []
        return {
            "ok": True,
            "provider": self.name,
            "fixture_languages": langs,
            "note": "mock provider is always healthy — it needs no network or credentials",
        }
