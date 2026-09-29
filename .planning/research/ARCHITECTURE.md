# Jeevikasetu Integration Architecture Research

**Scope:** Existing `AVSAR-main` and `KaushalVani-main` implementations, combined against `JEEVIKASETU-GSD-PRD.md` and `.planning/PROJECT.md`.
**Researched:** 2026-09-28
**Recommendation:** Use AVSAR as the initial implementation source of truth; integrate KaushalVani selectively behind AVSAR's contracts.

## Executive Decision

AVSAR should be the initial source of truth for the combined Jeevikasetu product. It is materially closer to the PRD's operational contract: one FastAPI core owns business logic and provider egress; PostgreSQL is extended for vector and text retrieval; seeds and ingestion are committed; mock mode is designed to run offline; and grounding, kill-service, latency, export, dashboard, and admin concerns are already represented in the architecture and delivery plan.

KaushalVani should be treated as a source of product concepts and selective implementation assets, not as a second runtime foundation. Its React/Vite client, Node/Express gateway, Python AI service, and PostgreSQL schema form a coherent demo architecture, but retaining that stack beside AVSAR would create two API authorities, two profile/recommendation models, two auth paths, and two provider boundaries. That directly conflicts with the PRD's single coherent backend, deterministic grounded facts, mock-provider requirement, and operational simplicity.

The initial target should therefore be an AVSAR-shaped deployment: Next.js web client(s) -> AVSAR FastAPI core -> PostgreSQL/pgvector plus Redis, with offline ingestion and mock providers. The beneficiary client can remain a Next.js PWA for the first integration increment while the PRD's Flutter-versus-PWA spike remains an explicit later decision. KaushalVani's accessible journey and roadmap concepts should be mapped into this contract rather than introduced through its Node gateway.

## Existing System Comparison

| Concern | AVSAR | KaushalVani | Jeevikasetu decision |
|---|---|---|---|
| Primary API | Python FastAPI `services/core`, modular routers | Node/Express gateway plus separate FastAPI AI service | AVSAR core owns the public contract and business logic |
| Frontend | Next.js 14 PWA for beneficiary, dashboard, admin | React/Vite/TypeScript portal | Keep AVSAR web shell initially; port UX ideas selectively |
| Data access | SQLAlchemy/PostgreSQL, pgvector, text retrieval, committed seeds and pipelines | Node `pg` access against a single SQL schema; no vector model in schema | AVSAR schema and migrations are canonical; reconcile domain fields |
| AI boundary | Speech/LLM/RAG provider abstractions in the core; mock twins | AI service exposes extraction, Bhashini proxy, and rule-based recommendations | Keep provider interfaces in AVSAR; port only useful extraction vocabulary |
| Voice flow | Session turn protocol, mock fixtures, speech router, grounded verbalizer, fallback ladder | Separate STT/TTS endpoints and a simple extraction endpoint | Unify on AVSAR sessions/turn protocol |
| Grounding | Tool-output-only design, post-check, `verify_grounding.py`, deterministic scoring | Claims verified by data access in principle, but AI endpoint composes recommendation text and facts | AVSAR's grounding invariant and test are mandatory |
| Operations | Compose health checks, `make up/seed/test/drill/grounding/latency`, optional ML image mode | Compose starts four services, but has basic `depends_on` and no equivalent full drill | Use AVSAR operational gates and add missing combined checks |
| Privacy/auth | Consent, JWT/RBAC, audit and retention described and represented in core | User/profile schema, JWT-oriented gateway, outcome tables | Port KaushalVani fields only after mapping to AVSAR consent/RBAC model |
| Outcome model | Recommendations and outcome tracking are part of architecture and routes | Explicit `livelihood_roadmaps` and `outcomes` tables | Keep AVSAR identity and recommendation keys; add roadmap/outcome richness |

## Recommended Target Boundary

```text
Next.js beneficiary PWA / future Flutter app
Next.js organization + officer + admin portal
                         |
                 HTTPS / JSON / audio
                         v
              AVSAR FastAPI core
   sessions, consent, profile, gap, recommendations,
   auth/RBAC, dashboard, exports, outcomes, admin
       |                 |                 |
       v                 v                 v
 PostgreSQL + pgvector  Redis          Provider adapters
 PostGIS-oriented data  cache/limits   mock | Bhashini | fallback
       ^
       |
 offline ingestion pipelines -> committed, synthetic-labelled seeds
```

The core is the only component allowed to call government data sources, LLMs, STT/TTS providers, or embedding services. Client applications consume the core contract and never replicate recommendation or qualification logic.

### Canonical responsibilities

- **Client:** voice/text capture, accessibility, replay, local draft/offline queue, result presentation, role-aware navigation.
- **FastAPI core:** consent gate, session state machine, profile extraction orchestration, deterministic eligibility/gap/recommendation logic, grounded verbalization, auth/RBAC, audit, outcomes, exports, and degradation behavior.
- **Provider adapters:** real and mock implementations for STT, TTS, LLM, and embeddings. Provider choice is configuration, not client behavior.
- **Database:** profiles, skills, qualifications/QPs, pathways, centres, opportunities, recommendations, consents, audit events, and outcomes. Source and verification metadata plus `synthetic` must survive every path.
- **Pipelines:** offline, idempotent fetch/normalize/join/embed/seed jobs. Request-time scraping is prohibited.

## What Can Be Reused

### Adopt directly from AVSAR

1. **FastAPI core structure.** `services/core/main.py` establishes the correct application factory, router registration, centralized error payloads, health/readiness endpoints, request metrics, and database-down behavior. Its optional router loading supports incremental phase delivery.
2. **Provider and retrieval boundaries.** AVSAR's `speech`, `llm`, and `rag` packages match the PRD's provider abstraction and grounded recommendation requirements. Keep deterministic structured lookup as the primary recommendation path and use RAG for explanatory scheme facts.
3. **Offline data strategy.** Reuse `pipelines/`, `seeds/`, `data/crosswalk/`, prompt fixtures, source metadata, idempotent loading, and synthetic-data flags. This is stronger than KaushalVani's runtime-shaped SQL seed story.
4. **Operational verification.** Preserve the grounding verifier, kill-service drill, latency report, purge/runbook patterns, Make targets, container health checks, and mock journey. These are product requirements, not optional implementation detail.
5. **Next.js shell and portal structure.** AVSAR already aligns with the PRD's portal choice and has beneficiary, dashboard, admin, export, and crosswalk surfaces. Keep its server-side BFF/proxy rule so vendor keys stay in the core.
6. **Security posture.** Retain consent-before-storage, JWT/RBAC, audit logging, server-side provider calls, retention controls, and no-raw-audio-by-default behavior.

### Port selectively from KaushalVani

1. **Profile vocabulary.** Its fields such as `desired_occupation`, `employment_preference`, `mobility_km`, interests, experience, and digital-literacy context are useful, but must map into the PRD's canonical `profiles`, `profile_skills`, preferences, and session fields rather than become a second beneficiary table.
2. **Roadmap presentation.** The explicit progression from aspiration to profile, skill gap, qualification, training, opportunity, and outcome should inform the AVSAR result UI and API payload. Store pathway steps as structured data linked to a canonical recommendation.
3. **Outcome detail.** Its separate training, certification, employment, enterprise, placement-date, income-band, and feedback concepts are useful additions to AVSAR's outcome state machine, subject to consent, role permissions, and synthetic flags.
4. **Accessibility and language UX.** Reuse the intent: 72px-or-larger voice control, high contrast, scalable typography, Marathi/Hindi/English defaults, and clear voice/text fallback. Port components or copy only after matching the AVSAR design and prompt-data conventions.
5. **Demo persona semantics.** Reconcile KaushalVani's Sita scenario with the PRD/AVSAR Sita fixture, retaining one canonical seeded identity and one canonical recommendation path.
6. **API ideas.** The nearby-centre, jobs, enterprise-pathway, roadmap, and outcome concepts can fill gaps in AVSAR's API, but routes must be redesigned under the `/v1` contract and backed by AVSAR models.

### Do not reuse as runtime foundations

- The Node/Express API gateway as a parallel public API.
- The standalone KaushalVani AI service as a second extraction/recommendation authority.
- The KaushalVani database schema as a parallel migration source.
- Direct client assumptions about Bhashini, qualifications, jobs, or recommendation internals.
- KaushalVani's permissive `cors()` and AI-service `allow_origins=["*"]` configuration.
- Rule-based extraction that marks every profile complete and uses hard-coded fallback facts without an explicit mock-provider contract.

## Conflicts That Must Be Resolved

### 1. Two backend authorities
AVSAR exposes a single FastAPI core; KaushalVani routes through Node and delegates selected work to FastAPI. Running both preserves duplicate sessions, auth, recommendation, and error contracts. Resolve by making AVSAR core the only public backend. If Node code contains a useful utility, port the behavior into a core module and delete the runtime dependency from the composed product.

### 2. Incompatible API contracts
AVSAR centers on `/v1/sessions`, turn streaming, profile patching, gap analysis, recommendations, centres, opportunities, analytics, exports, outcomes, and auth. KaushalVani uses `/api/beneficiaries`, `/api/voice/*`, `/api/recommendations/generate`, and `/api/roadmap/*`. Resolve by choosing the AVSAR session/turn and `/v1` contract, then adding roadmap/outcome fields to those responses where needed. Do not support both contracts indefinitely.

### 3. Database schema mismatch
AVSAR models sessions, consent, transcripts, courses/qualifications, crosswalk, document chunks, centre supply, recommendations, and audit records around grounded retrieval. KaushalVani models a named beneficiary, qualifications, centres, jobs, enterprise pathways, roadmaps, and outcomes with different IDs, types, and required fields. Resolve with one migration set and an explicit mapping document. Preserve AVSAR's `source`, `last_verified`, vector/search fields, consent/audit relations, PostGIS-compatible location, and `synthetic` markers. Add KaushalVani roadmap/outcome attributes only where they satisfy PRD requirements.

### 4. PostgreSQL capability and deployment mismatch
AVSAR uses PostgreSQL 16 with pgvector and pg_trgm initialization, plus Redis. KaushalVani uses PostgreSQL 15 and a schema that only enables `uuid-ossp`. The two Compose files expose the same host ports and define different service/container names. Resolve by retaining AVSAR's database image and extensions, renaming or removing the nested stacks from the active runbook, and assigning one Compose project/volume. Add PostGIS only if the existing schema and image are upgraded deliberately; do not assume latitude/longitude columns alone satisfy the PRD's PostGIS requirement.

### 5. Frontend framework and beneficiary-client decision
AVSAR uses Next.js 14; KaushalVani uses Vite React. The PRD names Next.js for the portal and leaves Flutter versus PWA open for beneficiaries. Resolve in two steps: use AVSAR Next.js for the first integrated journey, then run the mandated Flutter/PWA spike against mic permissions, WebSocket/streaming behavior, offline queue, accessibility, and low-end Android performance. A future Flutter client must consume the same core contract, not fork business logic.

### 6. Voice/provider behavior
AVSAR's design has provider selection, failover, fixtures, and mock mode. KaushalVani's AI endpoint returns fixed sample transcripts for the STT fallback and labels a TTS response without showing a provider abstraction. Resolve by moving any useful language fixtures into AVSAR's fixture/provider tests and requiring `real` and `mock` implementations for each provider. Real Bhashini calls remain server-side and optional.

### 7. Recommendation truth and explainability
KaushalVani's AI service selects the first matching qualification from caller-provided arrays and emits hard-coded factor scores and placement language. That makes the caller responsible for facts and can produce invented or unverified claims. Resolve by having core retrieval and scoring produce the recommendation object; an LLM or template may only verbalize that object. Every result must include matched/missing skills, factor breakdown, explanation, source metadata, and grounding status.

### 8. Identity and privacy
KaushalVani requires a name in its schema and its AI response extracts name/age; AVSAR and the PRD emphasize minimal PII, spoken consent, and no required name. Resolve by making name optional, placing consent before durable profile storage, retaining only necessary identity/contact data, and applying role-based field visibility. Avoid importing KaushalVani's named-profile assumptions into the canonical schema.

### 9. Security and operational maturity
KaushalVani's public CORS defaults are broad and its Compose dependency ordering lacks health conditions. AVSAR has a stronger error, health, provider, and drill posture. Resolve by adopting AVSAR's restrictive environment-driven CORS, readiness checks, rate limits, audit/retention controls, and CI gates. Review all imported UI/API code for secret exposure before porting.

## Practical Coarse Phase Sequence

1. **Contract and repository foundation**
   - Freeze AVSAR as the initial runtime anchor.
   - Define the unified `/v1` API, canonical IDs, roles, consent rules, synthetic-data policy, and source metadata.
   - Keep the two source directories read-only/reference-only during integration; do not merge duplicate Compose files.
   - Exit check: one architecture decision record and one endpoint/data mapping table.

2. **Runtime consolidation**
   - Make AVSAR Compose the only active local deployment: FastAPI core, Next.js web, PostgreSQL/pgvector, Redis.
   - Reconcile environment names, ports, health checks, Docker contexts, and Make targets.
   - Add PostGIS deliberately if required by the chosen PostgreSQL image/schema path.
   - Exit check: clean `make up` starts one coherent stack and all health/readiness checks pass.

3. **Canonical data model and ingestion**
   - Keep AVSAR migrations/seeds/pipelines and reconcile KaushalVani fields for profile, qualification, centre, job, enterprise, roadmap, and outcome concepts.
   - Add required roadmap/outcome attributes without duplicating beneficiaries or qualifications.
   - Validate source/verification/synthetic propagation and idempotent reloads.
   - Exit check: `make seed` produces the single Sita fixture, searchable qualifications, nearby supply, and outcome-capable recommendation rows.

4. **Session, profile, and voice integration**
   - Preserve AVSAR's consent/session/turn state machine and provider interfaces.
   - Port KaushalVani's useful extraction vocabulary, multilingual prompts, and accessibility behavior into AVSAR's prompt/fixture/provider tests.
   - Keep text fallback, replay, retry, degraded responses, and offline mock mode first-class.
   - Exit check: a mock Hindi/Marathi/English journey persists only after consent and handles provider failure without a second AI service.

5. **Grounded recommendation and pathway experience**
   - Use AVSAR deterministic retrieval/scoring/crosswalk as authority.
   - Extend the payload and UI with KaushalVani-style roadmap steps, explicit skill gaps, enterprise/wage alternatives, and factor explanations.
   - Add automated checks that every displayed/spoken fact is present in core output.
   - Exit check: the Sita journey shows one canonical recommendation, nearby centre, why-this factors, pathway steps, and no invented facts.

6. **Portal, roles, and outcomes**
   - Consolidate beneficiary, facilitator, organization, officer, and admin views in the AVSAR Next.js shell.
   - Port KaushalVani's roadmap/outcome presentation ideas and accessibility patterns.
   - Implement organization opportunity posting/matching, officer analytics/exports, server-side RBAC, audit visibility, and outcome status updates.
   - Exit check: each role's allowed journey works against the same records and exports preserve `synthetic` markers.

7. **Client decision and hardening**
   - Run the Flutter-versus-PWA spike using the integrated core, not a parallel backend.
   - Choose whether Flutter replaces or complements the beneficiary PWA; keep the portal Next.js unless a separate decision changes it.
   - Run grounding, RBAC, accessibility, latency, offline drill, provider-revocation, DB-down, retention, and dependency audits.
   - Exit check: PRD acceptance journey and CI gates pass from a clean environment with no API keys.

## Verification Priorities

The cheapest discriminating integration checks are:

- `make up && make seed` starts only the canonical AVSAR stack and exposes one API, one web client, one database, and one Redis instance.
- The mock journey reaches recommendation and outcome update without Node/Express or the KaushalVani AI service running.
- A recommendation's QP code, course name, number, centre, duration, and explanation are all derived from core/database output; the grounding test remains zero-invention.
- Database-down, provider-key-revoked, and network-off drills produce speakable degraded responses and recover.
- Role tests prove that imported KaushalVani concepts do not bypass AVSAR consent, RBAC, audit, or synthetic-data rules.
- The Flutter/PWA decision is measured against the PRD's mic, offline, accessibility, and low-bandwidth constraints rather than chosen by framework preference.

## Source Files Read

- [JEEVIKASETU-GSD-PRD.md](../../JEEVIKASETU-GSD-PRD.md)
- [AVSAR README](../../AVSAR-main/AVSAR-main/README.md)
- [AVSAR ARCHITECTURE.md](../../AVSAR-main/AVSAR-main/ARCHITECTURE.md)
- [AVSAR PLAN.md](../../AVSAR-main/AVSAR-main/PLAN.md)
- [AVSAR TECH_STACK.md](../../AVSAR-main/AVSAR-main/TECH_STACK.md)
- [AVSAR pyproject.toml](../../AVSAR-main/AVSAR-main/pyproject.toml)
- [AVSAR web package.json](../../AVSAR-main/AVSAR-main/apps/web/package.json)
- [AVSAR Compose/Docker/entrypoint files](../../AVSAR-main/AVSAR-main/infra/docker-compose.yml)
- [KaushalVani README](../../KaushalVani-main/KaushalVani-main/README.md)
- [KaushalVani architecture](../../KaushalVani-main/KaushalVani-main/docs/ARCHITECTURE.md)
- [KaushalVani API](../../KaushalVani-main/KaushalVani-main/docs/API.md)
- [KaushalVani backend package.json](../../KaushalVani-main/KaushalVani-main/backend/package.json)
- [KaushalVani frontend package.json](../../KaushalVani-main/KaushalVani-main/frontend/package.json)
- [KaushalVani AI entrypoint](../../KaushalVani-main/KaushalVani-main/ai-service/main.py)
- [KaushalVani Compose/schema](../../KaushalVani-main/KaushalVani-main/docker-compose.yml)
