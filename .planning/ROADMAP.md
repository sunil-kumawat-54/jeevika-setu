# Roadmap: Jeevikasetu

## Milestone

## v1.0 - Grounded Livelihood Bridge

Five demoable phases combine AVSAR's proven runtime, data, grounding, offline, and dashboard assets with selected KaushalVani journey, opportunity, accessibility, and outcome concepts. The source repositories remain reference material during migration; the active product has one FastAPI backend, one canonical PostgreSQL schema, and one public `/v1` contract.

## Phases

- [x] **Phase 1: Unified Foundation And Migration Boundary** - Establish one runnable authority, contracts, CI, mock providers, and the client decision gate. (Implementation complete; Docker/device evidence deferred.)
- [x] **Phase 2: Canonical Data, Knowledge And Grounded Backend** - Reconcile schemas and build provenance-aware NSQF, opportunity, vector, and spatial data. (Complete; live Docker/PostGIS and grounding gates passed 2026-09-29.)
- [ ] **Phase 3: Voice, Conversation And Profile Journey** - Deliver consented multilingual turns, profile extraction, facilitator mode, and resilient voice/text interaction.
- [ ] **Phase 4: Beneficiary And Organization Experiences** - Deliver grounded pathways, beneficiary continuity, organization workflows, officer views, and exports.
- [ ] **Phase 5: Outcomes, Security And Demo Readiness** - Close the outcome loop and prove privacy, resilience, accessibility, performance, and the full offline demo.

## Phase Details

### Phase 1: Unified Foundation And Migration Boundary

**Goal**: Developers and judges can start one coherent Jeevikasetu stack, while every later feature has a stable contract and an explicit migration boundary.

**Depends on**: Nothing (first phase)

**Requirements**: VOI-03, NFR-01, NFR-02

**Integration focus**: Adopt AVSAR FastAPI, Compose, Next.js shell, provider interfaces, health/readiness, Make targets, and CI as the baseline. Map KaushalVani profile, roadmap, opportunity, and outcome concepts to canonical IDs without running its Node/Express or standalone AI services. Publish the endpoint, role, consent, provenance, synthetic-data, and source-field mapping.

**Flutter vs Next.js/PWA spike**: Resolve D-01 here against target-device microphone permission, capture/playback, WebSocket behavior, text fallback, 200% scaling, preloaded offline journey, and draft outbox checks. The evidence-based smallest path is AVSAR Next.js/PWA for the first beneficiary journey; switch to Flutter only if device testing shows a material browser/audio failure or requires native capabilities. The organization/officer/admin portal remains Next.js.

**Verification criteria**:

1. Clean Compose startup exposes one API, one web client, one PostgreSQL/pgvector/PostGIS-capable database, and one Redis path with health/readiness passing.
2. A mock provider contract can be selected by environment, returns explicit provider/degraded metadata, and keeps credentials server-side.
3. CI runs the initial lint/test/grounding commands, and no active route depends on KaushalVani's duplicate runtime.
4. The client spike records target-device evidence and selects PWA or Flutter without changing the backend contract.

**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Freeze the versioned AVSAR authority, provider contract, and migration boundary
- [ ] 01-02-PLAN.md — Consolidate Compose, Make, env, and pull-request CI verification
- [ ] 01-03-PLAN.md — Run the KaushalVani mapping and Flutter-versus-Next.js/PWA client gate

### Phase 2: Canonical Data, Knowledge And Grounded Backend

**Goal**: Every recommendation-ready fact comes from one searchable, spatially aware, provenance-labelled and repeatably loaded data authority.

**Depends on**: Phase 1

**Requirements**: KB-01, KB-02, KB-03, KB-04

**Integration focus**: Retain AVSAR Alembic, seed envelopes, crosswalk, loader, ingestion report, pgvector retrieval, and decimal NSQF behavior. Reconcile KaushalVani's qualification, centre, employment, enterprise, roadmap, and outcome vocabulary into the canonical model. Add PostGIS geometry, verified centre metadata, privacy-safe coarse beneficiary origin, source/version/freshness fields, and synthetic propagation. Semantic retrieval remains candidate generation; database rows authorize facts.

**Verification criteria**:

1. An empty database applies one repeatable migration head with vector, text-search, and PostGIS extensions plus required indexes and constraints.
2. Seed and ingestion run twice with stable natural-key counts and fingerprints, and reports source, verification, synthetic mode, and failures.
3. A half-level NSQF qualification, QP version, skill embedding, verified centre geometry, and opportunity can be retrieved from the canonical database without integer coercion.
4. Database-side distance queries sort centres, exclude out-of-radius results, and honestly handle missing or stale coordinates.

**Plans:** 3 plans

Plans:
- [x] 02-01-PLAN.md — Establish the canonical migration, provenance, qualification identity, and PostGIS schema
- [x] 02-02-PLAN.md — Make snapshots and loaders deterministic, idempotent, and source-honest
- [x] 02-03-PLAN.md — Connect hybrid retrieval and database-side spatial facts to the grounded backend

### Phase 3: Voice, Conversation And Profile Journey

**Goal**: A beneficiary or facilitator can complete a consented multilingual intake through voice or text and leave with a confirmed, editable profile even when a provider degrades.

**Depends on**: Phase 2

**Requirements**: VOI-01, VOI-02, VOI-04, VOI-05, CNV-01, CNV-02, CNV-03, CNV-04, PRF-01, PRF-02

**Integration focus**: Preserve AVSAR sessions, WebSocket turn protocol, mock fixtures, speech router, replay/audio normalization, confidence confirmation, and failure ladder. Port KaushalVani's multilingual livelihood vocabulary, Sita scenario semantics, and accessibility intent behind the canonical contracts. Keep text fallback prominent and label simulated audio/transcripts honestly. Do not blindly replay conversational POSTs offline.

**Verification criteria**:

1. Hindi, English, and the configured regional language can be selected or detected, and each supported turn has a text fallback plus replayable audio when available.
2. Consent is captured before durable storage; the conversation asks only for missing slots and persists per-field confidence with confirmation for low-confidence values.
3. Sita and a facilitator-created shared-device profile complete the five-slot mock flow, including an open knowledge-base question, with identities separated.
4. Latency output reports STT, retrieval/LLM, and TTS p50/p95 and shows the p95 target status; provider failure produces a clear degraded or text-only response.

**Plans**: TBD
**UI hint**: yes

### Phase 4: Beneficiary And Organization Experiences

**Goal**: People can act on grounded pathways and real local opportunities, while organizations and officers can use privacy-aware matching and operational views through the same backend.

**Depends on**: Phase 3

**Requirements**: GAP-01, REC-01, REC-02, REC-03, REC-04, APP-01, APP-02, APP-03, APP-04, ADM-01, ADM-02, ADM-03, ADM-04, ADM-05

**Integration focus**: Use AVSAR deterministic crosswalk, retrieval, recommender, guarded verbalizer, dashboard, export, and synthetic badges as authority. Add KaushalVani-inspired roadmap steps, enterprise/self-employment vocabulary, and opportunity presentation only as structured fields backed by canonical rows. Add organization-owned opportunity CRUD, consent-aware candidate summaries, filters, and role-specific portal routes. Implement the minimal IndexedDB profile draft/outbox with idempotency and visible sync states.

**Verification criteria**:

1. Sita receives matched and missing skills, a multi-factor score, a grounded pathway, database-sorted nearby centres, relevant opportunities, and a reason whose facts pass the grounding suite across at least 50 randomized sessions.
2. Beneficiary UI is mic-first, has a 72 px primary target, text/audio alternatives, map/results presentation, synthetic labels, high contrast, screen-reader labels, and no clipping at 200% scaling.
3. Organization can publish only its own opportunity records and search only privacy-minimized, visibility-eligible candidate summaries by the required filters; officer can view maps, charts, funnel, and export.
4. Offline profile drafts show queued/synced/failed/retry states and safe sync behavior, while role tests reject unauthorized cross-role access.

**Plans**: TBD
**UI hint**: yes

### Phase 5: Outcomes, Security And Demo Readiness

**Goal**: The unified product can track livelihood progress and withstand the privacy, failure, performance, and evidence checks required for an honest hackathon demonstration.

**Depends on**: Phase 4

**Requirements**: OUT-01, OUT-02, OUT-03, SEC-01, SEC-02, SEC-03, SEC-04, SEC-05

**Integration focus**: Close the recommendation-to-outcome loop using canonical recommendation IDs and KaushalVani's richer training/certification/employment/self-employment vocabulary. Complete JWT/RBAC, encryption, audit, retention, rate limiting, validation, synthetic visibility, provider/database/network drills, accessibility and latency checks, dependency review, and demo artefacts. Live government APIs and v2 entry doors remain deferred.

**Verification criteria**:

1. A recommendation moves through the full outcome state path, with authorized organization/officer updates, beneficiary confirmation, and a reproducible feedback update to ranking or demand data.
2. RBAC, refresh/expiry, input validation, rate limits, encryption configuration, audit logs, retention purge, and raw-audio default deletion pass automated tests.
3. Network-off, database-down, and revoked-provider drills produce honest recoverable degradation; no API key or request-time government scrape is required.
4. A clean environment passes lint, unit/integration, grounding, idempotent seed, spatial, synthetic-export, accessibility, and latency gates, and the documented Sita demo runs end to end offline.

**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|---|---:|---|---|
| 1. Unified Foundation And Migration Boundary | 3/3 | Complete with deferred environment evidence | 2026-09-29 |
| 2. Canonical Data, Knowledge And Grounded Backend | 3/3 | Complete | 2026-09-29 |
| 3. Voice, Conversation And Profile Journey | 0/TBD | Not started | - |
| 4. Beneficiary And Organization Experiences | 0/TBD | Not started | - |
| 5. Outcomes, Security And Demo Readiness | 0/TBD | Not started | - |

## Coverage Check

All 39 v1 requirements are mapped exactly once in `REQUIREMENTS.md`: Phase 1 (3), Phase 2 (4), Phase 3 (10), Phase 4 (14), Phase 5 (8). v2 requirements and explicit exclusions are not phase acceptance requirements.
