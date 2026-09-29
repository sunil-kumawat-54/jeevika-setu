"""scripts/verify_sarvam.py — the LIVE Sarvam integration test.

The unit tests in ``services/core/tests/test_gate5_speech.py`` prove the adapter
*sends* the published contract, using a mocked transport. They cannot prove
Sarvam *accepts* it. Only this script can, and only with a real key.

It exercises, against the real API:

  * STT in hi, mr, te, en   — using the TTS audio as the input, so the round
    trip is genuine: AVSAR speaks a sentence, Sarvam hears it back.
  * TTS in hi, mr, te, en   — and checks the returned bytes are a playable
    16 kHz mono WAV, the format the PWA and the mock both use.
  * provider demotion       — a deliberately revoked key must demote after two
    failures and hand the turn to mock.
  * the mock floor          — unchanged and key-free.

Exit codes:
    0   every live check passed
    1   a live check failed
    2   no SARVAM_API_KEY — nothing live was verified (NOT a pass)

    python scripts/verify_sarvam.py
    python scripts/verify_sarvam.py --langs hi,en
    python scripts/verify_sarvam.py --keep-audio out/

Cost: one TTS + one STT call per language. At the published rates that is a
fraction of a rupee for a full run (research.md section 5.3), but it IS a paid
call — the script says so before it makes any.
"""

from __future__ import annotations

import argparse
import base64
import io
import os
import pathlib
import struct
import sys
import time
import wave

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

#: Short, natural sentences — one per supported language. Kept simple so a
#: transcription mismatch means a real problem rather than a hard sentence.
PHRASES = {
    "hi": "मुझे सिलाई का काम सीखना है",
    "mr": "मला शिवणकामाचे प्रशिक्षण घ्यायचे आहे",
    "te": "నాకు కుట్టు పని నేర్చుకోవాలి",
    "en": "I want to learn tailoring work",
}

PASS = "PASS"
FAIL = "FAIL"


def wav_facts(raw: bytes) -> dict:
    """Parse a WAV header so 'it returned audio' is a checkable claim."""
    with wave.open(io.BytesIO(raw), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        return {
            "channels": handle.getnchannels(),
            "sample_rate": rate,
            "sample_width": handle.getsampwidth(),
            "frames": frames,
            "seconds": round(frames / rate, 2) if rate else 0.0,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="live Sarvam integration test")
    parser.add_argument("--langs", default="hi,mr,te,en")
    parser.add_argument("--keep-audio", default=None, help="directory to write the WAVs to")
    args = parser.parse_args()
    langs = [x.strip() for x in args.langs.split(",") if x.strip()]

    from core.config import settings
    from core.speech.base import ProviderError
    from core.speech.mock import _wav_bytes
    from core.speech.router import SpeechRouter
    from core.speech.sarvam import SarvamProvider

    print("=" * 72)
    print("AVSAR — live Sarvam integration test")
    print(f"  base         : {settings.sarvam_base}")
    print(f"  stt          : {settings.sarvam_stt_model} (mode={settings.sarvam_stt_mode})")
    print(f"  tts          : {settings.sarvam_tts_model} speaker={settings.sarvam_tts_speaker}")
    print(f"  languages    : {', '.join(langs)}")

    if not settings.sarvam_api_key:
        print()
        print("  SARVAM_API_KEY is not set.")
        print("  NOTHING LIVE WAS VERIFIED. This is not a pass.")
        print()
        print("  To run this test for real:")
        print("    1. put a key in .env as SARVAM_API_KEY=...")
        print("    2. make up            # so the container picks it up")
        print("    3. make verify-sarvam")
        print("=" * 72)
        return 2

    print("  NOTE: this makes real, billable calls to Sarvam.")
    print("=" * 72)

    provider = SarvamProvider()
    failures: list[str] = []
    out_dir = pathlib.Path(args.keep_audio) if args.keep_audio else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    # ---- TTS, then STT on that same audio: a genuine round trip -----------
    for lang in langs:
        phrase = PHRASES.get(lang)
        if phrase is None:
            failures.append(f"{lang}: no phrase defined")
            continue

        print(f"\n[{lang}] TTS  {phrase!r}")
        try:
            started = time.monotonic()
            chunks = provider.synthesize(phrase, lang)
            tts_ms = (time.monotonic() - started) * 1000.0
        except ProviderError as exc:
            print(f"  {FAIL}  TTS raised: {exc}")
            failures.append(f"{lang} TTS: {exc}")
            continue

        if not chunks or not chunks[0].audio_b64:
            print(f"  {FAIL}  TTS returned no audio")
            failures.append(f"{lang} TTS: no audio")
            continue

        audio = base64.b64decode(chunks[0].audio_b64)
        try:
            facts = wav_facts(audio)
        except (wave.Error, EOFError, struct.error) as exc:
            print(f"  {FAIL}  TTS audio is not a readable WAV: {exc}")
            failures.append(f"{lang} TTS: unreadable WAV")
            continue

        ok_format = facts["channels"] == 1 and facts["sample_rate"] == 16_000
        print(
            f"  {PASS if ok_format else FAIL}  {len(audio)} bytes, "
            f"{facts['sample_rate']} Hz, {facts['channels']} ch, "
            f"{facts['seconds']}s, {tts_ms:.0f} ms, provider={chunks[0].provider}"
        )
        if not ok_format:
            failures.append(
                f"{lang} TTS: expected 16 kHz mono, got "
                f"{facts['sample_rate']} Hz / {facts['channels']} ch"
            )
        if out_dir:
            (out_dir / f"sarvam-tts-{lang}.wav").write_bytes(audio)

        print(f"[{lang}] STT  (transcribing the audio Sarvam just produced)")
        try:
            result = provider.transcribe(chunks[0].audio_b64, lang)
        except ProviderError as exc:
            print(f"  {FAIL}  STT raised: {exc}")
            failures.append(f"{lang} STT: {exc}")
            continue

        heard = result.text.strip()
        if not heard:
            print(f"  {FAIL}  STT returned an empty transcript")
            failures.append(f"{lang} STT: empty transcript")
            continue

        detected = result.raw.get("detected_language_code")
        print(
            f"  {PASS}  {heard!r}  conf={result.confidence} "
            f"detected={detected} {result.latency_ms:.0f} ms"
        )
        # A round trip through synthesis and recognition will not be
        # character-identical, so this asserts the language came back right and
        # something was actually heard — not string equality.
        if detected and not detected.startswith(lang):
            failures.append(f"{lang} STT: detected {detected}")

    # ---- demotion, with a key that is real in shape but wrong -------------
    print("\n[demotion] revoked key must demote after 2 failures, mock carries the turn")
    revoked = SarvamProvider(api_key="sk-revoked-not-a-real-key")
    router = SpeechRouter(primary="sarvam", providers={"sarvam": revoked})
    audio_b64 = base64.b64encode(_wav_bytes(1.0)).decode("ascii")

    first = router.transcribe(audio_b64, "hi", step="aspiration")
    demoted_early = router.is_demoted("sarvam")
    router.transcribe(audio_b64, "hi", step="aspiration")
    demoted = router.is_demoted("sarvam")
    third = router.transcribe(audio_b64, "hi", step="aspiration")

    ok_demote = (
        first.provider == "mock"
        and first.degraded
        and not demoted_early
        and demoted
        and third.provider == "mock"
        and third.text.strip()
    )
    print(
        f"  {PASS if ok_demote else FAIL}  turn1={first.provider} "
        f"demoted_after_1={demoted_early} demoted_after_2={demoted} "
        f"turn3={third.provider}"
    )
    if not ok_demote:
        failures.append("demotion did not behave as designed")

    # ---- the mock floor, untouched by any of this -------------------------
    print("\n[mock] RULE 1: mock primary answers with no key and no call")
    saved = os.environ.pop("SARVAM_API_KEY", None)
    try:
        mock_router = SpeechRouter(primary="mock")
        mock_result = mock_router.transcribe(audio_b64, "hi", step="aspiration")
        mock_tts = mock_router.synthesize("नमस्ते।", "hi")
    finally:
        if saved is not None:
            os.environ["SARVAM_API_KEY"] = saved

    ok_mock = (
        mock_result.provider == "mock"
        and bool(mock_result.text.strip())
        and bool(mock_tts)
        and all(c.provider == "mock" for c in mock_tts)
    )
    print(f"  {PASS if ok_mock else FAIL}  asr={mock_result.provider} tts_chunks={len(mock_tts)}")
    if not ok_mock:
        failures.append("mock floor did not answer")

    print("\n" + "=" * 72)
    if failures:
        print(f"  RESULT: FAIL — {len(failures)} check(s) failed")
        for line in failures:
            print(f"    - {line}")
        print("=" * 72)
        return 1
    print("  RESULT: PASS — live Sarvam STT + TTS verified in "
          f"{', '.join(langs)}, demotion and mock floor intact")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
