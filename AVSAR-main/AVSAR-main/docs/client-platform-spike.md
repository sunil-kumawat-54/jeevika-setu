# Beneficiary Client Platform Spike

## Default Decision

Use the AVSAR Next.js/PWA client. Flutter is only selected if the material-failure threshold below is reproduced or a required native capability is demonstrated. The organization, officer, and admin portal remains Next.js regardless of this decision.

## Target Matrix

Record the exact Chrome build, Android build, TalkBack result, and date for each run:

| Device | Browser/AT | Capture | Playback/SSE | Text fallback/200% | Cached shell | Result |
|---|---|---|---|---|---|---|
| Motorola Moto E13, Android 13 | Chrome stable + TalkBack | pending | pending | pending | pending | pending |
| Samsung Galaxy A04e, Android 13 | Chrome stable + TalkBack | pending | pending | pending | pending | pending |
| Android 13 emulator, 2G/3G throttle | Chrome stable + TalkBack | pending | pending | pending | pending | pending |

## Pass Checks

1. Microphone permission grant, denial, revocation, and a capture of at most 15 seconds.
2. 16 kHz mono WAV normalization, streamed SSE response, TTS playback, and autoplay recovery.
3. Text fallback in Hindi and one configured regional language, plus readable layout at 200% scaling and labelled controls.
4. Preloaded mock journey with network disabled after preparation; service-worker behavior is GET-only and never replays a conversational POST.

Phase 1 proves the cached shell and safe non-replay boundary only. It does not claim queued, synced, failed, or retry outbox behavior; that is a Phase 4 implementation gate.

## Material-Failure Threshold

Choose Flutter only for one reproducible failure affecting capture, playback, text fallback, accessibility, or the canonical mock journey on both physical devices, or for a required native capability. Any Flutter implementation must consume the same `/v1` backend contract.

## Environment Evidence

Portable checks pass on 2026-09-28: the client contract, frontend typecheck, CI grounding guard, and service-worker GET-only safety probe are green. Docker is unavailable on the Windows host and in the available WSL2 distribution, so Compose startup, `/v1/readyz`, and the live HTTP probe remain blocked until a Docker host is available. ADB and physical Android devices/emulators are also unavailable, so the three target rows above remain pending rather than being marked passed.
