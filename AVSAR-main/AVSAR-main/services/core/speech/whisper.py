"""Lazy local Whisper adapter.

The adapter never downloads models or calls a remote service. It uses an
already-installed ``faster_whisper`` or ``whisper`` package when available;
otherwise the router receives a typed unavailable-provider error and falls
through to the fixture-backed mock provider.
"""

from __future__ import annotations

import base64
import importlib
import io
import time
import wave

from core.speech.base import AsrResult, ProviderError, SpeechProvider, TtsChunk


class WhisperSpeechProvider(SpeechProvider):
    name = "whisper"

    def __init__(self, *, model_name: str = "base", model=None) -> None:
        self.model_name = model_name
        self._model = model
        self._backend: str | None = None
        self._load_error: str | None = None

    def _load(self):
        if self._model is not None:
            return self._model
        if self._load_error:
            raise ProviderError(self.name, self._load_error, retryable=False)
        try:
            module = importlib.import_module("faster_whisper")
            self._model = module.WhisperModel(self.model_name, device="cpu", compute_type="int8")
            self._backend = "faster_whisper"
            return self._model
        except (ImportError, AttributeError):
            try:
                module = importlib.import_module("whisper")
                self._model = module.load_model(self.model_name)
                self._backend = "whisper"
                return self._model
            except (ImportError, AttributeError):
                self._load_error = (
                    "approved local Whisper dependency is unavailable; "
                    "install faster-whisper or openai-whisper to enable this provider"
                )
                raise ProviderError(self.name, self._load_error, retryable=False)

    @staticmethod
    def _wav_file(audio_b64: str) -> io.BytesIO:
        try:
            raw = base64.b64decode(audio_b64, validate=True)
        except Exception as exc:
            raise ProviderError("whisper", f"undecodable audio: {exc}", retryable=False)
        return io.BytesIO(raw)

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        started = time.monotonic()
        model = self._load()
        lang = self.normalise_lang(lang)
        audio = self._wav_file(audio_b64)
        try:
            with wave.open(audio, "rb") as wav:
                if wav.getnchannels() != 1 or wav.getframerate() != 16_000:
                    raise ProviderError(self.name, "audio must be 16 kHz mono WAV", retryable=False)
        except wave.Error as exc:
            raise ProviderError(self.name, f"invalid WAV audio: {exc}", retryable=False)

        try:
            if self._backend == "faster_whisper":
                segments, info = model.transcribe(audio, language=lang)
                text = " ".join(segment.text.strip() for segment in segments).strip()
                detected = getattr(info, "language", lang)
            else:
                result = model.transcribe(audio, language=lang)
                text = str(result.get("text", "")).strip()
                detected = lang
        except Exception as exc:
            raise ProviderError(self.name, f"local inference failed: {exc}", retryable=True)

        return AsrResult(
            text=text,
            confidence=1.0 if text else 0.0,
            lang=lang,
            provider=self.name,
            latency_ms=(time.monotonic() - started) * 1000.0,
            raw={"backend": self._backend, "detected_language": detected},
        )

    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        raise ProviderError(self.name, "Whisper provides ASR only; no local TTS adapter is configured", retryable=False)

    def health(self) -> dict:
        if self._model is not None:
            return {"ok": True, "provider": self.name, "backend": self._backend}
        try:
            self._load()
        except ProviderError as exc:
            return {"ok": False, "provider": self.name, "configured": False, "detail": str(exc)}
        return {"ok": True, "provider": self.name, "backend": self._backend}
