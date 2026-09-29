"""Bhashini ULCA adapter.

TECH_STACK.md section 2.1 gives the exact two-call contract:

    # Step 1 — Pipeline Config (FIXED URL):
    POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
    Headers: { userID, ulcaApiKey, Content-Type: application/json }
    -> response.pipelineInferenceAPIEndPoint.callbackUrl            # DYNAMIC
    -> response.pipelineInferenceAPIEndPoint.inferenceApiKey.name   # DYNAMIC
    -> response.pipelineInferenceAPIEndPoint.inferenceApiKey.value  # DYNAMIC
    -> task entries carry serviceId per task

    # Step 2 — Pipeline Compute (dynamic URL/headers from above)
    POST {callbackUrl}  Headers: { "<name-from-config>": "<value-from-config>" }

research.md section 5.2 is emphatic about the trap this adapter must avoid:
*"Inference endpoint is NOT fixed ... Hardcoding either breaks — a classic
integration bug worth mentioning in your technical-approach slide."* So the
inference URL **and** the auth header's name and value are read from the config
response on every cache miss; none of them is ever hardcoded.

Adapter rules (TECH_STACK section 2.1): *"cache config responses ~10 min per
(task,lang); retry once on 5xx then demote provider."*

Licence posture (research.md section 5.2): the self-served keys are **PoC
only**. That is fine for SIH and is stated on the roadmap slide, not hidden.
"""

from __future__ import annotations

import logging
import time
import uuid

import httpx

from core.config import settings
from core.speech.base import AsrResult, ProviderError, SpeechProvider, TtsChunk

log = logging.getLogger("avsar.speech.bhashini")

ASR_TASK = "asr"
TTS_TASK = "tts"


class _ConfigCache:
    """Per-(task, lang) cache of the dynamic inference contract."""

    def __init__(self, ttl_s: int) -> None:
        self._ttl = ttl_s
        self._entries: dict[tuple[str, str], tuple[float, dict]] = {}

    def get(self, task: str, lang: str) -> dict | None:
        entry = self._entries.get((task, lang))
        if not entry:
            return None
        stored_at, payload = entry
        if self._ttl <= 0 or time.monotonic() - stored_at >= self._ttl:
            self._entries.pop((task, lang), None)
            return None
        return payload

    def put(self, task: str, lang: str, payload: dict) -> None:
        self._entries[(task, lang)] = (time.monotonic(), payload)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)


class BhashiniProvider(SpeechProvider):
    """ASR/TTS over Bhashini ULCA pipelines."""

    name = "bhashini"

    def __init__(
        self,
        user_id: str | None = None,
        api_key: str | None = None,
        config_url: str | None = None,
        *,
        timeout_s: float | None = None,
        cache_ttl_s: int | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.user_id = user_id if user_id is not None else settings.bhashini_user_id
        self.api_key = api_key if api_key is not None else settings.bhashini_api_key
        self.config_url = config_url or settings.bhashini_config_url
        # `or` would swallow a deliberate 0 (used to disable the cache in tests),
        # so fall back only on None.
        self.timeout_s = settings.voice_timeout_s if timeout_s is None else timeout_s
        ttl = settings.bhashini_config_cache_s if cache_ttl_s is None else cache_ttl_s
        self._cache = _ConfigCache(ttl)
        self._client = client

    # -- plumbing ---------------------------------------------------------

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_s)
        return self._client

    def _require_credentials(self) -> None:
        if not self.user_id or not self.api_key:
            raise ProviderError(
                self.name,
                "BHASHINI_USER_ID and BHASHINI_API_KEY are not set "
                "(auth is API key + User ID together — research.md section 5.2)",
                retryable=False,
            )

    def fetch_config(self, task: str, lang: str) -> dict:
        """Step 1. Returns ``{callback_url, header_name, header_value, service_id}``."""
        cached = self._cache.get(task, lang)
        if cached:
            return cached

        self._require_credentials()
        body = {
            "pipelineTasks": [{"taskType": task, "config": {"language": {"sourceLanguage": lang}}}],
            "pipelineRequestConfig": {"id": str(uuid.uuid4())},
        }
        response = self._http().post(
            self.config_url,
            json=body,
            headers={
                "userID": self.user_id,
                "ulcaApiKey": self.api_key,
                "Content-Type": "application/json",
            },
        )
        if response.status_code >= 500:
            raise ProviderError(self.name, f"config HTTP {response.status_code}", retryable=True)
        if response.status_code != 200:
            raise ProviderError(self.name, f"config HTTP {response.status_code}", retryable=False)

        payload = response.json()
        endpoint = (payload or {}).get("pipelineInferenceAPIEndPoint") or {}
        inference_key = endpoint.get("inferenceApiKey") or {}
        callback_url = endpoint.get("callbackUrl")
        header_name = inference_key.get("name")
        header_value = inference_key.get("value")
        if not (callback_url and header_name and header_value):
            raise ProviderError(
                self.name,
                "config response did not carry callbackUrl + inferenceApiKey.name/.value "
                "— these are DYNAMIC and must never be hardcoded",
                retryable=False,
            )

        service_id = None
        for entry in (payload or {}).get("pipelineResponseConfig") or []:
            if entry.get("taskType") == task:
                configs = entry.get("config") or []
                if configs:
                    service_id = configs[0].get("serviceId")
                break

        resolved = {
            "callback_url": callback_url,
            "header_name": header_name,
            "header_value": header_value,
            "service_id": service_id,
        }
        self._cache.put(task, lang, resolved)
        log.info("bhashini config resolved for %s/%s", task, lang, extra={"provider": self.name})
        return resolved

    def _compute(self, task: str, lang: str, payload_builder) -> dict:
        """Step 2, with the mandated single retry on 5xx before demotion."""
        config = self.fetch_config(task, lang)
        body = payload_builder(config)
        headers = {config["header_name"]: config["header_value"], "Content-Type": "application/json"}

        last_error: Exception | None = None
        for attempt in (1, 2):  # "retry once on 5xx then demote provider"
            try:
                response = self._http().post(config["callback_url"], json=body, headers=headers)
                if response.status_code >= 500:
                    last_error = ProviderError(
                        self.name, f"compute HTTP {response.status_code}", retryable=True
                    )
                    if attempt == 1:
                        # A stale cached config is a common cause; drop it and retry.
                        self._cache.clear()
                        config = self.fetch_config(task, lang)
                        body = payload_builder(config)
                        headers = {
                            config["header_name"]: config["header_value"],
                            "Content-Type": "application/json",
                        }
                        continue
                    raise last_error
                if response.status_code != 200:
                    raise ProviderError(
                        self.name, f"compute HTTP {response.status_code}", retryable=False
                    )
                return response.json()
            except httpx.HTTPError as exc:
                last_error = ProviderError(self.name, f"transport error: {exc}", retryable=True)
                if attempt == 2:
                    raise last_error
        raise last_error or ProviderError(self.name, "compute failed", retryable=True)

    # -- interface --------------------------------------------------------

    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult:
        started = time.monotonic()
        lang = self.normalise_lang(lang)

        def build(config: dict) -> dict:
            task_config: dict = {
                "language": {"sourceLanguage": lang},
                "audioFormat": "wav",
                "transcriptionFormat": {"value": "unspecified"},
            }
            if config.get("service_id"):
                task_config["serviceId"] = config["service_id"]
            return {
                "pipelineTasks": [
                    {
                        "taskType": ASR_TASK,
                        "input": [{"source": ""}],
                        "audio": [{"audioContent": audio_b64}],
                        "config": task_config,
                    }
                ]
            }

        payload = self._compute(ASR_TASK, lang, build)
        text = ""
        for output in (payload or {}).get("pipelineResponse") or []:
            for item in output.get("output") or []:
                if item.get("source"):
                    text = item["source"]
                    break
            if text:
                break

        return AsrResult(
            text=text,
            # ULCA does not return a confidence score; a successful decode is
            # reported at 1.0 and an empty one at 0.0 rather than inventing a number.
            confidence=1.0 if text.strip() else 0.0,
            lang=lang,
            provider=self.name,
            latency_ms=(time.monotonic() - started) * 1000.0,
            raw={"note": "ULCA returns no confidence field"},
        )

    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]:
        lang = self.normalise_lang(lang)
        chunks: list[TtsChunk] = []
        # Per-sentence so the first chunk can play while the rest generate.
        for index, sentence in enumerate(self.split_sentences(text) or [text]):
            started = time.monotonic()

            def build(config: dict, _sentence: str = sentence) -> dict:
                task_config: dict = {
                    "language": {"sourceLanguage": lang},
                    "gender": "female",
                    "samplingRate": 16000,
                }
                if config.get("service_id"):
                    task_config["serviceId"] = config["service_id"]
                return {
                    "pipelineTasks": [
                        {"taskType": TTS_TASK, "input": [{"source": _sentence}], "config": task_config}
                    ]
                }

            payload = self._compute(TTS_TASK, lang, build)
            audio_b64 = ""
            for output in (payload or {}).get("pipelineResponse") or []:
                for item in output.get("audio") or []:
                    if item.get("audioContent"):
                        audio_b64 = item["audioContent"]
                        break
                if audio_b64:
                    break
            chunks.append(
                TtsChunk(
                    text=sentence,
                    audio_b64=audio_b64,
                    mime="audio/wav",
                    lang=lang,
                    provider=self.name,
                    index=index,
                    latency_ms=(time.monotonic() - started) * 1000.0,
                )
            )
        return chunks

    def health(self) -> dict:
        return {
            "ok": bool(self.user_id and self.api_key),
            "provider": self.name,
            "configured": bool(self.user_id and self.api_key),
            "cached_configs": len(self._cache),
            "licence": "PoC only (research.md section 5.2)",
        }
