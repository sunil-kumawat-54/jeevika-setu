"""Azure Speech adapter — the failover leg.

research.md section 5.2 records the reliability pattern this implements:
*"OpenNyAI's Jugalbandi ships Bhashini as default speech layer **with automatic
Azure failover** — architect yours the same way."* ARCHITECTURE.md section 6
turns that into the demotion rule the router enforces.

Uses the Azure Speech REST endpoints (no SDK dependency, so the core image stays
small): short-audio recognition for ASR and the v1 synthesis endpoint for TTS.
"""

from __future__ import annotations

import base64
import logging
import time

import httpx

from core.config import settings
from core.speech.base import AsrResult, ProviderError, SpeechProvider, TtsChunk

log = logging.getLogger("avsar.speech.azure")

LOCALES = {"hi": "hi-IN", "mr": "mr-IN", "te": "te-IN", "en": "en-IN"}
VOICES = {
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
    "te": "te-IN-ShrutiNeural",
    "en": "en-IN-NeerjaNeural",
}


class AzureSpeechProvider(SpeechProvider):
    name = "azure"

    def __init__(
        self,
        key: str | None = None,
        region: str | None = None,
        *,
        timeout_s: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.key = key if key is not None else settings.azure_speech_key
        self.region = region if region is not None else settings.azure_speech_region
        self.timeout_s = settings.voice_timeout_s if timeout_s is None else timeout_s
        self._client = client

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_s)
        return self._client

    def _require(self) -> None:
        if not self.key or not self.region:
            raise ProviderError(
                self.name, "AZURE_SPEECH_KEY / AZURE_SPEECH_REGION are not set", retryable=False
            )

    def _locale(self, lang: str) -> str:
        return LOCALES.get(self.normalise_lang(lang), "hi-IN")

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        started = time.monotonic()
        self._require()
        lang = self.normalise_lang(lang)
        try:
            audio = base64.b64decode(audio_b64)
        except Exception as exc:
            raise ProviderError(self.name, f"undecodable audio: {exc}", retryable=False)

        url = (
            f"https://{self.region}.stt.speech.microsoft.com"
            "/speech/recognition/conversation/cognitiveservices/v1"
        )
        try:
            response = self._http().post(
                url,
                params={"language": self._locale(lang), "format": "detailed"},
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                },
                content=audio,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(self.name, f"transport error: {exc}", retryable=True)

        if response.status_code >= 500:
            raise ProviderError(self.name, f"STT HTTP {response.status_code}", retryable=True)
        if response.status_code != 200:
            raise ProviderError(self.name, f"STT HTTP {response.status_code}", retryable=False)

        payload = response.json() or {}
        text = payload.get("DisplayText", "")
        confidence = 0.0
        best = (payload.get("NBest") or [{}])[0]
        if best.get("Confidence") is not None:
            confidence = float(best["Confidence"])
        elif text.strip():
            confidence = 1.0

        return AsrResult(
            text=text,
            confidence=confidence,
            lang=lang,
            provider=self.name,
            latency_ms=(time.monotonic() - started) * 1000.0,
            raw={"recognition_status": payload.get("RecognitionStatus")},
        )

    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        self._require()
        lang = self.normalise_lang(lang)
        locale = self._locale(lang)
        voice = VOICES.get(lang, VOICES["hi"])
        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

        chunks: list[TtsChunk] = []
        for index, sentence in enumerate(self.split_sentences(text) or [text]):
            started = time.monotonic()
            ssml = (
                f"<speak version='1.0' xml:lang='{locale}'>"
                f"<voice xml:lang='{locale}' name='{voice}'>{_escape(sentence)}</voice></speak>"
            )
            try:
                response = self._http().post(
                    url,
                    headers={
                        "Ocp-Apim-Subscription-Key": self.key,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
                        "User-Agent": "avsar",
                    },
                    content=ssml.encode("utf-8"),
                )
            except httpx.HTTPError as exc:
                raise ProviderError(self.name, f"transport error: {exc}", retryable=True)

            if response.status_code >= 500:
                raise ProviderError(self.name, f"TTS HTTP {response.status_code}", retryable=True)
            if response.status_code != 200:
                raise ProviderError(self.name, f"TTS HTTP {response.status_code}", retryable=False)

            chunks.append(
                TtsChunk(
                    text=sentence,
                    audio_b64=base64.b64encode(response.content).decode("ascii"),
                    mime="audio/wav",
                    lang=lang,
                    provider=self.name,
                    index=index,
                    latency_ms=(time.monotonic() - started) * 1000.0,
                )
            )
        return chunks

    def health(self) -> dict:
        configured = bool(self.key and self.region)
        return {"ok": configured, "provider": self.name, "configured": configured}


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
