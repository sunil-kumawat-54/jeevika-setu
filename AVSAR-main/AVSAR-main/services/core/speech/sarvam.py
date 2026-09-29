"""Sarvam AI adapter — the live speech provider (TECH_STACK.md section 2.2).

Bhashini remains implemented and reachable, but its ULCA approval is not
available to this team, so Sarvam is the provider AVSAR actually runs on when
keys are present. The ladder and the mock floor are untouched: RULE 1 still
holds, and ``VOICE_PROVIDER=mock`` still completes the whole journey offline.

**Contract verified against the current published API (docs.sarvam.ai), not
against the summary in TECH_STACK.md** — see ``docs/decisions.md`` D-047. Four
things in the previous version of this file did not match the live API and
would have failed on the first real call:

===========================  =============================  ===================
what                         was                            is
===========================  =============================  ===================
STT model                    ``saarika:v2``                 ``saaras:v3`` (v2.5
                                                            saarika is legacy)
TTS text field               ``inputs: [str]``              ``text: str``
TTS language field           ``target_language_code``       ``language_code``
TTS speaker                  ``meera``                      ``anushka`` (meera
                                                            is not a bulbul:v2
                                                            voice)
===========================  =============================  ===================

The live contract, as used below:

    STT   POST {base}/speech-to-text            multipart/form-data
          file=<16 kHz mono WAV>  model=saaras:v3  mode=transcribe
          language_code=hi-IN|mr-IN|te-IN|en-IN
          -> {"request_id", "transcript", "language_code",
              "language_probability"?}
          sync limit: 30 s of audio per request (AVSAR caps turns at 15 s)

    TTS   POST {base}/text-to-speech            application/json
          {"text", "language_code", "model": "bulbul:v3",
           "speaker": "shubh", "speech_sample_rate": 16000,
           "output_audio_codec": "wav"}
          bulbul:v2 is deprecated server-side and answers HTTP 400.
          -> {"request_id", "audios": ["<base64 wav>"]}

    Auth  header ``api-subscription-key`` on both.

Cost, from research.md section 5.3: ~2 min STT + ~600 chars TTS is **under
Rs 2 per conversation**, so price is a non-issue; the Starter tier's 60 req/min
account-wide limit is the real constraint, which is why TTS is cached and canned
prompts are pre-rendered.

RULE 8: every call here originates in ``services/core``. RULE 9: the key is read
from settings and never logged — failures report status codes, never headers.
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from core.config import settings
from core.speech.base import (
    MAX_UTTERANCE_S,
    AsrResult,
    ProviderError,
    SpeechProvider,
    TtsChunk,
)

log = logging.getLogger("avsar.speech.sarvam")

#: Sarvam takes BCP-47-style locales, not bare ISO-639. These four are exactly
#: the languages AVSAR supports (``core.speech.base.LANGS``).
LANG_CODES = {"hi": "hi-IN", "mr": "mr-IN", "te": "te-IN", "en": "en-IN"}

#: Reverse map, for reading the language the API says it detected.
LOCALE_TO_LANG = {v: k for k, v in LANG_CODES.items()}

#: Per-request text ceiling by TTS model, from the published limits. A single
#: spoken sentence never approaches this, but a recommendation read-out with no
#: sentence punctuation could, so it is enforced rather than assumed.
TTS_CHAR_LIMIT = {"bulbul:v2": 1500, "bulbul:v3": 2500}  # v2 kept for the cap only; it is deprecated

#: The sync REST STT endpoint accepts 30 s of audio. The browser already caps a
#: turn at 15 s (``MAX_UTTERANCE_S``); this is the server-side backstop so an
#: oversized upload fails with a clear message instead of a bare HTTP 400.
MAX_STT_AUDIO_S = 30

#: 16 kHz mono 16-bit PCM: 32 000 bytes per second, plus a small header.
_BYTES_PER_SECOND_16K_MONO = 16_000 * 2

#: Confidence AVSAR reports when Sarvam's detected language is not the language
#: the beneficiary is speaking in. The REST API returns no per-utterance
#: transcription confidence, so this is the one honest signal available: a
#: language mismatch usually means the audio was noise or a different speaker.
#: It sits deliberately below the FSM's 0.55 clarify threshold so the turn is
#: confirmed rather than acted on. A clean transcript reports 1.0 — AVSAR never
#: invents a confidence score it was not given.
MISMATCHED_LANG_CONFIDENCE = 0.5


class SarvamProvider(SpeechProvider):
    name = "sarvam"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        timeout_s: float | None = None,
        stt_model: str | None = None,
        stt_mode: str | None = None,
        tts_model: str | None = None,
        tts_speaker: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.sarvam_api_key
        self.base_url = (base_url or settings.sarvam_base).rstrip("/")
        self.timeout_s = settings.voice_timeout_s if timeout_s is None else timeout_s
        self.stt_model = stt_model or settings.sarvam_stt_model
        self.stt_mode = stt_mode or settings.sarvam_stt_mode
        self.tts_model = tts_model or settings.sarvam_tts_model
        self.tts_speaker = tts_speaker or settings.sarvam_tts_speaker
        self._client = client

    # -- plumbing ---------------------------------------------------------

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_s)
        return self._client

    def _headers(self) -> dict:
        if not self.api_key:
            # Fail closed and non-retryable: a missing key is a configuration
            # fault, and retrying it only delays the fall through to mock.
            raise ProviderError(self.name, "SARVAM_API_KEY is not set", retryable=False)
        return {"api-subscription-key": self.api_key}

    def _locale(self, lang: str) -> str:
        return LANG_CODES.get(self.normalise_lang(lang), "hi-IN")

    @staticmethod
    def _api_message(response: httpx.Response) -> str:
        """The server's own explanation, for the error message.

        Sarvam answers a rejected payload with
        ``{"error": {"message": ..., "code": ..., "request_id": ...}}``. Quoting
        it turns an opaque "HTTP 400" into a self-diagnosing failure — the
        deprecation of bulbul:v2 was invisible until this was surfaced. The body
        is the service's own text and carries no credential; only the message
        and code are taken, never headers.
        """
        try:
            payload = response.json()
        except ValueError:
            return ""
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            parts = [str(error.get(k)) for k in ("message", "code") if error.get(k)]
            return ": " + " ".join(parts) if parts else ""
        return f": {error}" if error else ""

    def _check(self, response: httpx.Response, what: str) -> None:
        """Map HTTP status onto the shared ProviderError contract.

        Only 5xx and 429 are retryable; a 401/403/400 is a configuration or
        payload fault that will fail identically on a retry, so it demotes
        straight away and the ladder moves on.
        """
        code = response.status_code
        if code == 200:
            return
        if code == 429:
            raise ProviderError(
                self.name,
                f"{what} rate limited (Starter tier is 60 req/min account-wide)",
                retryable=True,
            )
        if code in (401, 403):
            raise ProviderError(
                self.name, f"{what} HTTP {code}: key rejected", retryable=False
            )
        if code >= 500:
            raise ProviderError(
                self.name, f"{what} HTTP {code}{self._api_message(response)}", retryable=True
            )
        raise ProviderError(
            self.name, f"{what} HTTP {code}{self._api_message(response)}", retryable=False
        )

    def _post_with_retry(self, what: str, **kwargs) -> httpx.Response:
        """TECH_STACK section 2.1: *retry once on 5xx then demote provider*.

        The same rule the Bhashini adapter follows, so the router's demotion
        arithmetic means the same thing whichever provider is primary.
        """
        last: ProviderError | None = None
        for attempt in (1, 2):
            try:
                response = self._http().post(**kwargs)
            except httpx.HTTPError as exc:
                last = ProviderError(self.name, f"{what} transport error: {exc}", retryable=True)
                if attempt == 2:
                    raise last
                continue
            if response.status_code >= 500 and attempt == 1:
                log.warning(
                    "sarvam %s returned %d, retrying once",
                    what,
                    response.status_code,
                    extra={"provider": self.name, "event": "provider_retry"},
                )
                continue
            self._check(response, what)
            return response
        raise last or ProviderError(self.name, f"{what} failed", retryable=True)

    # -- ASR --------------------------------------------------------------

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        started = time.monotonic()
        lang = self.normalise_lang(lang)
        locale = self._locale(lang)

        try:
            audio = base64.b64decode(audio_b64)
        except Exception as exc:
            raise ProviderError(self.name, f"undecodable audio: {exc}", retryable=False)
        if not audio:
            raise ProviderError(self.name, "empty audio payload", retryable=False)

        seconds = len(audio) / _BYTES_PER_SECOND_16K_MONO
        if seconds > MAX_STT_AUDIO_S:
            raise ProviderError(
                self.name,
                f"audio is ~{seconds:.0f}s; the sync endpoint accepts "
                f"{MAX_STT_AUDIO_S}s (AVSAR turns are capped at {MAX_UTTERANCE_S}s)",
                retryable=False,
            )

        response = self._post_with_retry(
            "STT",
            url=f"{self.base_url}/speech-to-text",
            headers=self._headers(),
            files={"file": ("turn.wav", audio, "audio/wav")},
            # mode=transcribe keeps the transcript in the beneficiary's own
            # language. mode=translate would return English and silently break
            # the multilingual journey.
            data={
                "model": self.stt_model,
                "mode": self.stt_mode,
                "language_code": locale,
            },
        )

        payload = response.json() or {}
        text = (payload.get("transcript") or "").strip()
        detected = payload.get("language_code")

        confidence = 1.0 if text else 0.0
        if text and detected and detected != locale:
            # Sarvam heard a different language than the session is in. Report
            # it below the clarify threshold so the FSM confirms the turn.
            confidence = MISMATCHED_LANG_CONFIDENCE
            log.info(
                "sarvam detected %s while the session is %s",
                detected,
                locale,
                extra={"provider": self.name, "event": "asr_lang_mismatch"},
            )

        return AsrResult(
            text=text,
            confidence=confidence,
            lang=lang,
            provider=self.name,
            latency_ms=(time.monotonic() - started) * 1000.0,
            raw={
                "request_id": payload.get("request_id"),
                "detected_language_code": detected,
                # Probability that the DETECTED LANGUAGE is right — not a
                # transcription confidence. Recorded, never repurposed as one.
                "language_probability": payload.get("language_probability"),
                "model": self.stt_model,
                "mode": self.stt_mode,
            },
        )

    # -- TTS --------------------------------------------------------------

    def _tts_pieces(self, text: str) -> list[str]:
        """Sentences, further split so no single request exceeds the model cap."""
        limit = TTS_CHAR_LIMIT.get(self.tts_model, 1500)
        pieces: list[str] = []
        for sentence in self.split_sentences(text) or [text]:
            sentence = sentence.strip()
            if not sentence:
                continue
            while len(sentence) > limit:
                # Break on the last space inside the window so a word is never
                # cut in half; fall back to a hard cut if there is no space.
                cut = sentence.rfind(" ", 0, limit)
                cut = cut if cut > 0 else limit
                pieces.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if sentence:
                pieces.append(sentence)
        return pieces

    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        lang = self.normalise_lang(lang)
        locale = self._locale(lang)
        chunks: list[TtsChunk] = []

        for index, sentence in enumerate(self._tts_pieces(text)):
            started = time.monotonic()
            response = self._post_with_retry(
                "TTS",
                url=f"{self.base_url}/text-to-speech",
                headers=self._headers(),
                json={
                    "text": sentence,
                    "language_code": locale,
                    "model": self.tts_model,
                    "speaker": self.tts_speaker,
                    # Matches the capture format the PWA records and the mock
                    # emits, so every rung of the ladder sounds the same shape.
                    "speech_sample_rate": 16000,
                    "output_audio_codec": "wav",
                },
            )

            payload = response.json() or {}
            audios = payload.get("audios") or []
            if not audios or not audios[0]:
                raise ProviderError(
                    self.name, "TTS returned no audio for a sentence", retryable=True
                )

            chunks.append(
                TtsChunk(
                    text=sentence,
                    audio_b64=audios[0],
                    mime="audio/wav",
                    lang=lang,
                    provider=self.name,
                    index=index,
                    latency_ms=(time.monotonic() - started) * 1000.0,
                )
            )
        return chunks

    # -- health -----------------------------------------------------------

    def health(self) -> dict:
        """Cheap and credential-free — must not call the API (base contract)."""
        return {
            "ok": bool(self.api_key),
            "provider": self.name,
            "configured": bool(self.api_key),
            "stt_model": self.stt_model,
            "stt_mode": self.stt_mode,
            "tts_model": self.tts_model,
            "tts_speaker": self.tts_speaker,
            "languages": sorted(LANG_CODES),
        }
