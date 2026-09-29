"""Drill scenario 3 — a provider whose key has been revoked.

Called by ``scripts/kill_service_drill.sh``. Simulates the venue failure
PLAN.md §11 risk R2 describes ("Bhashini keys throttled/rate-limited at venue")
by pointing the Bhashini adapter at a server that answers 401 to everything,
then asserting the router's documented behaviour:

* the failing provider is tried,
* after ``PROVIDER_DEMOTE_AFTER`` failures it is demoted and not called again,
* the mock rung carries the turn so the beneficiary never sees a dead screen,
* the result is flagged ``degraded`` so the UI can say so honestly.
"""

from __future__ import annotations

import base64
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

import httpx  # noqa: E402
from core.speech.bhashini import BhashiniProvider  # noqa: E402
from core.speech.mock import _wav_bytes  # noqa: E402
from core.speech.router import SpeechRouter  # noqa: E402

AUDIO = base64.b64encode(_wav_bytes(1.0)).decode("ascii")


def revoked_key_transport(request: httpx.Request) -> httpx.Response:
    """Every call answers 401, exactly as a revoked ULCA key would."""
    return httpx.Response(401, json={"message": "Invalid or revoked API key"})


def main() -> int:
    calls = {"n": 0}

    def counting(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return revoked_key_transport(request)

    broken = BhashiniProvider(
        user_id="demo-user",
        api_key="revoked-key",
        client=httpx.Client(transport=httpx.MockTransport(counting)),
    )
    router = SpeechRouter(primary="bhashini", providers={"bhashini": broken})

    # --- turn 1: provider fails, mock carries it
    first = router.transcribe(AUDIO, "hi", step="aspiration")
    if not first.text.strip():
        print("FAIL: no transcript after the primary provider failed")
        return 1
    if first.provider != "mock":
        print(f"FAIL: expected the mock rung to answer, got {first.provider}")
        return 1
    if not first.degraded:
        print("FAIL: a fallback answer was not flagged degraded")
        return 1
    print(f"turn 1: bhashini failed -> {first.provider} answered, degraded={first.degraded}")

    if router.is_demoted("bhashini"):
        print("FAIL: provider demoted after a single failure (PROVIDER_DEMOTE_AFTER=2)")
        return 1

    # --- turn 2: second failure trips demotion
    router.transcribe(AUDIO, "hi", step="aspiration")
    if not router.is_demoted("bhashini"):
        print("FAIL: provider was not demoted after two failures")
        return 1
    print(f"turn 2: bhashini demoted after {router.demote_after} failures")

    # --- turn 3: a demoted provider must not be called again
    before = calls["n"]
    third = router.transcribe(AUDIO, "hi", step="aspiration")
    if calls["n"] != before:
        print(f"FAIL: demoted provider was called again ({calls['n'] - before} extra calls)")
        return 1
    if not third.text.strip():
        print("FAIL: no transcript after demotion")
        return 1
    print(f"turn 3: demoted provider not contacted; {third.provider} served the turn")

    # --- TTS must fall through too
    chunks = router.synthesize("नमस्ते। यह एक जाँच है।", "hi")
    if not chunks or not all(c.provider == "mock" for c in chunks):
        print("FAIL: TTS did not fall through to the mock rung")
        return 1
    print(f"tts: {len(chunks)} chunks from {chunks[0].provider}, degraded={chunks[0].degraded}")

    # --- health must report the degradation honestly
    health = router.health()
    if not health["ok"]:
        print("FAIL: the voice path reported unhealthy even though mock is available")
        return 1
    if not health["degraded"]:
        print("FAIL: health did not report degradation")
        return 1
    print(f"health: ok={health['ok']} degraded={health['degraded']} active={health['provider']}")

    print("PROVIDER DRILL OK — revoked key demoted, mock carried the session, degradation flagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
