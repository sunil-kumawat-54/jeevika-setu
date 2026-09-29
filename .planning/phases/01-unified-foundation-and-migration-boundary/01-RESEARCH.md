# Phase 1: Unified Foundation And Migration Boundary - Research

**Researched:** 2026-09-28
**Domain:** Runtime consolidation, API/provider contracts, Compose/CI baseline, and beneficiary client spike
**Confidence:** HIGH for repository inventory; MEDIUM for execution readiness because Docker and GNU Make are unavailable in this session

## User Constraints

- Planning only: do not modify application source files during research.
- Do not run AVSAR and KaushalVani as parallel production authorities.
- AVSAR FastAPI is the initial runtime and public business-logic authority.
- Use one canonical PostgreSQL migration lineage.
- Integrate KaushalVani selectively behind unified contracts.
- Facts are database/tool output; generated language only verbalizes those facts.
- Mock mode is a first-class acceptance path with zero API keys after images/assets are prepared.
- Flutter versus Next.js/PWA is a Phase 1 spike; default to PWA unless target-device evidence shows a material browser/audio or native-capability failure.
- The organization/officer/admin portal remains Next.js.
- Preserve decimal NSQF levels, source/version/freshness metadata, and `synthetic` through derived records and exports.
- Do not store raw audio by default after transcription; enforce consent before durable beneficiary data.
- Separate local-stack mock offline judging from browser-disconnected continuity; service-worker caching alone is insufficient.

## Phase Requirements

| ID | Description | Research support |
|----|-------------|------------------|
| VOI-03 | STT and TTS are selected through server-side provider interfaces with real and mock implementations, including Bhashini, Whisper/fallback, and mock configuration paths. | AVSAR `services/core/speech/base.py`, `router.py`, `mock.py`, `bhashini.py`, `sarvam.py`, and `azure.py` provide the existing server-side speech boundary; `config.py` selects it through `VOICE_PROVIDER`. The Phase 1 plan must preserve this boundary and identify the configured approved fallback. |
| NFR-01 | Compose or `make up` starts the canonical stack and the complete journey runs offline with mock providers and zero API keys after preparation. | AVSAR `infra/docker-compose.yml`, `.env.example`, `Makefile`, mock speech/LLM providers, and Gate 0 tests provide the strongest baseline. Docker is unavailable in this session, so clean-start verification remains a required execution checkpoint. |
| NFR-02 | CI runs lint, unit/integration tests, and the grounding test on every pull request. | AVSAR `.github/workflows/ci.yml` runs ruff, clean Alembic migration, pytest, and Next build on pull requests, but does not currently invoke `make grounding`; the Phase 1 plan must close that explicit requirement gap. |

## Summary

AVSAR is the only repository with a coherent mock-first foundation suitable for the initial Jeevikasetu runtime. Its Compose stack defines PostgreSQL/pgvector, Redis, FastAPI core, and Next.js web services with healthchecks; its Makefile provides startup, migration, seed, test, lint, drill, grounding, latency, and mock-provider switches; and its CI establishes Python and frontend gates. [VERIFIED: `AVSAR-main/AVSAR-main/infra/docker-compose.yml`, `AVSAR-main/AVSAR-main/Makefile`, `AVSAR-main/AVSAR-main/.github/workflows/ci.yml`]

KaushalVani is valuable as reviewed domain vocabulary and UI concepts, but its runtime must not be composed into v1. Its Docker topology runs PostgreSQL 15, a Node/Express backend on port 5000, a separate Python AI service on port 8000, and a React/Vite frontend on port 3000. Its backend uses mock login responses, in-memory maps, permissive generated fallback qualifications, hard-coded distance/origin assumptions, and roadmap prose containing fallback facts. [VERIFIED: `KaushalVani-main/KaushalVani-main/docker-compose.yml`, `backend/src/index.ts`, `backend/src/routes/api.routes.ts`, `backend/src/db/store.ts`, `backend/src/controllers/recommendation.controller.ts`, `backend/src/controllers/roadmap.controller.ts`]

The main implementation conflict is that the planning contract requires one public `/v1` FastAPI contract, while the inspected AVSAR app currently registers its routers at unprefixed paths such as `/auth`, `/sessions`, and `/admin`; the AVSAR Next BFF calls `/api/core/sessions` and related paths. This must be resolved explicitly in the Phase 1 contract plan, with a compatibility decision and tests, rather than assumed from documentation. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/main.py`, `AVSAR-main/AVSAR-main/services/core/api/auth.py`, `AVSAR-main/AVSAR-main/services/core/api/sessions.py`, `AVSAR-main/AVSAR-main/apps/web/lib/session.ts`]

**Primary recommendation:** Establish AVSAR FastAPI plus its Compose/Make/CI/Next shell as the only active authority, publish a deliberate `/v1` contract and field/ID mapping, retain KaushalVani only as mapped vocabulary/fixtures, and make the PWA the default beneficiary client pending a narrow target-device gate.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Public business logic and provider egress | API / Backend | — | AVSAR `services/core` owns routers, sessions, recommendations, provider calls, and government-data access; the web client is intended to remain a thin client. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/main.py`] |
| Canonical persistence and migrations | Database / Storage | API / Backend | AVSAR uses Alembic and PostgreSQL-oriented models/migrations; KaushalVani's SQL schema and in-memory store must not become a second lineage. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/alembic/`, `AVSAR-main/AVSAR-main/pipelines/load_to_db.py`, `KaushalVani-main/KaushalVani-main/backend/src/db/store.ts`] |
| Runtime orchestration and local dependency health | API / Backend | CDN / Static | Compose owns db, Redis, core, web, and optional nginx; FastAPI `/healthz` and `/readyz` own application health. [VERIFIED: `AVSAR-main/AVSAR-main/infra/docker-compose.yml`, `services/core/api/health.py`] |
| Beneficiary voice/text interaction | Browser / Client | API / Backend | AVSAR `StartClient.tsx` owns language, microphone, text/choice interaction, SSE consumption, TTS replay, and accessibility focus; FastAPI owns ASR/TTS/provider selection. [VERIFIED: `AVSAR-main/AVSAR-main/apps/web/app/start/StartClient.tsx`, `apps/web/lib/audio.ts`, `services/core/speech/`] |
| Offline shell caching | Browser / Client | — | AVSAR `public/sw.js` caches GET navigations/assets only and explicitly leaves non-GET requests network-only. [VERIFIED: `AVSAR-main/AVSAR-main/apps/web/public/sw.js`] |
| Offline draft continuity/outbox | Browser / Client | API / Backend | This is not implemented by either inspected repository; Phase 1 should define the contract/gate, while implementation belongs to the client continuity phase. [VERIFIED: `AVSAR-main/AVSAR-main/apps/web/public/sw.js`, `KaushalVani-main/KaushalVani-main/frontend/src/`] |
| Auth, role guards, consent and audit | API / Backend | Database / Storage | AVSAR has JWT/refresh, Argon2id officer credentials, role dependencies, consent-gated sessions, and audit helpers. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/api/auth.py`, `api/security.py`, `api/sessions.py`] |
| Organization/officer/admin portal | Browser / Client | API / Backend | Next.js is the selected portal shell; backend authorization and organization ownership must be added behind the unified API in later phases. [VERIFIED: `.planning/PROJECT.md`, `AVSAR-main/AVSAR-main/apps/web/package.json`] |

## Exact Existing Surface

### AVSAR runtime and deployment

| Concern | Existing file(s) | Exact observed behavior | Phase 1 implication |
|---|---|---|---|
| Compose | `AVSAR-main/AVSAR-main/infra/docker-compose.yml` | Project name `avsar`; services `db`, `redis`, `core`, `web`, optional `nginx` profile `full`; db image `pgvector/pgvector:pg16`; Redis `redis:7-alpine`; core `8000`; web `3000`; nginx `8080`. All four baseline services have healthchecks. [VERIFIED: file] | Copy/adapt one Compose authority to Jeevikasetu naming and paths; deliberately decide whether container names, volume names, project name, and `PostGIS` image/extensions change. Do not merge KaushalVani's port 5000/8000 topology. |
| Environment | `AVSAR-main/AVSAR-main/.env.example`, `services/core/config.py` | Defaults are demo/mock: `ENV=demo`, AVSAR DB/Redis URLs, `JWT_ACCESS_MIN=30`, `JWT_REFRESH_H=12`, `LLM_PROVIDER=mock`, `VOICE_PROVIDER=mock`, empty real keys, `EMBEDDING_BACKEND=auto`, `MOCK_OTP=123456`, demo users, retention/rate limits, `CORE_URL`, and `NEXT_PUBLIC_CORE_URL`. [VERIFIED: files] | Keep mock defaults and server-only credentials. Rename product-facing values during migration, add any missing canonical settings, and test `.env.example` against `Settings.model_fields`. |
| FastAPI entrypoint | `services/core/main.py` | Creates FastAPI app, registers health plus optional auth/session/district/recommendation/dashboard/export/admin/live-check routers, adds CORS and exception handlers, exposes `/` with `/healthz` and `/readyz`; no `/v1` router prefix is present. [VERIFIED: file] | Freeze the public prefix policy before client migration. A versioned router mount or compatibility aliases must be planned and tested. |
| Next.js runtime | `apps/web/package.json`, `apps/web/Dockerfile`, `infra/docker-compose.yml` | Next `14.2.35`, React `18.3.1`, Node 20 Alpine image, standalone build, server-side `CORE_URL=http://core:8000`, browser `NEXT_PUBLIC_CORE_URL=http://localhost:8000`; PWA shell is served on `3000`. [VERIFIED: files] | Retain Next as portal and initial beneficiary shell. Do not introduce Vite/React as a second active web runtime. |
| Database migrations | `services/core/alembic.ini`, `services/core/alembic/versions/`, `pipelines/load_to_db.py` | Alembic is invoked inside core by `make migrate` and `make seed`; Gate 1 tests assert one migration head/repeatability. [VERIFIED: `Makefile`, `services/core/tests/test_gate1_models.py`] | Phase 1 freezes one migration lineage and records which KaushalVani fields map forward; no independent `database/schema.sql` runtime. |
| Seeds/ingestion | `pipelines/run_all.py`, `pipelines/load_to_db.py`, `scripts/load_demo.py`, `seeds/` | AVSAR has committed snapshots, ordered ingestion scripts, demo seed loading, and provenance/synthetic patterns. [VERIFIED: repository file inventory and `README.md`] | Keep these as the offline preparation path; later data phase owns schema reconciliation and spatial truth. |

### Health and readiness

- AVSAR liveness is `GET /healthz`; it never touches the database and returns `{"status":"ok","service":"avsar-core","env":...}`. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/api/health.py`]
- AVSAR readiness is `GET /readyz`; it checks database reachability, pgvector availability, Redis ping, and speech router health. It returns `200` with `healthy` or `503` with `degraded`; the mock provider counts as healthy and the speech router always retains a mock floor. LLM readiness is currently marked `ok: true` with the configured provider rather than actively probed. [VERIFIED: `services/core/api/health.py`, `services/core/speech/router.py`]
- Compose core healthcheck calls `http://localhost:8000/healthz`; web healthcheck calls `/api/health`; `Makefile wait-healthy` waits for four named containers and prints `ALL HEALTHY`. [VERIFIED: `infra/docker-compose.yml`, `apps/web/Dockerfile`, `Makefile`]
- KaushalVani exposes only `GET /health` on the Node backend and the Compose file does not define service healthchecks or readiness dependencies beyond `depends_on`; the AI service is described separately but its exact health implementation was not used as a v1 authority. [VERIFIED: `KaushalVani-main/KaushalVani-main/backend/src/index.ts`, `docker-compose.yml`]

### Provider interfaces and mock behavior

- Speech contract: `SpeechProvider` defines `transcribe(audio_b64, lang, step)` and `synthesize(text, lang, step)`, plus cheap `health()`. Shared results carry provider, confidence/latency, language, and degraded metadata. Supported language literals are `hi`, `mr`, `te`, `en`; audio constants are 16 kHz mono and max 15 seconds. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/speech/base.py`]
- Provider implementations: `mock.py`, `bhashini.py`, `sarvam.py`, and `azure.py`; `router.py` builds them from `VOICE_PROVIDER`, orders `sarvam`, `bhashini`, `azure`, `mock`, retries through the ladder, demotes after `PROVIDER_DEMOTE_AFTER` failures, and guarantees a mock floor. [VERIFIED: `services/core/speech/router.py`, `.env.example`]
- LLM contract: `services/core/llm/providers.py` and `guarded.py` provide provider selection and post-checking; `LLM_PROVIDER=mock` or `template` keeps the journey local. The exact LLM contract should be included in the Phase 1 provider map even though VOI-03 is speech-specific. [VERIFIED: `services/core/llm/providers.py`, `llm/guarded.py`, `config.py`]
- Embedding contract: `services/core/rag/embedder.py` supports `auto`, `e5`, and deterministic `hashing`; CI selects hashing to avoid model/network dependence. [VERIFIED: `services/core/rag/embedder.py`, `.github/workflows/ci.yml`]
- KaushalVani does not provide a comparable unified provider interface: its routes call voice behavior through the Node gateway, and its frontend uses browser `SpeechRecognition` then `MediaRecorder` upload. Its fallback can synthesize sample transcript content when APIs fail. [VERIFIED: `KaushalVani-main/KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`, `backend/src/routes/api.routes.ts`]

### Auth, role, session and consent contracts

- AVSAR auth routes are `POST /auth/request-otp`, `POST /auth/verify-otp`, `POST /auth/login`, `POST /auth/refresh`, and `GET /auth/me`. Beneficiaries use validated Indian phone OTP-lite with no password; staff use email/password; demo OTP is returned as `otp_hint`. [VERIFIED: `AVSAR-main/AVSAR-main/services/core/api/auth.py`]
- AVSAR JWTs use HS256 with access and refresh `typ` claims, configurable 30-minute access and 12-hour refresh lifetimes, role and language claims, and Argon2id password hashing for staff. [VERIFIED: `services/core/api/security.py`, `services/core/config.py`]
- Existing AVSAR role ladder is `beneficiary`, `viewer`, `officer`, `admin`; viewer < officer < admin, while beneficiary is outside the staff ladder. Route guards are `require_viewer`, `require_officer`, and `require_admin`. [VERIFIED: `services/core/api/security.py`; role enum is defined in the inspected Alembic initial migration]
- AVSAR sessions begin at `POST /sessions` with `channel`, `lang`, and optional phone; current channels in the session model/contract include `pwa`, `ivr`, `whatsapp`, and `demo`. The turn route is `POST /sessions/{id}/turn` with text/audio/DTMF/choice/fixture variant and SSE events in the order transcript, state, optional recommendations, TTS chunks, or error. [VERIFIED: `services/core/api/sessions.py`, `ARCHITECTURE.md`]
- Consent is the initial FSM step; session creation does not persist profile slots, and the session turn path is responsible for consent gating before durable slot storage. [VERIFIED: `services/core/api/sessions.py`, `services/core/tests/test_gate6_sessions_auth.py`]
- KaushalVani's login endpoint accepts fixed demo credentials and returns `mock-jwt-token-*` values; route handlers have no equivalent server-side role dependency or audit contract. Its beneficiary interface requires a name and stores richer PII in an in-memory `Beneficiary` shape. [VERIFIED: `backend/src/routes/api.routes.ts`, `backend/src/db/store.ts`]

## Contract Conflicts And Migration Boundary

| Conflict | Existing evidence | Required Phase 1 decision |
|---|---|---|
| API version | Requirements say one public `/v1` contract; AVSAR currently mounts unprefixed routers and the Next BFF uses `/api/core`. [VERIFIED: `.planning/REQUIREMENTS.md`, `services/core/main.py`, `apps/web/lib/session.ts`] | Choose the canonical public URL shape, preferably `/v1` for external clients, then define whether temporary unprefixed aliases are test-only or supported during cutover. Update BFF target mapping in the implementation phase, not by running a second backend. |
| Runtime count | AVSAR: FastAPI + Next + Postgres/Redis; KaushalVani: Node + AI FastAPI + Postgres + React. [VERIFIED: both Compose files] | Only AVSAR-shaped stack runs in Compose. KaushalVani service files remain reference material until reviewed behavior is ported. |
| Database authority | AVSAR Alembic/SQLAlchemy-oriented migration path versus KaushalVani `database/schema.sql` and in-memory store. [VERIFIED: repository files] | One Alembic head and one PostgreSQL database. Map KaushalVani concepts to canonical IDs; do not migrate both schemas independently. |
| NSQF | AVSAR architecture/migration uses decimal-safe numeric semantics; KaushalVani `Qualification.nsqf_level` is `number` and seeded as integer 4. [VERIFIED: AVSAR architecture/migration and `backend/src/db/store.ts`] | Preserve decimal NSQF and QP/version identity; never import integer coercion as the canonical type. |
| Recommendation truth | KaushalVani manufactures a `qual-custom-*` QP and fallback facts when matching is weak; roadmap has fixed 350-hour, 8.4 km, salary and grant prose. [VERIFIED: `recommendation.controller.ts`, `roadmap.controller.ts`] | Port only structured vocabulary and presentation concepts. AVSAR DB/tool payload authorizes every fact; no generated fallback entity or numeric claim. |
| Spatial truth | KaushalVani uses fixed beneficiary coordinates and Haversine calculation; AVSAR current centre supply is not proof of verified centre geometry. [VERIFIED: `recommendation.controller.ts`, `.planning/research/SUMMARY.md`] | Phase 1 records this as a Phase 2 dependency and does not promise centre accuracy from either existing implementation. |
| Auth/privacy | AVSAR has consent, JWT, RBAC, audit and minimal beneficiary identity; KaushalVani has fixed login and name-rich in-memory profiles. [VERIFIED: AVSAR auth/security/session files and KaushalVani routes/store] | Publish AVSAR role/consent/session contract as canonical; map KaushalVani fields only where consent, retention and visibility rules permit. |
| Offline semantics | AVSAR service worker caches GETs and refuses POST replay; KaushalVani has browser capture/sample fallback but no durable outbox. [VERIFIED: `AVSAR-main/apps/web/public/sw.js`, `KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`] | Define local-stack offline judging separately from disconnected profile-draft continuity. Do not claim the current service worker satisfies NFR-01/APP-03 by itself. |

## Migration Order

1. **Freeze the authority and URL policy.** Record AVSAR FastAPI as the only business-logic authority, canonical `/v1` public contract decision, BFF mapping, and the rule that KaushalVani Node/AI routes are not started by Compose. [VERIFIED: planning artifacts and inspected entrypoints]
2. **Consolidate runtime configuration.** Make one Jeevikasetu Compose project derived from AVSAR services; retain mock defaults, server-side keys, one DB volume, Redis path, and explicit PostGIS decision. Do not combine port mappings or health models from KaushalVani. [VERIFIED: both Compose files]
3. **Freeze provider contracts.** Publish speech, LLM, embedding, degraded metadata, provider selection, mock fixtures, and health behavior. Confirm whether Whisper is an approved implementation or only a stated fallback requirement; the inspected AVSAR adapters are mock/Bhashini/Sarvam/Azure, not a named Whisper adapter. [VERIFIED: AVSAR speech/config files; [ASSUMED] Whisper is still a desired acceptance implementation because the requirement names it]
4. **Freeze identity and session mapping.** Define canonical role IDs, JWT/refresh behavior, consent-before-storage rule, session/channel IDs, SSE event names, and source-field mapping from KaushalVani's beneficiary/roadmap/outcome concepts. [VERIFIED: AVSAR auth/session files and KaushalVani store/interfaces]
5. **Make health/readiness and Make targets canonical.** Ensure one health URL set, one readiness response shape, and one command vocabulary for developers/judges. Include grounding as a CI-visible command. [VERIFIED: AVSAR health/Make/CI files]
6. **Add CI baseline and clean-stack gate.** Run backend lint/tests/migration, frontend typecheck/build, grounding, and a Compose smoke/readiness check in mock mode. Docker absence blocks execution here but not plan definition. [VERIFIED: current CI and Make targets; environment probe]
7. **Run the client spike against the integrated contract.** Test AVSAR PWA on specified low-end Android/browser targets for mic permission, capture normalization, SSE, playback/autoplay recovery, text fallback, 200% scaling, shell/data preload, and safe draft outbox behavior. Select Flutter only for a material failure or required native capability. [VERIFIED: AVSAR audio/session/client/service-worker files; target devices remain unspecified in planning state]
8. **Hand off canonical data work.** Phase 2 then owns the single migration head, KaushalVani vocabulary mapping, provenance/synthetic propagation, decimal NSQF/QP versions, and verified centre geometry. [VERIFIED: roadmap and research summary]

## Verification Commands

### Existing AVSAR commands

Run from `AVSAR-main/AVSAR-main` after copying `.env.example` to `.env`:

```bash
cp .env.example .env
make up
make ps
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
make seed
make lint
make test
make grounding
make drill
make latency
make mock-on
make ci-local
make down
```

These targets are declared in `Makefile`; `make up` builds and starts `db redis core web` then waits for four healthy containers, `make seed` applies Alembic and loads demo data, `make test` runs backend pytest plus optional web tests, `make grounding` runs 50 randomized grounding checks, and `make ci-local` runs lint, test, and the web build. [VERIFIED: `AVSAR-main/AVSAR-main/Makefile`]

### Direct checks useful for the Phase 1 gate

```bash
docker compose -f infra/docker-compose.yml --env-file .env config
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
curl -fsS http://localhost:3000/api/health
python -m pytest -q services/core/tests/test_gate0_infra.py
python -m pytest -q services/core/tests/test_gate5_speech.py
python -m pytest -q services/core/tests/test_gate6_sessions_auth.py
cd apps/web && npm run typecheck && npm run build
```

Gate 0 directly checks health, readiness dependencies, PostgreSQL 16, pgvector, Redis, required layout/files, Make targets, `.env.example` coverage, empty example secrets, Compose healthchecks, and CI strings. Gate 5 checks the named speech providers and mock journey; Gate 6 checks session, consent, auth, JWT, role and audit behavior. [VERIFIED: `services/core/tests/test_gate0_infra.py`, `test_gate5_speech.py`, `test_gate6_sessions_auth.py`]

### Required new/adjusted checks for Phase 1

```bash
# Required CI behavior: ensure this is invoked by the PR workflow.
make grounding

# Contract prefix smoke test, after the /v1 decision is implemented.
curl -fsS http://localhost:8000/v1/healthz
curl -fsS -X POST http://localhost:8000/v1/sessions \
  -H 'content-type: application/json' \
  -d '{"channel":"pwa","lang":"hi"}'

# Confirm the duplicate runtime is absent from the active Compose project.
docker compose -f infra/docker-compose.yml ps
```

The `/v1` smoke commands are future verification targets, not current passing commands, because the inspected AVSAR app currently exposes `/healthz` and `/sessions` without the version prefix. [VERIFIED: `services/core/main.py`, `api/health.py`, `api/sessions.py`]

## Flutter Versus Next.js/PWA Spike

**Default selection: AVSAR Next.js/PWA.** It is the only client with direct evidence for the integrated journey: `StartClient.tsx` handles language selection, session creation, mic support, text/choice fallback, SSE transcript/state/recommendation/TTS events, audio replay, degraded/offline notices, and focus management; `lib/audio.ts` normalizes browser recordings; `public/sw.js` pre-caches shell routes and makes GET requests network-first. [VERIFIED: AVSAR client files]

**PWA pass criteria:**

- Mic permission request and denial are recoverable on the target low-end Android browser.
- `MediaRecorder` capture can be normalized to the FastAPI audio contract; playback works after user gesture and can recover from autoplay failure.
- SSE turn events render transcript, state, recommendations, TTS chunks, degraded metadata, and errors without duplicate turns.
- Text/choice input remains usable when microphone or provider access fails.
- The first screen and conversation remain usable at 200% text scaling with focus and screen-reader labels.
- Preloaded shell/data supports the agreed disconnected experience; no conversational POST is replayed blindly.
- A draft/outbox probe demonstrates idempotency and visible queued/synced/failed/retry states, or records the gap for the later client phase.

**Flutter switch gate:** select Flutter only if target-device evidence shows a material browser/audio failure, or the product explicitly requires background audio, call interruption handling, Bluetooth/device integration, or installed-app/native distribution. This is consistent with the planning decision and avoids introducing a second beneficiary implementation before the shared backend contract is stable. [VERIFIED: `.planning/STATE.md`, `.planning/research/SUMMARY.md`; target-device thresholds are [ASSUMED] and need product confirmation]

**KaushalVani client evidence:** its React/Vite frontend provides a `VoiceRecorder` with Web Speech recognition and `MediaRecorder` fallback, plus roadmap/accessibility components, but failed speech can lead to sample transcript simulation and its API paths are `/api/*` behind Node rather than the canonical FastAPI contract. [VERIFIED: `KaushalVani-main/KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`, `frontend/package.json`, `backend/src/routes/api.routes.ts`]

## Don't Hand-Roll

| Problem | Don't build | Use instead | Reason |
|---|---|---|---|
| Provider selection/failover | Client-side vendor calls or ad hoc retries | AVSAR `SpeechRouter` and server-side provider interfaces | Keeps credentials server-side, gives degraded metadata, and guarantees mock floor. [VERIFIED: `services/core/speech/base.py`, `router.py`] |
| Auth/role enforcement | Frontend-only role checks or KaushalVani mock JWT | AVSAR JWT/refresh, Argon2id and FastAPI role dependencies | Role-sensitive operations need server enforcement and audit. [VERIFIED: `services/core/api/auth.py`, `api/security.py`] |
| Grounded recommendation facts | Generated fallback qualifications, distances, salaries or QPs | Canonical DB/tool payload plus guarded verbalizer | Prevents the exact KaushalVani fallback behavior from entering v1. [VERIFIED: KaushalVani recommendation/roadmap controllers; AVSAR architecture/research] |
| Offline conversational replay | Service-worker cache replay of POST turns | Explicit profile-draft outbox with idempotency and state machine | AVSAR worker intentionally network-only for non-GET; blindly replaying turns can duplicate FSM transitions. [VERIFIED: `apps/web/public/sw.js`] |
| Second runtime gateway | Node gateway proxy plus standalone AI service | FastAPI `/v1` boundary | One authority is a locked architecture requirement. [VERIFIED: `.planning/REQUIREMENTS.md`, AVSAR `main.py`] |
| Spatial distance | Fixed-origin Haversine result | Later canonical PostGIS geometry and database-side distance | Existing KaushalVani distance is not verified centre truth. [VERIFIED: KaushalVani recommendation controller; `.planning/research/SUMMARY.md`] |

## Common Pitfalls

1. **Assuming documentation equals the current route surface.** AVSAR docs describe `/auth`, `/sessions`, and `/healthz`, while the product requirements require `/v1`; make the prefix decision explicit and test it. [VERIFIED: planning requirements, AVSAR architecture, AVSAR `main.py`]
2. **Running both Compose files.** Both stacks claim ports 3000 and 5432, and KaushalVani also claims 8000 for AI; concurrent startup creates ambiguous authority and port conflicts. [VERIFIED: both Compose files]
3. **Treating readiness as liveness.** `/healthz` deliberately does not touch dependencies; use `/readyz` and container health status for the clean-stack gate. [VERIFIED: AVSAR health.py and Compose]
4. **Calling mock mode decorative.** AVSAR Gate 5 tests that fixtures cover dialogue steps and reach a real recommendation; retain those tests while moving the boundary. [VERIFIED: `test_gate5_speech.py`]
5. **Adding Whisper by assumption.** VOI-03 names Whisper/fallback, but no inspected AVSAR file is a named Whisper adapter. Require a decision or implementation task; do not claim it exists. [VERIFIED: inspected speech files; [ASSUMED] requirement interpretation]
6. **Confusing shell caching with offline continuity.** AVSAR caches GETs and leaves POSTs network-only; the PWA spike must separately test draft persistence and safe sync. [VERIFIED: `public/sw.js`]
7. **Importing KaushalVani generated facts.** Its weak-match path creates synthetic QP codes and its roadmap fills missing facts with hard-coded values. Port labels and step concepts, not those values. [VERIFIED: recommendation and roadmap controllers]
8. **Changing role names casually.** Existing AVSAR staff roles are `viewer`, `officer`, and `admin`; KaushalVani uses `official` and `admin`. Publish the canonical mapping before UI or data migration. [VERIFIED: AVSAR security and KaushalVani auth route]
9. **Assuming current CI satisfies NFR-02.** AVSAR CI runs lint, pytest, migrations and Next build, but the inspected workflow has no `grounding` invocation. Add and verify it. [VERIFIED: `.github/workflows/ci.yml`]

## State Of Existing Implementations

| Area | AVSAR | KaushalVani | Decision |
|---|---|---|---|
| Backend | FastAPI core with routers, DB, sessions, auth, recommendation, dashboard, exports, admin | Node/Express gateway plus FastAPI AI service | AVSAR only |
| Frontend | Next.js 14 PWA and portal shell | React/Vite beneficiary portal | Next.js baseline; Flutter only after spike |
| Persistence | Alembic/PostgreSQL-oriented canonical path, Redis runtime | PostgreSQL schema plus in-memory runtime store | AVSAR migration lineage only |
| Providers | Speech interfaces/adapters/mock floor; LLM and embedding selection | Voice endpoints/front-end browser speech and API fallback | AVSAR provider boundary only |
| Offline | Service-worker shell/cache; no POST replay | No durable offline queue found | Local-stack mock now; outbox gate later |
| CI/operations | `.github/workflows/ci.yml`, Makefile, drills, grounding, latency | No equivalent inspected root CI/Make baseline | AVSAR operational baseline |
| Domain reuse | Crosswalk, NSQF, seeded persona and grounded recommendation surfaces | Roadmap, opportunity, enterprise, outcome vocabulary and UX | Map selectively behind contracts |

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---:|---|---|
| Docker / Docker Compose | Compose startup, readiness, offline smoke | No | — | Install/enable Docker Desktop before execution; no live Compose result was obtained in this session. |
| GNU Make | Existing AVSAR command surface | No | — | Use Git Bash/WSL or invoke the underlying `docker compose`, `pytest`, `ruff`, and npm commands directly. |
| Node.js | Next build and client spike tooling | Yes | `v25.9.0` | Prefer the repository's Node 20 container/CI target for reproducible builds. |
| Python | FastAPI/tests | Yes | `3.13.1` | Use AVSAR's CI/container Python 3.12 target for compatibility evidence. |
| PostgreSQL/Redis host services | Direct host run | Not probed as live services because Docker is unavailable | — | Use Compose containers; no host services should become a second authority. |

## Validation Architecture

### Existing test framework

| Property | Value |
|---|---|
| Framework | pytest for core; npm scripts for Next typecheck/build; ruff for Python lint. [VERIFIED: `services/core/requirements-dev.txt`, `Makefile`, `.github/workflows/ci.yml`] |
| Config | `services/core/tests/conftest.py`; `apps/web/package.json`; CI starts service containers for backend checks. [VERIFIED: files] |
| Quick backend command | `python -m pytest -q services/core/tests/test_gate0_infra.py` after DB/Redis are available. |
| Full existing command | `make ci-local` plus `make grounding`; current `ci-local` itself does not include grounding. [VERIFIED: Makefile] |

### Phase requirements to test map

| Req ID | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| VOI-03 | Provider names implement one server-side speech contract; mock works without credentials; degraded/fallback metadata is explicit. | Unit/integration | `python -m pytest -q services/core/tests/test_gate5_speech.py` | Yes |
| NFR-01 | One Compose stack starts db, Redis, FastAPI and web; health/readiness pass; mock journey works without keys. | Compose smoke/integration | `make up && curl -fsS http://localhost:8000/readyz && make seed && make test` | Partial: Compose and Gate 0 exist; clean smoke unavailable in this session |
| NFR-02 | PR CI runs lint, tests, grounding, and frontend build. | CI/config plus integration | `make ci-local && make grounding`; inspect workflow for `make grounding` | Partial: current workflow lacks grounding invocation |

### Wave 0 gaps for planning

- [ ] Decide and test the `/v1` public prefix and any temporary compatibility aliases.
- [ ] Add a Phase 1 contract test for the canonical health/readiness and session/provider envelope after the prefix decision.
- [ ] Add `make grounding` (or equivalent direct grounding command) to PR CI and a test that fails if the gate is omitted.
- [ ] Define the canonical role mapping from KaushalVani `official`/`admin` to AVSAR `viewer`/`officer`/`admin`, including organization role introduction timing.
- [ ] Define the client spike target matrix: exact Android devices, browser versions, assistive technology, connectivity profile, and pass/fail threshold.
- [ ] Define the boundary between local-stack offline judging and disconnected beneficiary draft/outbox continuity.
- [ ] Confirm whether Whisper is required as an actual adapter in Phase 1 or whether the existing server-side fallback ladder satisfies the requirement.

## Security Domain

Security enforcement is enabled at ASVS level 1 in `.planning/config.json`. [VERIFIED: `.planning/config.json`]

| ASVS category | Applies | Existing control/evidence | Phase 1 action |
|---|---:|---|---|
| V2 Authentication | Yes | AVSAR phone OTP-lite and staff login; server-side token creation. [VERIFIED: `api/auth.py`] | Preserve canonical auth endpoints and test mock credentials remain server-side. |
| V3 Session Management | Yes | Access/refresh JWT types, expiry, bearer validation. [VERIFIED: `api/security.py`] | Include refresh/expiry and session identity in the published mapping. |
| V4 Access Control | Yes | Role ranking and route dependencies; audit helper. [VERIFIED: `api/security.py`] | Map KaushalVani role concepts without importing frontend-only authorization. |
| V5 Input Validation | Yes | Pydantic request models, phone validation, audio size cap, rate-limit dependencies. [VERIFIED: `api/auth.py`, `api/sessions.py`] | Keep validation in FastAPI and include contract tests. |
| V6 Cryptography | Yes | Argon2id password hashing and JWT signing; TLS is deployment configuration. [VERIFIED: `api/security.py`, `ARCHITECTURE.md`] | Do not move secrets to either client; record production secret/TLS checkpoint. |

Known Phase 1 threat patterns: duplicate runtime authority can fork auth/session state; browser/provider direct calls can expose credentials; KaushalVani fallback generation can create fabricated regulated facts; and service-worker POST replay can duplicate conversational turns. The standard mitigations are one FastAPI boundary, server-side provider calls, database/tool-grounded facts, and explicit outbox idempotency. [VERIFIED: inspected source and planning requirements]

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The Phase 1 public contract should use `/v1` and may need temporary aliases. | Contract conflicts | A different versioning decision changes BFF, health, CI and client test tasks. |
| A2 | Whisper is a required implementation rather than a requirement-level fallback label. | Provider migration | The plan could add unnecessary provider work or miss an acceptance gate. |
| A3 | Target-device acceptance can be defined after product supplies exact Android/browser/AT matrix. | Client spike | The PWA/Flutter decision cannot be made reproducibly without targets. |
| A4 | The minimal outbox belongs after the Phase 1 contract gate rather than inside the foundation itself. | Migration order | NFR-01 wording may require a broader Phase 1 client artifact than current roadmap intent. |

## Open Questions

1. **What exact URL shape is canonical?** Current AVSAR routes are unprefixed while requirements require `/v1`; planner should make the route mount and compatibility policy a first task.
2. **Which additional language is configured for v1?** Existing AVSAR supports `hi`, `mr`, `te`, `en`; product requirements say Hindi, English, and one configured additional Indian language. The plan should keep the provider contract extensible and select the acceptance language explicitly.
3. **Is Whisper an actual provider deliverable?** No inspected AVSAR adapter is named Whisper; confirm whether `sarvam`/`bhashini`/`azure` plus mock satisfies the intended fallback.
4. **What target devices and disconnected scope define the spike?** Planning state records these as unspecified; the spike cannot produce a durable PWA/Flutter decision until they are named.
5. **When does the organization role enter the canonical RBAC enum?** It is required by later requirements but is not in the current AVSAR role ladder; Phase 1 should reserve the mapping and Phase 5/4 should implement according to the roadmap sequence.

## Sources

### Primary repository sources read this session

- `AVSAR-main/AVSAR-main/infra/docker-compose.yml`
- `AVSAR-main/AVSAR-main/.env.example`
- `AVSAR-main/AVSAR-main/Makefile`
- `AVSAR-main/AVSAR-main/.github/workflows/ci.yml`
- `AVSAR-main/AVSAR-main/services/core/main.py`
- `AVSAR-main/AVSAR-main/services/core/config.py`
- `AVSAR-main/AVSAR-main/services/core/api/health.py`
- `AVSAR-main/AVSAR-main/services/core/api/auth.py`
- `AVSAR-main/AVSAR-main/services/core/api/security.py`
- `AVSAR-main/AVSAR-main/services/core/api/sessions.py`
- `AVSAR-main/AVSAR-main/services/core/speech/base.py`
- `AVSAR-main/AVSAR-main/services/core/speech/router.py`
- `AVSAR-main/AVSAR-main/services/core/tests/test_gate0_infra.py`
- `AVSAR-main/AVSAR-main/services/core/tests/test_gate5_speech.py`
- `AVSAR-main/AVSAR-main/services/core/tests/test_gate6_sessions_auth.py`
- `AVSAR-main/AVSAR-main/apps/web/package.json`
- `AVSAR-main/AVSAR-main/apps/web/Dockerfile`
- `AVSAR-main/AVSAR-main/apps/web/lib/session.ts`
- `AVSAR-main/AVSAR-main/apps/web/app/start/StartClient.tsx`
- `AVSAR-main/AVSAR-main/apps/web/public/sw.js`
- `KaushalVani-main/KaushalVani-main/docker-compose.yml`
- `KaushalVani-main/KaushalVani-main/.env.example`
- `KaushalVani-main/KaushalVani-main/backend/src/index.ts`
- `KaushalVani-main/KaushalVani-main/backend/src/routes/api.routes.ts`
- `KaushalVani-main/KaushalVani-main/backend/src/db/store.ts`
- `KaushalVani-main/KaushalVani-main/backend/src/controllers/recommendation.controller.ts`
- `KaushalVani-main/KaushalVani-main/backend/src/controllers/roadmap.controller.ts`
- `KaushalVani-main/KaushalVani-main/frontend/package.json`
- `KaushalVani-main/KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`

### Planning sources

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/research/SUMMARY.md` (the requested root `research/SUMMARY.md` does not exist; this is the located planning synthesis)
- `.planning/config.json`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH; exact Compose, Make, CI, package, and FastAPI files were opened.
- Architecture: HIGH for the current repository boundary; MEDIUM for the target `/v1` and organization-role decisions because they are planning gaps.
- Pitfalls: HIGH for duplicate runtime, generated fallback facts, readiness distinction, provider mock floor, and service-worker POST behavior because each is visible in source.
- Execution readiness: MEDIUM; Docker and GNU Make were unavailable, so no live Compose startup or readiness result was obtained.

**Research date:** 2026-09-28
**Valid until:** 2026-10-05 for provider/runtime availability; repository-local contract findings remain valid until source changes.
