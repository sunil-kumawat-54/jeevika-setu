"""Drill scenario 1 — the whole journey with no network at all.

Called by ``scripts/kill_service_drill.sh``. Every outbound HTTP transport is
monkeypatched to raise before anything runs, so a passing run is proof that the
beneficiary path made no network call — not merely that it happened not to need
one this time.

``--no-db`` additionally skips the database, so the same script can run inside
``docker run --network none`` where Postgres is unreachable by construction.
That variant proves the speech and verbalizer layers alone are offline-clean.
"""

from __future__ import annotations

import argparse
import base64
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))


def cut_the_wire() -> None:
    """Make any outbound HTTP call raise loudly."""
    import socket

    import httpx

    def refuse(*args, **kwargs):
        raise AssertionError("NETWORK CALL ATTEMPTED during the offline drill")

    httpx.Client.send = refuse
    httpx.Client.request = refuse
    httpx.AsyncClient.send = refuse
    httpx.AsyncClient.request = refuse
    socket.create_connection = refuse


JOURNEY = [
    "language_select",
    "consent",
    "profile_district",
    "profile_age_band",
    "profile_gender",
    "profile_education",
    "profile_current_work",
    "aspiration",
    "confirm_intent",
    "recommendation",
    "summary",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-db", action="store_true", help="skip the database-backed steps")
    args = parser.parse_args()

    cut_the_wire()

    from core.speech.mock import _wav_bytes
    from core.speech.router import SpeechRouter

    audio = base64.b64encode(_wav_bytes(1.0)).decode("ascii")
    router = SpeechRouter(primary="mock")

    # ---- speech, every step, every language ---------------------------
    spoken_steps = 0
    for lang in ("hi", "mr", "te", "en"):
        for step in JOURNEY:
            asr = router.transcribe(audio, lang, step=step)
            if not asr.text.strip():
                print(f"FAIL: {lang}/{step} produced no transcript offline")
                return 1
            tts = router.synthesize(asr.text, lang, step=step)
            if not tts or not tts[0].audio_b64:
                print(f"FAIL: {lang}/{step} produced no audio offline")
                return 1
            spoken_steps += 1
    print(f"offline speech: {spoken_steps} turns across 4 languages, mock provider, no network")

    # ---- verbalizer (template rung needs no LLM and no network) --------
    from core.llm import templates
    from core.llm.guardrails import check_numerals, tool_payload_for_items

    sample = [
        {
            "rank": 1,
            "course_id": 1,
            "qp_code": "AP/Q01868",
            "name": "Self Employed Tailor",
            "nsqf_level": 2.5,
            "nsqf_level_spoken": 2,
            "hours": 300,
            "sector": "Apparel",
            "seats_in_district": 40,
            "why": "offline drill",
            "next_step": "",
            "assistance": {"loan_support": "up to Rs 50,000 or 50% of project cost"},
        }
    ]
    text = templates.verbalize_recommendation(sample, "hi")
    report = check_numerals(text, tool_payload_for_items(sample))
    if not text or not report.grounded:
        print(f"FAIL: offline verbalizer produced ungrounded text: {report.explain()}")
        return 1
    print(f"offline verbalizer: template rung produced {len(text)} chars, grounded={report.grounded}")

    if args.no_db:
        print("OFFLINE DRILL OK (speech + verbalizer, no database, no network interface)")
        return 0

    # ---- full recommendation + FSM against the local database ----------
    from core.db import SessionLocal
    from core.domain.fsm import FsmState, Step, TurnInput, advance
    from core.domain.recommender import Intent, Profile, recommend
    from core.llm.verbalizer import verbalize

    db = SessionLocal()
    try:
        state = FsmState(step=Step.consent)
        state = advance(state, TurnInput(choice="yes")).state
        for value in ["270481", "18_30", "female", "8th_10th", "unemployed"]:
            state = advance(state, TurnInput(choice=value)).state
        if state.step != Step.aspiration:
            print(f"FAIL: FSM reached {state.step} instead of aspiration")
            return 1

        transcript = router.transcribe(audio, "hi", step="aspiration")
        result = recommend(
            db,
            Profile(
                district_code="270481",
                gender="female",
                edu_level="8th_10th",
                current_work="unemployed",
                lang="hi",
            ),
            Intent(concept_text=transcript.text),
        )
        if not result.items:
            print(f"FAIL: no recommendation offline (refusal={result.refusal})")
            return 1

        spoken = verbalize(result.items, "hi", db=db)
        grounded = check_numerals(spoken.text, tool_payload_for_items(result.items))
        if not grounded.grounded:
            print(f"FAIL: offline recommendation was ungrounded: {grounded.explain()}")
            return 1

        print(
            f"offline recommendation: {result.items[0]['qp_code']} "
            f"{result.items[0]['name']!r} via {spoken.mode}, grounded={grounded.grounded}"
        )
    finally:
        db.close()

    print("OFFLINE DRILL OK — full journey completed with every network call blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
