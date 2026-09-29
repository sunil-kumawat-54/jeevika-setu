---
phase: 01-unified-foundation-and-migration-boundary
plan: 03
status: complete-with-deferred-environment-evidence
completed: 2026-09-29
---

# Plan 03 Summary

Kept the beneficiary client as the AVSAR Next.js/PWA implementation. The PWA uses the canonical `/v1` backend contract through the Next BFF, while the organization, officer, and admin portal remain Next.js. No Flutter runtime was added and the backend/provider/data contracts remain reversible.

The migration map, client platform spike protocol, versioned client contract probe, and GET-only service-worker safety boundary are in place. Phase 1 does not claim an IndexedDB outbox or conversational POST replay safety beyond the tested GET-only worker behavior; queued/synced/failed/retry draft continuity remains a Phase 4 gate.

## Verification

- `python -m pytest -q services/core/tests/test_gate_phase1_contracts.py -x` passed.
- `python scripts/verify_service_worker_safety.py` passed.
- `python scripts/assert_ci_grounding.py .github/workflows/ci.yml` passed.
- Flutter SDK and Android tooling are installed and healthy, but no physical Android device or emulator is connected.
- Docker remains unavailable, so the live client probe and Compose-backed mock journey remain deferred to a Docker-capable host.

## Decision

**Next.js/PWA selected.** This is the default and evidence-supported path. Flutter is not required unless later target-device testing reproduces a material browser/audio/accessibility failure or a native capability becomes mandatory. The decision does not alter the canonical `/v1` backend contract.

## Deferred evidence

The named Moto E13, Galaxy A04e, and Android 13 emulator matrix remains pending. This is an environment evidence gap, not an implementation gap. It must be completed before claiming full NFR-01 acceptance.
