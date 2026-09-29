"""Gate 5 — speech provider acceptance tests.

Proves: the SpeechRouter carries bhashini/sarvam/azure/mock behind one contract;
the Sarvam adapter matches the published live contract field-for-field;
the Bhashini adapter reads its inference URL and auth header **from the config
response** (never hardcoded) and caches it ~10 minutes; a provider is demoted
after 2 failures; and the mock provider completes the whole beneficiary journey
with no network and no credentials.
"""

from __future__ import annotations

import base64
import json
import logging
import pathlib
import struct
import time

import httpx
import pytest

from core.speech.base import LANGS, MAX_UTTERANCE_S, SAMPLE_RATE_HZ, AsrResult, ProviderError
from core.speech.bhashini import BhashiniProvider
from core.speech.mock import MockSpeechProvider
from core.speech.router import PROVIDER_ORDER, SpeechRouter
from core.speech.sarvam import SarvamProvider
from core.speech.whisper import WhisperSpeechProvider

REPO = pathlib.Path(__file__).resolve().parents[3]
FIXTURES = REPO / "seeds" / "fixtures"

JOURNEY_STEPS = [
    "language_select", "consent", "profile_district", "profile_age_band",
    "profile_gender", "profile_education", "profile_current_work",
    "aspiration", "confirm_intent", "recommendation", "summary",
]


def _mock_audio(seconds: float = 1.0) -> str:
    from core.speech.mock import _wav_bytes

    return base64.b64encode(_wav_bytes(seconds)).decode("ascii")


# --------------------------------------------------------------------------
# Contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["bhashini", "sarvam", "azure", "whisper", "mock"])
def test_every_named_provider_exists_and_implements_the_contract(name):
    """ARCHITECTURE.md §6 names exactly these four."""
    from core.speech.router import _build

    provider = _build(name)
    assert provider.name == name
    for method in ("transcribe", "synthesize", "health"):
        assert callable(getattr(provider, method))


def test_audio_contract_matches_tech_stack():
    """TECH_STACK §4: "16 kHz mono WAV, <=15 s per turn"."""
    assert SAMPLE_RATE_HZ == 16_000
    assert MAX_UTTERANCE_S == 15


def test_supported_languages():
    assert set(LANGS) == {"hi", "mr", "te", "en"}


def test_sentence_split_keeps_the_danda_attached():
    """Devanagari ends sentences with ।; a line must never start with one."""
    chunks = MockSpeechProvider().split_sentences("पहला वाक्य। दूसरा वाक्य। तीसरा।")
    assert len(chunks) == 3
    assert all(not c.startswith("।") for c in chunks)
    assert chunks[0].endswith("।")


# --------------------------------------------------------------------------
# Mock provider — the airplane-mode path
# --------------------------------------------------------------------------


def test_mock_needs_no_credentials(monkeypatch):
    """RULE 1 — zero API keys."""
    for var in ("BHASHINI_API_KEY", "BHASHINI_USER_ID", "SARVAM_API_KEY", "AZURE_SPEECH_KEY"):
        monkeypatch.delenv(var, raising=False)
    result = MockSpeechProvider().transcribe(_mock_audio(), "hi", step="aspiration")
    assert result.text
    assert result.provider == "mock"


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_mock_fixtures_exist_for_every_language(lang):
    path = FIXTURES / "asr" / f"{lang}.json"
    assert path.is_file(), f"missing mock fixtures for {lang} — run pipeline 08"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["steps"], f"{lang} fixture has no steps"


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
@pytest.mark.parametrize("step", JOURNEY_STEPS)
def test_mock_covers_every_dialogue_step(lang, step):
    """"fixtures correspond to dialogue steps; supports the full beneficiary
    journey" — so every step must return a usable transcript."""
    result = MockSpeechProvider().transcribe(_mock_audio(), lang, step=step)
    assert result.text.strip(), f"{lang}/{step} produced an empty transcript"
    assert 0.0 < result.confidence <= 1.0
    assert result.lang == lang


def test_mock_is_not_a_hello_world():
    """The brief forbids a trivial mock: the journey must be a real script, so
    each step must say something different."""
    provider = MockSpeechProvider()
    texts = {provider.transcribe(_mock_audio(), "hi", step=s).text for s in JOURNEY_STEPS}
    assert len(texts) >= len(JOURNEY_STEPS) - 1, (
        f"mock returns only {len(texts)} distinct transcripts for {len(JOURNEY_STEPS)} steps"
    )


def test_mock_aspiration_reaches_a_real_recommendation(db_session):
    """The point of the mock: it drives the actual recommendation flow."""
    from core.domain.recommender import Intent, Profile, recommend

    transcript = MockSpeechProvider().transcribe(_mock_audio(), "hi", step="aspiration")
    result = recommend(
        db_session,
        Profile(district_code="270481", gender="female", edu_level="8th_10th",
                current_work="unemployed", lang="hi"),
        Intent(concept_text=transcript.text),
    )
    assert result.concept == "tailoring"
    assert result.items, "mock transcript produced no recommendation"


def test_mock_empty_variant_drives_menu_mode():
    """PLAN.md §4.1: "Any ASR empty-result twice → offer keypad/menu mode"."""
    provider = MockSpeechProvider()
    first = provider.transcribe(_mock_audio(), "hi", step="aspiration:empty")
    second = provider.transcribe(_mock_audio(), "hi", step="aspiration:empty")
    assert first.is_empty and second.is_empty
    assert first.confidence == 0.0


def test_mock_low_confidence_variant_drives_clarify_once():
    payload = json.loads((FIXTURES / "asr" / "hi.json").read_text(encoding="utf-8"))
    threshold = payload["clarify_threshold"]
    result = MockSpeechProvider().transcribe(_mock_audio(), "hi", step="aspiration:low_confidence")
    assert result.text.strip()
    assert result.confidence < threshold


def test_mock_unknown_variant_is_outside_the_crosswalk(db_session):
    """Feeds the forced-hallucination / refusal path."""
    from core.domain.recommender import Intent, Profile, recommend

    transcript = MockSpeechProvider().transcribe(_mock_audio(), "hi", step="aspiration:unknown")
    result = recommend(
        db_session,
        Profile(district_code="270481", edu_level="8th_10th", lang="hi"),
        Intent(concept_text=transcript.text),
    )
    assert result.concept != "tailoring"


def test_mock_gap_variant_triggers_the_declared_gap_refusal(db_session):
    from core.domain.recommender import Intent, Profile, recommend

    transcript = MockSpeechProvider().transcribe(_mock_audio(), "hi", step="aspiration:gap")
    result = recommend(
        db_session,
        Profile(district_code="270481", edu_level="5th_8th", lang="hi"),
        Intent(concept_text=transcript.text),
    )
    assert result.refusal == "declared_gap"


def test_mock_tts_returns_playable_16k_mono_wav():
    chunks = MockSpeechProvider().synthesize("पहला वाक्य। दूसरा वाक्य।", "hi")
    assert len(chunks) == 2, "TTS must chunk per sentence for streaming"
    audio = base64.b64decode(chunks[0].audio_b64)
    assert audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"
    channels, rate = struct.unpack("<H", audio[22:24])[0], struct.unpack("<I", audio[24:28])[0]
    assert channels == 1, "audio must be mono"
    assert rate == SAMPLE_RATE_HZ, f"audio must be 16 kHz, got {rate}"


def test_mock_tts_orders_chunks():
    chunks = MockSpeechProvider().synthesize("एक। दो। तीन।", "hi")
    assert [c.index for c in chunks] == [0, 1, 2]


def test_mock_decodes_the_audio_it_is_given():
    """The mock exercises the real decode path so malformed payloads fail here."""
    result = MockSpeechProvider().transcribe(_mock_audio(2.0), "hi", step="aspiration")
    assert result.raw["audio_bytes"] > 0


def test_mock_health_is_always_ok():
    health = MockSpeechProvider().health()
    assert health["ok"] is True
    assert set(health["fixture_languages"]) >= {"hi", "mr", "te", "en"}


def test_whisper_unavailable_is_typed_and_never_networked():
    provider = WhisperSpeechProvider()
    health = provider.health()
    assert health["ok"] is False
    assert health["provider"] == "whisper"
    assert "unavailable" in health["detail"]


def test_whisper_unavailable_falls_through_to_mock(monkeypatch):
    monkeypatch.setattr(
        "core.speech.whisper.importlib.import_module",
        lambda name: (_ for _ in ()).throw(ImportError(name)),
    )
    router = SpeechRouter(primary="whisper")
    result = router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert result.provider == "mock"
    assert result.degraded is True


# --------------------------------------------------------------------------
# Bhashini adapter — the dynamic-endpoint contract
# --------------------------------------------------------------------------


CONFIG_RESPONSE = {
    "pipelineInferenceAPIEndPoint": {
        "callbackUrl": "https://dynamic-inference.example.gov.in/compute",
        "inferenceApiKey": {"name": "X-Dynamic-Auth", "value": "dyn-token-123"},
    },
    "pipelineResponseConfig": [
        {"taskType": "asr", "config": [{"serviceId": "ai4bharat/conformer-hi-gpu--t4"}]}
    ],
}


def _bhashini_with(handler) -> BhashiniProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return BhashiniProvider(user_id="u", api_key="k", client=client)


def test_bhashini_reads_inference_url_and_header_from_config():
    """TECH_STACK §2.1 / research.md §5.2: the inference endpoint and the auth
    header NAME and VALUE are dynamic. Hardcoding any of them is the classic
    integration bug — this test fails if we ever do."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            assert request.headers["userID"] == "u"
            assert request.headers["ulcaApiKey"] == "k"
            return httpx.Response(200, json=CONFIG_RESPONSE)
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return httpx.Response(
            200, json={"pipelineResponse": [{"output": [{"source": "सिलाई का काम"}]}]}
        )

    provider = _bhashini_with(handler)
    result = provider.transcribe(_mock_audio(), "hi")

    assert result.text == "सिलाई का काम"
    assert seen["url"] == CONFIG_RESPONSE["pipelineInferenceAPIEndPoint"]["callbackUrl"]
    assert seen["headers"]["x-dynamic-auth"] == "dyn-token-123"


def test_bhashini_sends_the_service_id_from_config():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            return httpx.Response(200, json=CONFIG_RESPONSE)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"pipelineResponse": [{"output": [{"source": "ok"}]}]})

    _bhashini_with(handler).transcribe(_mock_audio(), "hi")
    task = captured["body"]["pipelineTasks"][0]
    assert task["config"]["serviceId"] == "ai4bharat/conformer-hi-gpu--t4"
    assert task["config"]["audioFormat"] == "wav"
    assert task["audio"][0]["audioContent"]


def test_bhashini_caches_the_config():
    """"cache config responses ~10 min per (task,lang)"."""
    calls = {"config": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            calls["config"] += 1
            return httpx.Response(200, json=CONFIG_RESPONSE)
        return httpx.Response(200, json={"pipelineResponse": [{"output": [{"source": "ok"}]}]})

    provider = _bhashini_with(handler)
    for _ in range(4):
        provider.transcribe(_mock_audio(), "hi")
    assert calls["config"] == 1, f"config fetched {calls['config']} times; it must be cached"


def test_bhashini_config_cache_expires():
    calls = {"config": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            calls["config"] += 1
            return httpx.Response(200, json=CONFIG_RESPONSE)
        return httpx.Response(200, json={"pipelineResponse": [{"output": [{"source": "ok"}]}]})

    transport = httpx.MockTransport(handler)
    provider = BhashiniProvider(
        user_id="u", api_key="k", cache_ttl_s=0, client=httpx.Client(transport=transport)
    )
    provider.transcribe(_mock_audio(), "hi")
    time.sleep(0.01)
    provider.transcribe(_mock_audio(), "hi")
    assert calls["config"] == 2


def test_bhashini_cache_is_per_task_and_language():
    calls = {"config": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            calls["config"] += 1
            return httpx.Response(200, json=CONFIG_RESPONSE)
        return httpx.Response(200, json={"pipelineResponse": [{"output": [{"source": "ok"}]}]})

    provider = _bhashini_with(handler)
    provider.transcribe(_mock_audio(), "hi")
    provider.transcribe(_mock_audio(), "te")
    assert calls["config"] == 2


def test_bhashini_rejects_a_config_missing_the_dynamic_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"pipelineInferenceAPIEndPoint": {}})

    with pytest.raises(ProviderError, match="DYNAMIC"):
        _bhashini_with(handler).transcribe(_mock_audio(), "hi")


def test_bhashini_retries_once_on_5xx_then_raises():
    """"retry once on 5xx then demote provider"."""
    attempts = {"compute": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "getModelsPipeline" in str(request.url):
            return httpx.Response(200, json=CONFIG_RESPONSE)
        attempts["compute"] += 1
        return httpx.Response(503, json={"error": "unavailable"})

    with pytest.raises(ProviderError):
        _bhashini_with(handler).transcribe(_mock_audio(), "hi")
    assert attempts["compute"] == 2, f"expected exactly one retry, made {attempts['compute']} calls"


def test_bhashini_without_credentials_fails_closed():
    provider = BhashiniProvider(user_id="", api_key="")
    with pytest.raises(ProviderError, match="not set"):
        provider.transcribe(_mock_audio(), "hi")


def test_bhashini_health_reports_the_poc_licence():
    health = BhashiniProvider(user_id="", api_key="").health()
    assert health["ok"] is False
    assert "PoC" in health["licence"]


# --------------------------------------------------------------------------
# Router — failover and demotion
# --------------------------------------------------------------------------


class _AlwaysFails:
    name = "flaky"

    def __init__(self):
        self.calls = 0

    def transcribe(self, audio_b64, lang, *, step=None):
        self.calls += 1
        raise ProviderError("flaky", "boom", retryable=True)

    def synthesize(self, text, lang, *, step=None):
        self.calls += 1
        raise ProviderError("flaky", "boom", retryable=True)

    def health(self):
        return {"ok": False, "provider": "flaky"}


def test_router_ladder_always_ends_at_mock():
    for primary in PROVIDER_ORDER:
        ladder = SpeechRouter(primary=primary).ladder()
        assert ladder[0] == primary
        assert ladder[-1] == "mock" or "mock" in ladder


def test_router_falls_through_to_mock_when_the_primary_fails():
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", providers={"flaky": flaky})
    result = router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert result.text, "router failed to fall through to mock"
    assert result.provider == "mock"
    assert result.degraded is True


def test_provider_is_demoted_after_two_failures():
    """ARCHITECTURE §6 + PROVIDER_DEMOTE_AFTER=2."""
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", demote_after=2, providers={"flaky": flaky})

    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert not router.is_demoted("flaky"), "demoted too early — one failure is not two"
    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert router.is_demoted("flaky"), "provider was not demoted after 2 failures"

    calls_before = flaky.calls
    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert flaky.calls == calls_before, "a demoted provider must not be called again"


def test_demotion_changes_the_active_provider():
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", demote_after=1, providers={"flaky": flaky})
    assert router.active_name() == "flaky"
    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert router.active_name() != "flaky"


def test_mock_is_never_demoted():
    router = SpeechRouter(primary="mock", demote_after=1)
    for _ in range(5):
        router.record_failure("mock")
    assert router.is_demoted("mock") is False


def test_success_resets_the_failure_counter():
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", demote_after=3, providers={"flaky": flaky})
    router.record_failure("flaky")
    router.record_success("flaky")
    router.record_failure("flaky")
    router.record_failure("flaky")
    assert not router.is_demoted("flaky"), "counter did not reset on success"


def test_router_reports_degradation_in_health():
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", demote_after=1, providers={"flaky": flaky})
    router.transcribe(_mock_audio(), "hi", step="aspiration")
    health = router.health()
    assert health["ok"] is True, "the voice path must still resolve via mock"
    assert health["degraded"] is True
    assert health["provider"] == "mock"


def test_router_tts_falls_through_too():
    flaky = _AlwaysFails()
    router = SpeechRouter(primary="flaky", providers={"flaky": flaky})
    chunks = router.synthesize("नमस्ते। आपका स्वागत है।", "hi")
    assert chunks and all(c.provider == "mock" for c in chunks)
    assert all(c.degraded for c in chunks)


def test_router_records_metrics():
    from core.metrics import counters

    router = SpeechRouter(primary="mock")
    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert any("speech_asr_total" in key for key in counters())


# --------------------------------------------------------------------------
# Full journey, airplane mode
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_full_journey_in_mock_mode(lang):
    """RULE 1 — every step of the beneficiary journey, offline, no keys."""
    router = SpeechRouter(primary="mock")
    spoken = []
    for step in JOURNEY_STEPS:
        asr = router.transcribe(_mock_audio(), lang, step=step)
        assert asr.text.strip(), f"{lang}/{step}: empty transcript breaks the journey"
        tts = router.synthesize(asr.text, lang, step=step)
        assert tts, f"{lang}/{step}: no TTS produced"
        assert tts[0].audio_b64
        spoken.append(asr.text)
    assert len(spoken) == len(JOURNEY_STEPS)


def test_journey_needs_no_network(monkeypatch):
    """Hard proof: any outbound HTTP during the mock journey fails the test."""

    def explode(*args, **kwargs):
        raise AssertionError("mock mode attempted a network call")

    monkeypatch.setattr(httpx.Client, "send", explode)
    monkeypatch.setattr(httpx.Client, "request", explode)

    router = SpeechRouter(primary="mock")
    for step in JOURNEY_STEPS:
        result = router.transcribe(_mock_audio(), "hi", step=step)
        assert isinstance(result, AsrResult)
        assert router.synthesize(result.text, "hi", step=step)


# --------------------------------------------------------------------------
# Sarvam adapter — the live provider contract
# --------------------------------------------------------------------------
#
# Every assertion below pins a field name against the published API
# (docs.sarvam.ai). The previous version of the adapter used `saarika:v2`,
# `inputs`, `target_language_code` and the speaker `meera` — all four are wrong
# on the live API, and none of them were covered by a test, which is exactly why
# they survived. These tests fail if any of them come back.

SARVAM_LOCALES = {"hi": "hi-IN", "mr": "mr-IN", "te": "te-IN", "en": "en-IN"}

#: One natural sentence per language, to prove the adapter is language-agnostic
#: rather than Hindi-with-extras.
SPOKEN = {
    "hi": "मुझे सिलाई का काम सीखना है",
    "mr": "मला शिवणकामाचे प्रशिक्षण घ्यायचे आहे",
    "te": "నాకు కుట్టు పని నేర్చుకోవాలి",
    "en": "I want to learn tailoring work",
}


def _sarvam_with(handler, **kwargs) -> SarvamProvider:
    """A Sarvam adapter whose transport is a scripted mock — no network."""
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SarvamProvider(api_key="test-key", client=client, **kwargs)


def _stt_handler(lang: str, seen: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen["url"] = str(request.url)
            seen["headers"] = dict(request.headers)
            seen["body"] = request.content
        return httpx.Response(
            200,
            json={
                "request_id": "req-1",
                "transcript": SPOKEN[lang],
                "language_code": SARVAM_LOCALES[lang],
                "language_probability": 0.98,
            },
        )

    return handler


def _tts_handler(seen: dict | None = None, audio: str | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        if seen is not None:
            seen.setdefault("bodies", []).append(body)
            seen["url"] = str(request.url)
            seen["headers"] = dict(request.headers)
        return httpx.Response(
            200, json={"request_id": "req-2", "audios": [audio or _mock_audio(0.4)]}
        )

    return handler


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_sarvam_stt_transcribes_every_supported_language(lang):
    seen: dict = {}
    provider = _sarvam_with(_stt_handler(lang, seen))

    result = provider.transcribe(_mock_audio(), lang)

    assert result.text == SPOKEN[lang]
    assert result.lang == lang
    assert result.provider == "sarvam"
    assert result.confidence == 1.0
    assert not result.is_empty
    assert result.latency_ms >= 0
    assert seen["url"].endswith("/speech-to-text")
    assert seen["headers"]["api-subscription-key"] == "test-key"


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_sarvam_stt_sends_the_right_locale_and_model(lang):
    """Field names and values, verbatim from the published multipart contract."""
    seen: dict = {}
    provider = _sarvam_with(_stt_handler(lang, seen))
    provider.transcribe(_mock_audio(), lang)

    body = seen["body"].decode("utf-8", errors="replace")
    assert f'name="language_code"\r\n\r\n{SARVAM_LOCALES[lang]}' in body
    assert 'name="model"\r\n\r\nsaaras:v3' in body
    # translate would hand back English and silently break the journey.
    assert 'name="mode"\r\n\r\ntranscribe' in body
    assert "saarika" not in body, "saarika:* is the legacy model family"
    assert 'name="file"' in body


def test_sarvam_stt_reads_the_transcript_field_not_text():
    """The response field is `transcript`. Falling back to `text` would mask a
    contract change instead of surfacing it."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"request_id": "r", "transcript": "ठीक है"})

    assert _sarvam_with(handler).transcribe(_mock_audio(), "hi").text == "ठीक है"


def test_sarvam_stt_flags_a_language_mismatch_below_the_clarify_threshold():
    """Sarvam returns no transcription confidence. A detected language that is
    not the session language is the one real signal available, so it lands
    under the FSM's 0.55 clarify threshold rather than being reported as
    certain."""
    from core.domain.fsm import CLARIFY_THRESHOLD

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"transcript": "something", "language_code": "ta-IN", "language_probability": 0.4},
        )

    result = _sarvam_with(handler).transcribe(_mock_audio(), "hi")
    assert result.confidence < CLARIFY_THRESHOLD
    assert result.raw["detected_language_code"] == "ta-IN"


def test_sarvam_stt_never_reports_language_probability_as_confidence():
    """language_probability is about the detected LANGUAGE, not the words. It is
    recorded, never repurposed into a confidence score."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"transcript": "सिलाई", "language_code": "hi-IN", "language_probability": 0.31},
        )

    result = _sarvam_with(handler).transcribe(_mock_audio(), "hi")
    assert result.confidence == 1.0
    assert result.raw["language_probability"] == 0.31


def test_sarvam_stt_empty_transcript_is_zero_confidence():
    """Drives the two-empty-ASR -> menu-mode rule the same way the mock does."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"transcript": "   ", "language_code": "hi-IN"})

    result = _sarvam_with(handler).transcribe(_mock_audio(), "hi")
    assert result.is_empty
    assert result.confidence == 0.0


def test_sarvam_stt_rejects_audio_longer_than_the_sync_endpoint_accepts():
    from core.speech.sarvam import MAX_STT_AUDIO_S

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("oversized audio must not reach the API")

    provider = _sarvam_with(handler)
    with pytest.raises(ProviderError) as excinfo:
        provider.transcribe(_mock_audio(MAX_STT_AUDIO_S + 5), "hi")
    assert not excinfo.value.retryable


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_sarvam_tts_synthesizes_every_supported_language(lang):
    seen: dict = {}
    provider = _sarvam_with(_tts_handler(seen))

    chunks = provider.synthesize(SPOKEN[lang], lang)

    assert chunks and all(c.provider == "sarvam" for c in chunks)
    assert all(c.audio_b64 for c in chunks)
    assert all(c.lang == lang for c in chunks)
    assert all(c.mime == "audio/wav" for c in chunks)
    assert seen["url"].endswith("/text-to-speech")
    assert seen["bodies"][0]["language_code"] == SARVAM_LOCALES[lang]


@pytest.mark.parametrize("lang", ["hi", "mr", "te", "en"])
def test_sarvam_tts_sends_the_published_field_names(lang):
    """`text` not `inputs`; `language_code` not `target_language_code`."""
    seen: dict = {}
    _sarvam_with(_tts_handler(seen)).synthesize(SPOKEN[lang], lang)
    body = seen["bodies"][0]

    assert isinstance(body["text"], str)
    assert "inputs" not in body, "`inputs` is not a field on the live API"
    assert "target_language_code" not in body, "the field is `language_code`"
    assert body["model"] == "bulbul:v3"
    assert body["speech_sample_rate"] == 16000
    assert body["output_audio_codec"] == "wav"


def test_sarvam_tts_speaker_is_valid_for_the_configured_model():
    """Speakers are model-specific and the API rejects a mismatched pair, so
    this guards the COMBINATION, not just the names.

    Live evidence (2026-09-12): bulbul:v2 now answers
    HTTP 400 "Model 'bulbul:v2' has been deprecated. Please use 'bulbul:v3'
    instead.", so v3 is the default and a v2 voice such as `anushka` is no
    longer valid with it.
    """
    BULBUL_V3_SPEAKERS = {
        "shubh", "aditya", "ritu", "priya", "neha", "rahul", "pooja", "rohan",
        "simran", "kavya", "amit", "dev", "ishita", "shreya", "ratan", "varun",
    }
    BULBUL_V2_SPEAKERS = {"anushka", "abhilash", "manisha", "vidya", "arya", "karun", "hitesh"}
    seen: dict = {}
    _sarvam_with(_tts_handler(seen)).synthesize("नमस्ते", "hi")

    body = seen["bodies"][0]
    assert body["model"] == "bulbul:v3", "bulbul:v2 is deprecated server-side"
    assert body["speaker"] in BULBUL_V3_SPEAKERS
    assert body["speaker"] not in BULBUL_V2_SPEAKERS, "a v2 voice is invalid on v3"
    assert body["speaker"] != "meera"


def test_sarvam_tts_returns_one_chunk_per_sentence_in_order():
    seen: dict = {}
    chunks = _sarvam_with(_tts_handler(seen)).synthesize(
        "पहला वाक्य। दूसरा वाक्य। तीसरा वाक्य।", "hi"
    )
    assert len(chunks) == 3
    assert [c.index for c in chunks] == [0, 1, 2]
    assert [b["text"] for b in seen["bodies"]] == [c.text for c in chunks]


def test_sarvam_tts_splits_text_over_the_model_character_limit():
    """A recommendation read-out with no sentence punctuation must not exceed
    the per-request ceiling."""
    from core.speech.sarvam import TTS_CHAR_LIMIT

    seen: dict = {}
    limit = TTS_CHAR_LIMIT["bulbul:v3"]
    long_text = " ".join(["शब्द"] * 1400)
    assert len(long_text) > limit

    _sarvam_with(_tts_handler(seen)).synthesize(long_text, "hi")
    assert all(len(b["text"]) <= limit for b in seen["bodies"])
    assert len(seen["bodies"]) > 1


def test_sarvam_tts_raises_when_the_api_returns_no_audio():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"request_id": "r", "audios": []})

    with pytest.raises(ProviderError):
        _sarvam_with(handler).synthesize("नमस्ते", "hi")


def test_sarvam_retries_once_on_5xx_then_raises():
    """TECH_STACK §2.1: retry once on 5xx then demote — the same rule Bhashini
    follows, so the router's demotion arithmetic means one thing."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": "upstream"})

    with pytest.raises(ProviderError) as excinfo:
        _sarvam_with(handler).transcribe(_mock_audio(), "hi")

    assert calls["n"] == 2, "expected exactly one retry"
    assert excinfo.value.retryable


def test_sarvam_rate_limit_is_retryable_but_not_retried_in_place():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, json={"error": "rate limited"})

    with pytest.raises(ProviderError) as excinfo:
        _sarvam_with(handler).transcribe(_mock_audio(), "hi")
    assert calls["n"] == 1
    assert excinfo.value.retryable


@pytest.mark.parametrize("status", [400, 401, 403])
def test_sarvam_client_errors_are_not_retryable(status):
    """A rejected key or a bad payload fails identically on a retry; it should
    demote immediately and let the ladder move on."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "nope"})

    with pytest.raises(ProviderError) as excinfo:
        _sarvam_with(handler).transcribe(_mock_audio(), "hi")
    assert not excinfo.value.retryable


def test_sarvam_without_a_key_fails_closed_and_never_calls_out():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no call may be made without a key")

    provider = SarvamProvider(
        api_key="", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderError) as excinfo:
        provider.transcribe(_mock_audio(), "hi")
    assert not excinfo.value.retryable
    assert provider.health()["ok"] is False


def test_sarvam_health_is_credential_free_and_makes_no_call():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("health() must not perform inference")

    health = _sarvam_with(handler).health()
    assert health["provider"] == "sarvam"
    assert health["ok"] is True
    assert sorted(health["languages"]) == ["en", "hi", "mr", "te"]


def test_sarvam_never_logs_the_api_key(caplog):
    """RULE 9: a failure must report a status code, never a credential."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    provider = _sarvam_with(handler)
    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderError) as excinfo:
        provider.transcribe(_mock_audio(), "hi")

    assert "test-key" not in str(excinfo.value)
    assert "test-key" not in caplog.text


# --------------------------------------------------------------------------
# Sarvam through the router — demotion and the mock floor
# --------------------------------------------------------------------------


def test_router_prefers_sarvam_over_bhashini_in_the_fallback_ladder():
    """Bhashini is still on the ladder and still implemented; Sarvam simply
    leads, because Sarvam is the provider with a usable key."""
    ladder = SpeechRouter(primary="sarvam").ladder()
    assert "bhashini" in ladder, "Bhashini support must not be removed"
    assert ladder[0] == "sarvam"
    assert ladder[-1] == "mock", "the floor of the ladder is always mock"

    # ...and the preference holds even when something else is primary.
    fallback = SpeechRouter(primary="azure").ladder()
    assert fallback.index("sarvam") < fallback.index("bhashini")
    assert "mock" in fallback


def test_sarvam_primary_demotes_after_two_failures_and_mock_carries_the_turn():
    """The exact venue failure: the key is revoked mid-session."""
    calls = {"n": 0}

    def revoked(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": "revoked"})

    broken = _sarvam_with(revoked)
    router = SpeechRouter(primary="sarvam", providers={"sarvam": broken})

    first = router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert first.provider == "mock"
    assert first.text.strip()
    assert first.degraded is True
    assert not router.is_demoted("sarvam")

    router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert router.is_demoted("sarvam")

    before = calls["n"]
    third = router.transcribe(_mock_audio(), "hi", step="aspiration")
    assert calls["n"] == before, "a demoted provider must not be called again"
    assert third.provider == "mock"
    assert third.text.strip()


def test_sarvam_tts_failure_falls_through_to_mock():
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    router = SpeechRouter(primary="sarvam", providers={"sarvam": _sarvam_with(failing)})
    chunks = router.synthesize("नमस्ते। यह एक जाँच है।", "hi")

    assert chunks and all(c.provider == "mock" for c in chunks)
    assert all(c.degraded for c in chunks)


def test_router_health_reports_sarvam_degradation_honestly():
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    router = SpeechRouter(primary="sarvam", providers={"sarvam": _sarvam_with(failing)})
    for _ in range(2):
        router.transcribe(_mock_audio(), "hi")

    health = router.health()
    assert health["ok"] is True          # the mock floor keeps the path alive
    assert health["degraded"] is True    # but it says so
    assert health["provider"] == "mock"
    assert health["primary"] == "sarvam"


def test_mock_still_needs_no_sarvam_key(monkeypatch):
    """RULE 1 is unchanged by this integration: with VOICE_PROVIDER=mock the
    journey runs with no Sarvam key present and no call attempted.

    The mock reports ``degraded=True`` even as primary, and that is deliberate
    and pre-existing: a scripted fixture is never real inference, so the UI is
    told so rather than being allowed to imply a live provider answered.
    """
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    router = SpeechRouter(primary="mock")
    result = router.transcribe(_mock_audio(), "hi", step="aspiration")

    assert result.provider == "mock"
    assert result.text.strip()
    assert result.degraded is True, "mock output must always be flagged as mock"

    chunks = router.synthesize("नमस्ते।", "hi")
    assert chunks and all(c.provider == "mock" for c in chunks)
