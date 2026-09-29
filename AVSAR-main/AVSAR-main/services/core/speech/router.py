"""SpeechRouter — provider selection, failover and demotion.

ARCHITECTURE.md section 6:
    **SpeechRouter** picks provider per call: ``VOICE_PROVIDER=mock|bhashini|
    sarvam|azure|whisper``; runtime health probe demotes a failing provider
    automatically (Jugalbandi failover pattern).

TECH_STACK.md section 2.1 fixes the demotion rule: *"retry once on 5xx then
demote provider"*, with ``PROVIDER_DEMOTE_AFTER=2``.

The ladder always ends at ``mock``. That is the whole point of RULE 1: whatever
fails upstream, the beneficiary still completes their journey, the session is
marked ``degraded``, and the UI says so rather than pretending.
"""

from __future__ import annotations

import logging
import threading
import time

from core.config import settings
from core.metrics import incr, observe
from core.speech.base import AsrResult, ProviderError, SpeechProvider, TtsChunk
from core.speech.mock import MockSpeechProvider

log = logging.getLogger("avsar.speech.router")

#: How long a demoted provider stays out before it may be tried again.
DEMOTION_COOLDOWN_S = 120.0

#: Fallback preference after the configured primary. Sarvam leads: it is the
#: provider AVSAR actually runs on, because Bhashini ULCA approval is not
#: available to this team. Bhashini stays implemented and one env var away, and
#: mock stays the floor so RULE 1 holds with no keys at all.
PROVIDER_ORDER = ("sarvam", "bhashini", "azure", "whisper", "mock")


def _build(name: str) -> SpeechProvider:
    name = (name or "mock").lower()
    if name == "bhashini":
        from core.speech.bhashini import BhashiniProvider

        return BhashiniProvider()
    if name == "sarvam":
        from core.speech.sarvam import SarvamProvider

        return SarvamProvider()
    if name == "azure":
        from core.speech.azure import AzureSpeechProvider

        return AzureSpeechProvider()
    if name == "whisper":
        from core.speech.whisper import WhisperSpeechProvider

        return WhisperSpeechProvider()
    return MockSpeechProvider()


class SpeechRouter:
    """Routes ASR/TTS through a preference ladder, demoting failures."""

    def __init__(
        self,
        primary: str | None = None,
        *,
        demote_after: int | None = None,
        providers: dict[str, SpeechProvider] | None = None,
    ) -> None:
        self.primary = (primary or settings.voice_provider or "mock").lower()
        self.demote_after = (
            settings.provider_demote_after if demote_after is None else demote_after
        )
        self._lock = threading.Lock()
        self._failures: dict[str, int] = {}
        self._demoted_at: dict[str, float] = {}
        self._built: dict[str, SpeechProvider] = dict(providers or {})

    # -- ladder -----------------------------------------------------------

    def ladder(self) -> list[str]:
        """Preference order: the configured primary, then the rest, mock last."""
        configured_order = tuple(
            item.strip().lower()
            for item in settings.voice_provider_order.split(",")
            if item.strip()
        )
        rest = [p for p in configured_order if p != self.primary]
        order = [self.primary, *rest]
        # Deduplicate while preserving order, and guarantee mock is reachable.
        seen, result = set(), []
        for name in order:
            if name not in seen:
                seen.add(name)
                result.append(name)
        if "mock" not in result:
            result.append("mock")
        return result

    def provider(self, name: str) -> SpeechProvider:
        with self._lock:
            if name not in self._built:
                self._built[name] = _build(name)
            return self._built[name]

    def is_demoted(self, name: str) -> bool:
        if name == "mock":
            return False  # the floor of the ladder is never demoted
        with self._lock:
            since = self._demoted_at.get(name)
            if since is None:
                return False
            if time.monotonic() - since > DEMOTION_COOLDOWN_S:
                # Cooldown expired — give it another chance.
                self._demoted_at.pop(name, None)
                self._failures[name] = 0
                return False
            return True

    def record_failure(self, name: str) -> bool:
        """Count a failure; returns True if this demoted the provider."""
        if name == "mock":
            return False
        with self._lock:
            count = self._failures.get(name, 0) + 1
            self._failures[name] = count
            incr("speech_provider_failures_total", provider=name)
            if count >= self.demote_after and name not in self._demoted_at:
                self._demoted_at[name] = time.monotonic()
                incr("speech_provider_demotions_total", provider=name)
                log.warning(
                    "demoting speech provider after %d failures", count,
                    extra={"provider": name, "event": "provider_demoted"},
                )
                return True
        return False

    def record_success(self, name: str) -> None:
        with self._lock:
            self._failures[name] = 0

    def active_name(self) -> str:
        for name in self.ladder():
            if not self.is_demoted(name):
                return name
        return "mock"

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._demoted_at.clear()

    # -- operations -------------------------------------------------------

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None,
                   session_id: str | None = None) -> AsrResult:
        started = time.monotonic()
        errors: list[str] = []
        for name in self.ladder():
            if self.is_demoted(name):
                errors.append(f"{name}: demoted")
                continue
            try:
                result = self.provider(name).transcribe(audio_b64, lang, step=step)
                self.record_success(name)
                # Anything below the configured primary is a degraded path.
                result.degraded = result.degraded or name != self.primary
                observe("asr", (time.monotonic() - started) * 1000.0, session_id)
                incr("speech_asr_total", provider=name)
                return result
            except ProviderError as exc:
                errors.append(str(exc))
                self.record_failure(name)
                log.warning("ASR failed, falling through", extra={"provider": name})
            except Exception as exc:  # a broken adapter must not end the session
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                self.record_failure(name)
                log.exception("ASR adapter raised", extra={"provider": name})

        # Unreachable in practice: mock never raises. Kept so the contract holds.
        observe("asr", (time.monotonic() - started) * 1000.0, session_id)
        return AsrResult(
            text="", confidence=0.0, lang=lang, provider="none",
            latency_ms=(time.monotonic() - started) * 1000.0,
            degraded=True, raw={"errors": errors},
        )

    def synthesize(self, text: str, lang: str, *, step: str | None = None,
                   session_id: str | None = None) -> list[TtsChunk]:
        started = time.monotonic()
        errors: list[str] = []
        for name in self.ladder():
            if self.is_demoted(name):
                errors.append(f"{name}: demoted")
                continue
            try:
                chunks = self.provider(name).synthesize(text, lang, step=step)
                self.record_success(name)
                for chunk in chunks:
                    chunk.degraded = chunk.degraded or name != self.primary
                if chunks:
                    observe("tts_first_byte", chunks[0].latency_ms, session_id)
                incr("speech_tts_total", provider=name)
                return chunks
            except ProviderError as exc:
                errors.append(str(exc))
                self.record_failure(name)
                log.warning("TTS failed, falling through", extra={"provider": name})
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                self.record_failure(name)
                log.exception("TTS adapter raised", extra={"provider": name})

        observe("tts_first_byte", (time.monotonic() - started) * 1000.0, session_id)
        return []

    # -- health -----------------------------------------------------------

    def health(self) -> dict:
        """Used by ``/readyz``. A mock primary counts as healthy by design."""
        active = self.active_name()
        detail = {}
        for name in self.ladder():
            try:
                detail[name] = {
                    **self.provider(name).health(),
                    "demoted": self.is_demoted(name),
                    "failures": self._failures.get(name, 0),
                }
            except Exception as exc:
                detail[name] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)}
        return {
            "ok": True,  # the mock floor guarantees the voice path always resolves
            "provider": active,
            "primary": self.primary,
            "degraded": active != self.primary,
            "ladder": self.ladder(),
            "providers": detail,
        }


_SHARED: SpeechRouter | None = None
_SHARED_LOCK = threading.Lock()


def get_router(refresh: bool = False) -> SpeechRouter:
    """Process-wide router. ``refresh=True`` after `make mock-on`/`mock-off`."""
    global _SHARED
    with _SHARED_LOCK:
        if _SHARED is None or refresh:
            _SHARED = SpeechRouter()
        return _SHARED
