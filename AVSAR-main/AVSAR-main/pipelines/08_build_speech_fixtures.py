"""Build the mock-provider speech fixtures.

ARCHITECTURE.md section 6: *"Mock provider: replays fixture WAVs/transcripts
from ``seeds/fixtures/`` keyed by dialogue step — full flow works
airplane-mode."*

The fixtures are derived from ``data/prompts/dialogue.<lang>.json`` so the
scripted answers always match the questions the UI actually asks — a fixture
that drifts from the dialogue would make the offline demo incoherent.

Each step carries a default transcript plus the *variants* the FSM must be able
to handle:

``empty``           silence -> two in a row switches to menu mode (PLAN §4.1)
``low_confidence``  below threshold -> clarify-once branch
``unknown``         an aspiration outside the crosswalk -> refusal / handoff

Also writes a small set of 16 kHz mono WAVs so the audio transport is exercised
offline. They are generated tones, not recorded speech, and both this file and
the UI say so.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "services"))

from pipelines.common import SEEDS, PipelineResult, Provenance, write_seed  # noqa: E402

log = logging.getLogger("08_fixtures")

NAME = "08_build_speech_fixtures"
PROMPTS = REPO / "data" / "prompts"
FIXTURES = SEEDS / "fixtures"
ASR_DIR = FIXTURES / "asr"
WAV_DIR = FIXTURES / "wav"

LANGS = ("hi", "mr", "te", "en")

#: The spoken answer a beneficiary gives at each dialogue step, per language.
#: District/aspiration answers are the ones that really matter — the rest are
#: usually tapped, but a fixture exists so every step is voice-completable.
SCRIPT: dict[str, dict[str, str]] = {
    "language_select": {
        "hi": "हिंदी", "mr": "मराठी", "te": "తెలుగు", "en": "English",
    },
    "consent": {
        "hi": "हाँ, आगे बढ़ें", "mr": "होय, पुढे चला",
        "te": "అవును, ముందుకు వెళ్లండి", "en": "Yes, please continue",
    },
    "profile_district": {
        "hi": "लातूर", "mr": "लातूर", "te": "నల్గొండ", "en": "Latur",
    },
    "profile_age_band": {
        "hi": "अठारह से तीस साल", "mr": "अठरा ते तीस वर्षे",
        "te": "పద్దెనిమిది నుండి ముప్పై", "en": "eighteen to thirty",
    },
    "profile_gender": {
        "hi": "महिला", "mr": "महिला", "te": "మహిళ", "en": "female",
    },
    "profile_education": {
        "hi": "आठवीं से दसवीं तक", "mr": "आठवी ते दहावी",
        "te": "ఎనిమిది నుండి పది", "en": "eighth to tenth",
    },
    "profile_current_work": {
        "hi": "अभी कोई काम नहीं है", "mr": "सध्या काम नाही",
        "te": "ప్రస్తుతం పని లేదు", "en": "currently no work",
    },
    "aspiration": {
        "hi": "मैं सिलाई का काम सीखना चाहती हूँ",
        "mr": "मला शिवणकाम शिकायचे आहे",
        "te": "నాకు కుట్టు పని నేర్చుకోవాలని ఉంది",
        "en": "I want to learn tailoring",
    },
    "clarify": {
        "hi": "सिलाई", "mr": "शिवणकाम", "te": "కుట్టు పని", "en": "tailoring",
    },
    "confirm_intent": {
        "hi": "हाँ, सही है", "mr": "होय, बरोबर आहे",
        "te": "అవును, సరైనదే", "en": "yes that is right",
    },
    "recommendation": {
        "hi": "फिर सुनें", "mr": "पुन्हा ऐका",
        "te": "మళ్లీ వినండి", "en": "play it again",
    },
    "summary": {
        "hi": "खत्म", "mr": "संपले", "te": "ముగించు", "en": "finish",
    },
}

#: An aspiration deliberately outside the curated crosswalk, used by the forced
#: hallucination test (Gate 7) and the refusal path.
UNKNOWN_ASPIRATION = {
    "hi": "मुझे अंतरिक्ष यात्री बनना है",
    "mr": "मला अंतराळवीर व्हायचे आहe",
    "te": "నేను వ్యోమగామి కావాలనుకుంటున్నాను",
    "en": "I want to become an astronaut",
}

#: A poultry aspiration — recognised concept, declared crosswalk gap.
GAP_ASPIRATION = {
    "hi": "मुर्गी पालन शुरू करना है",
    "mr": "कुक्कुटपालन सुरू करायचे आहे",
    "te": "కోళ్ల పెంపకం ప్రారంభించాలి",
    "en": "I want to start poultry farming",
}

#: Confidence levels. research.md §5.1 measures ~26.8% WER on rural telephony
#: Hindi, so the default is deliberately not 0.99 — the confidence pill must
#: show something realistic during the demo.
DEFAULT_CONFIDENCE = 0.86
LOW_CONFIDENCE = 0.41


def build_language(lang: str) -> dict:
    prompts_path = PROMPTS / f"dialogue.{lang}.json"
    prompts = json.loads(prompts_path.read_text(encoding="utf-8")) if prompts_path.exists() else {}
    known_steps = set(prompts.get("steps", {}))

    steps: dict[str, dict] = {}
    for step, per_lang in SCRIPT.items():
        text = per_lang.get(lang, per_lang["en"])
        entry = {
            "text": text,
            "confidence": DEFAULT_CONFIDENCE,
            "variants": {
                # Silence. Two of these in a row must switch the FSM to menu mode.
                "empty": {"text": "", "confidence": 0.0},
                # Below the clarify threshold -> the clarify-once branch.
                "low_confidence": {"text": text, "confidence": LOW_CONFIDENCE},
            },
        }
        if step == "aspiration":
            entry["variants"]["unknown"] = {
                "text": UNKNOWN_ASPIRATION.get(lang, UNKNOWN_ASPIRATION["en"]),
                "confidence": DEFAULT_CONFIDENCE,
            }
            entry["variants"]["gap"] = {
                "text": GAP_ASPIRATION.get(lang, GAP_ASPIRATION["en"]),
                "confidence": DEFAULT_CONFIDENCE,
            }
        steps[step] = entry

    unmatched = sorted(known_steps - set(steps) - {"menu_mode", "end"})
    return {
        "lang": lang,
        "note": (
            "Scripted ASR fixtures for VOICE_PROVIDER=mock. Transcripts are the "
            "answers a beneficiary gives at each dialogue step; no inference is "
            "performed and no network or credential is required."
        ),
        "clarify_threshold": 0.55,
        "steps": steps,
        "dialogue_steps_without_fixture": unmatched,
    }


def run() -> PipelineResult:
    from core.speech.mock import _wav_bytes

    ASR_DIR.mkdir(parents=True, exist_ok=True)
    WAV_DIR.mkdir(parents=True, exist_ok=True)

    prov = Provenance(
        pipeline=NAME,
        source_url="derived from data/prompts/dialogue.*.json",
        mode="synthetic",
        synthetic=True,
        fallback_note=(
            "Mock speech fixtures. Transcripts are scripted, not recognised; the WAVs "
            "are generated 16 kHz mono tones, not recorded human speech. They exist so "
            "the full voice path runs offline with zero credentials (RULE 1). Real audio "
            "comes from a real provider via `make mock-off`."
        ),
    )

    records = []
    for lang in LANGS:
        payload = build_language(lang)
        path = ASR_DIR / f"{lang}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        records.append({"lang": lang, "steps": sorted(payload["steps"]), "file": path.name})
        log.info("wrote %s (%d steps)", path.name, len(payload["steps"]))

    # A few reference WAVs so the audio contract is inspectable without running
    # the service. Deterministic, so `make ingest` stays idempotent.
    for seconds in (0.5, 1.5, 3.0):
        wav = WAV_DIR / f"tone_{str(seconds).replace('.', '_')}s.wav"
        wav.write_bytes(_wav_bytes(seconds))

    write_seed(FIXTURES / "manifest.json", records, prov)
    return PipelineResult(name=NAME, seed_path=FIXTURES / "manifest.json", provenance=prov)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
