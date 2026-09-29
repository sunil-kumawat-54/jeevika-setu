---
phase: 01-unified-foundation-and-migration-boundary
plan: 01
status: complete-with-environment-blocker
completed: 2026-09-28
---

# Plan 01 Summary

Established the AVSAR FastAPI runtime as the Jeevikasetu authority with a deliberate `/v1` route family. The Next.js BFF adds exactly one `/v1` prefix upstream while browser callers continue using `/api/core/*`; no provider URL is exposed to the browser.

The speech boundary is server-side and fixture-backed. `SpeechRouter` guarantees a mock floor, provider failures expose degraded metadata, and the lazy local Whisper adapter reports a typed unavailable-provider error when no approved dependency is installed. The migration map and Phase 1 contract tests document KaushalVani as reference-only and preserve canonical ownership, provenance, synthetic state, decimal NSQF values, and QP versions.

## Verification

- `python -m pytest -q services/core/tests/test_gate_phase1_contracts.py -x` passed.
- `python -m pytest -q services/core/tests/test_gate5_speech.py services/core/tests/test_gate_phase1_contracts.py -x` passed: 136 passed, 3 skipped.
- `python -m pytest -q services/core/tests/test_gate0_infra.py -x` passed: 40 passed, 3 skipped.
- `.planning/source-snapshot-manifest.json` covers both untracked reference trees.
- Docker and GNU Make are unavailable on this Windows host; Compose startup/readiness/seed acceptance remains blocked for CI or a Docker-capable host.

No commit was created because the application trees are untracked reference sources in the outer workspace and the required local execution tools for the runtime gate are unavailable.
