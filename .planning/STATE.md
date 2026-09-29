# Jeevikasetu State

## Project Reference

**Core value**: A low-literacy beneficiary can speak in a local language and receive a trustworthy, explainable, locally relevant path from existing skills to a better livelihood, even when providers or connectivity fail.

**Current focus**: Phase 2 is complete. The canonical schema, deterministic loaders, grounded retrieval, spatial read path, and Docker/PostGIS runtime acceptance are verified.

**Scope**: The PRD's 39 v1 requirements across voice, conversation/profile, canonical data, grounded recommendations, beneficiary and organization experiences, outcomes, security, and offline demo operations. WhatsApp/IVR, live government APIs, premium analytics, extra language expansion, and advanced assessments are deferred to v2.

## Current Position

- **Phase**: 2 of 5
- **Plan**: Phase 2 complete; Phase 3 planning next
- **Status**: Canonical migration, ORM, provenance, PostGIS schema, deterministic snapshots, natural-key loader reports, grounded retrieval, canonical authorization, focused tests, live Docker/PostGIS checks, and the 50-session grounding verifier all pass.
- **Progress**: [##########] 100%
- **Last activity**: Started the Jeevikasetu stack, migrated and seeded PostgreSQL/PostGIS, fixed the Alembic revision-length defect, passed all Phase 2 database-backed tests, and passed the 50-session grounding and live client probes.

## Decisions

| Decision | Status | Rationale |
|---|---|---|
| AVSAR FastAPI is the initial runtime and public business-logic authority | Accepted for planning | It has the strongest mock-first, grounded, offline-drill, seed, migration, latency, and dashboard evidence. |
| One canonical PostgreSQL migration lineage | Accepted for planning | Avoids duplicate profile, recommendation, auth, and provenance truths from the two repositories. |
| KaushalVani is selectively integrated behind unified contracts | Accepted for planning | Its roadmap, outcome, opportunity, language, accessibility, and persona concepts are useful, but its runtime fallbacks and second services conflict with grounding and simplicity. |
| Facts are database/tool output; generated language only verbalizes them | Accepted for planning | Prevents invented QP codes, qualifications, distances, centres, numbers, and opportunities. |
| Mock mode is a first-class acceptance path | Accepted for planning | The judging journey must work with zero API keys and no internet after preparation. |
| Flutter vs Next.js/PWA | Spike in Phase 1; default PWA | Existing AVSAR PWA is the smallest evidence-based path. Target-device testing can reverse the choice only for a material browser/audio or native-capability failure; the portal remains Next.js. |
| PostGIS centre geometry and privacy-safe origin | Required Phase 2 decision | Existing AVSAR aggregates and KaushalVani application Haversine logic do not prove nearby-centre claims. |

## Accumulated Context

### Constraints

- Do not modify application source files as part of planning.
- Do not run AVSAR and KaushalVani as parallel production authorities.
- Preserve decimal NSQF levels, source/version/freshness metadata, and `synthetic` through derived records and exports.
- Never store raw audio by default after transcription; enforce consent before durable beneficiary data.
- Separate local-stack mock offline judging from browser-disconnected continuity; service-worker caching alone is insufficient.

### Risks To Carry Forward

- Target Android models, browsers, screen readers, and exact disconnected scope are still unspecified.
- Live Bhashini access/licensing and approved fallback provider are not confirmed.
- Verified centre coordinates and freshness policy need implementation evidence.
- Organization candidate visibility and contact policy needs a privacy decision before implementation.

## Next Action

Next: plan and execute Phase 3 voice, conversation, and profile journey work. Keep the verified Docker stack available for integration checks. The active beneficiary PWA restores a short-lived session snapshot without replaying POST requests.

## Session Continuity

Planning artifacts written:

- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

Planning documents are committed in `5a0fc06` (`chore: initialize Jeevikasetu planning`).
