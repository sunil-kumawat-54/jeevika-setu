# Phase 1: Unified Foundation And Migration Boundary - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 18 candidate modules/configuration files across AVSAR and KaushalVani
**Analogs found:** 18 workspace references / 0 tracked-source analogs

## Important Source-Provenance Note

The workspace Git index currently contains the planning artifacts, but not the files under `AVSAR-main/` or `KaushalVani-main/`. `git ls-files` from the workspace root returned no application paths, and both nested paths resolve to the same workspace Git root rather than independent repositories. Therefore every file below is an **untracked workspace reference**, not a planner-approved tracked analog. Before execution, promote the selected source trees or their copied modules into tracked source and re-run the tracked-source gate. Do not treat the current untracked paths as a stable migration dependency.

The recommendations are still concrete: AVSAR owns the runtime contract; KaushalVani contributes reviewed domain and UX vocabulary only.

## File Classification

| Phase 1 concern | Role / data flow | Recommended source reference | Recommendation | Match quality |
|---|---|---|---|---|
| Canonical service entrypoint | application factory / request-response | `AVSAR-main/AVSAR-main/services/core/main.py` | Copy/adapt as the only public FastAPI authority | exact |
| Configuration and env loading | config / transform | `AVSAR-main/AVSAR-main/services/core/config.py` | Copy the typed `BaseSettings` boundary and mock defaults | exact |
| Database session boundary | service utility / CRUD | `AVSAR-main/AVSAR-main/services/core/db.py` | Retain request-scoped and script-scoped SQLAlchemy sessions | exact |
| Compose topology and healthchecks | config / request-response health | `AVSAR-main/AVSAR-main/infra/docker-compose.yml` | Adopt AVSAR topology; add PostGIS deliberately in Phase 2 | exact |
| Makefile conventions | config / command orchestration | `AVSAR-main/AVSAR-main/Makefile` | Adopt `env`, `up`, `wait-healthy`, `seed`, `test`, `lint`, `drill`, `grounding`, `mock-on/off` | exact |
| Provider contract | service interface / streaming transform | `AVSAR-main/AVSAR-main/services/core/speech/base.py` | Copy interface/result/error shapes for every external provider | exact |
| Provider selection/failover | service / streaming | `AVSAR-main/AVSAR-main/services/core/speech/router.py` | Copy ladder, demotion, degraded metadata, and mock floor | exact |
| Mock provider | service / fixture-backed streaming | `AVSAR-main/AVSAR-main/services/core/speech/mock.py` | Copy fixture replay and deterministic failure variants | exact |
| API health/readiness | route / request-response | `AVSAR-main/AVSAR-main/services/core/api/health.py` | Copy `/healthz`, `/readyz`, `/metrics` semantics | exact |
| API route registration | application factory / request-response | `AVSAR-main/AVSAR-main/services/core/main.py` | Register unified `/v1` routers here; do not add a second gateway | exact |
| Auth and role handling | middleware/dependency / request-response | `AVSAR-main/AVSAR-main/services/core/api/security.py` and `auth.py` | Copy JWT, OTP-lite, Argon2id, role guards, and audit primitive | exact |
| Admin mutation/audit | controller / CRUD | `AVSAR-main/AVSAR-main/services/core/api/admin.py` | Adapt for canonical mapping writes and mandatory audit rows | role-match |
| CI workflow | config / batch verification | `AVSAR-main/AVSAR-main/.github/workflows/ci.yml` | Copy backend/frontend jobs and mock/no-network env | exact |
| Infrastructure acceptance tests | test / request-response + batch | `AVSAR-main/AVSAR-main/services/core/tests/test_gate0_infra.py` | Copy as Phase 1 gate structure; extend for unified contract | exact |
| Speech contract tests | test / streaming | `AVSAR-main/AVSAR-main/services/core/tests/test_gate5_speech.py` | Copy provider/mock/failure-ladder assertions | exact |
| KaushalVani route inventory | route / request-response | `KaushalVani-main/KaushalVani-main/backend/src/routes/api.routes.ts` | Use only as a migration inventory; map concepts into FastAPI `/v1` | partial |
| Roadmap vocabulary | controller/domain / transform | `KaushalVani-main/KaushalVani-main/backend/src/controllers/roadmap.controller.ts` | Adapt step concepts to canonical recommendation IDs and sourced facts | role-match |
| Outcome vocabulary | controller/domain / CRUD | `KaushalVani-main/KaushalVani-main/backend/src/controllers/outcome.controller.ts` | Adapt status vocabulary behind canonical IDs and RBAC | role-match |
| Beneficiary persona/language UX | provider/context / state transform | `KaushalVani-main/KaushalVani-main/frontend/src/context/BeneficiaryContext.tsx`, `LanguageContext.tsx` | Port Sita fixture, language/accessibility intent, not storage/API shape | partial |

## Pattern Assignments

### Canonical service entrypoint and route registration

**Analog:** `AVSAR-main/AVSAR-main/services/core/main.py` (untracked workspace reference; `create_app` line 36, `_include_optional` line 151)

Copy the application-factory shape. `create_app()` creates FastAPI, installs CORS, includes health first, then imports feature routers; the helper skips not-yet-landed routers without creating a second service. It also owns request metrics, SQLAlchemy-to-503 translation, generic speakable 500 responses, root metadata, and startup warm-up. Phase 1 should adapt this to a single `/v1` namespace and make the unified router list explicit once the contract is frozen.

```python
app = FastAPI(title="AVSAR Core API", ...)
app.include_router(health.router)
_include_optional(app, "core.api.auth")
_include_optional(app, "core.api.sessions")
...
@app.exception_handler(SQLAlchemyError)
async def database_down(...):
    return JSONResponse(status_code=503, content={"detail": error_payload(...)})
```

**Do not copy:** KaushalVani `backend/src/index.ts` as a runtime gateway. Its `app.use('/api', router)` and `app.listen` lines 32-39 are useful only as evidence of the old route inventory. Running it would create the forbidden second authority.

### Configuration and environment loading

**Analog:** `AVSAR-main/AVSAR-main/services/core/config.py` (untracked; `Settings` line 15, `get_settings` line 103)

Use one typed `pydantic-settings` object with `.env`, `extra="ignore"`, cached access, and defaults that make mock mode boot without credentials. Preserve separate runtime provider fields (`voice_provider`, `llm_provider`), database/Redis URLs, JWT durations, CORS, rate limits, retention, and demo credentials. Keep government hostnames out of runtime settings as this file does; ingestion-only configuration belongs in pipeline code.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
    llm_provider: str = "mock"
    voice_provider: str = "mock"
    allow_live_check: bool = False

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

KaushalVani `ai-service/main.py` uses `load_dotenv()` and reads provider values directly from `os.getenv`; do not adopt that split configuration pattern. It has permissive `allow_origins=["*"]` and no typed central contract.

### Compose, healthchecks, and Makefile

**Analogs:** `AVSAR-main/AVSAR-main/infra/docker-compose.yml` (untracked; services begin line 6) and `AVSAR-main/AVSAR-main/Makefile` (untracked; environment portability lines 6-7; targets `env`, `up`, `wait-healthy`, `seed`, `test`, `drill`, `mock-on`, `mock-off`, `ci-local`)

Adopt the four-service AVSAR shape: pgvector Postgres, Redis, FastAPI core, and Next web. Use `depends_on.condition: service_healthy`; healthcheck DB for both readiness and vector extension, Redis with `redis-cli ping`, core with `/healthz`, and web with its local `/api/health`. Keep container names and `wait-healthy` aligned or replace them consistently; do not merge KaushalVani's unhealthchecked Postgres 15 + Node backend + separate AI service topology.

Make targets should remain the operator contract: create `.env`, build/start, wait for all dependencies, migrate/seed, run lint/tests, run grounding and failure drills, and switch mock mode without editing source. Preserve `MSYS_NO_PATHCONV`/`MSYS2_ARG_CONV_EXCL` for Git Bash on Windows. Phase 1 should make `make up` prove one stack, not both repositories.

### Provider interfaces and mock implementations

**Analogs:** `AVSAR-main/AVSAR-main/services/core/speech/base.py` (`AsrResult` line 32, `TtsChunk` line 51, `ProviderError` line 69, `SpeechProvider` line 78), `speech/router.py` (`_build` line 39, `SpeechRouter` line 56, `get_router` line 237), and `speech/mock.py` (`_wav_bytes` line 54, `MockSpeechProvider` line 84)

Copy the contract-first boundary:

```python
class SpeechProvider(abc.ABC):
    @abc.abstractmethod
    def transcribe(self, audio_b64: str, lang: str, *, step: str | None = None) -> AsrResult: ...
    @abc.abstractmethod
    def synthesize(self, text: str, lang: str, *, step: str | None = None) -> list[TtsChunk]: ...
    def health(self) -> dict: ...
```

Retain explicit provider, language, confidence, latency, and `degraded` metadata. Adapt `SpeechRouter`'s configured-primary ladder, failure count, cooldown demotion, exception isolation, and guaranteed mock floor. `MockSpeechProvider` is load-bearing: fixture lookup by language/step, deterministic `empty`, `low_confidence`, `unknown`, and `gap` variants, sentence-level WAV chunks, and a health response that needs no network or key. Apply the same shape to any Phase 1 LLM/provider contracts.

### Health and readiness

**Analog:** `AVSAR-main/AVSAR-main/services/core/api/health.py` (`healthz` line 19, `readyz` line 25, `metrics` line 76)

Keep liveness cheap and dependency-free. Readiness should check DB connectivity, pgvector, Redis, and provider resolution; return `503` plus structured checks when a required dependency is down. Mock speech counts healthy by design. The Compose core healthcheck should call `/healthz`; Phase 1 verification should call `/readyz` separately to prove the full dependency contract.

### Auth, roles, and audit

**Analogs:** `AVSAR-main/AVSAR-main/services/core/api/auth.py` and `api/security.py` (untracked; JWT `create_token` line 85, `Principal` line 138, `current_principal` line 178, role guards lines 209-248, `audit` line 262)

Copy AVSAR's separation: auth routes issue phone OTP-lite tokens for beneficiaries and Argon2id-password JWT pairs for staff; security dependencies resolve a `Principal`; `require_viewer`, `require_officer`, and `require_admin` enforce route-level roles; `audit()` writes in the same transaction as an admin mutation. Preserve 30-minute access and 12-hour refresh defaults, language-aware error payloads, minimal beneficiary identity, and no anonymous mutation path.

Use KaushalVani's `api.routes.ts` auth line 17 only to identify legacy endpoints. Its hard-coded credentials and unconditional admin fallback are not an auth pattern to migrate.

### CI and verification structure

**Analogs:** `AVSAR-main/AVSAR-main/.github/workflows/ci.yml` (untracked; backend job line 13, frontend job line 64), `services/core/tests/test_gate0_infra.py` (tests lines 17-136), and `test_gate5_speech.py` (provider contract/mock sections)

Copy the CI split: backend service containers for pgvector Postgres and Redis, mock providers, hashing embeddings, dependency install, vector extension setup, Ruff, clean Alembic upgrade, pytest, and non-blocking pip audit; frontend runs `npm ci` fallback, typecheck, build, and non-blocking npm audit. Phase 1 should add the unified route/role/contract checks before later feature tests.

The gate-test pattern is executable acceptance evidence rather than file-existence checks alone. `test_gate0_infra.py` verifies `/healthz`, `/readyz`, pgvector, Postgres major version, metrics, monorepo layout, required Make targets, env coverage, secret hygiene, Compose healthchecks, and CI commands. `test_gate5_speech.py` verifies every named provider implements the same methods, audio format/languages, fixture coverage, mock journey, failure variants, TTS chunking, and fallback behavior. Adapt these tests to assert one canonical API and absence of an active KaushalVani runtime.

KaushalVani `scripts/test-scenarios.js` is useful as a scenario inventory (six beneficiary shapes and a recommendation-to-roadmap journey), but it assumes a live port 5001 and permissive JSON endpoints. Convert its scenarios into AVSAR pytest fixtures or HTTP contract tests; do not retain it as the Phase 1 CI command.

### KaushalVani concepts to adapt behind canonical contracts

**Roadmap:** `backend/src/controllers/roadmap.controller.ts` (untracked; lookup lines 4-24, step construction line 26). Preserve the concept sequence: baseline profile -> skill gap/qualification -> training -> certification -> wage opportunity -> enterprise alternative -> outcome tracking. Replace every synthesized default, fixed distance, salary, grant, and named centre with canonical database rows, provenance, freshness, consent, and `synthetic` flags. Link every step to the canonical recommendation ID and source record.

**Outcome:** `backend/src/controllers/outcome.controller.ts` is a vocabulary reference for training, completion, certification, employment/self-employment, placement, income band, feedback, and timestamps. Adapt these as validated enums and canonical foreign keys with role authorization and audit; do not copy its in-memory mutation behavior.

**Persona and language:** `frontend/src/context/BeneficiaryContext.tsx` (Sita fixture and reset/demo state lines 17-63) is a useful scenario seed, not a beneficiary persistence model. `frontend/src/context/LanguageContext.tsx` (supported languages line 3, accessibility state lines 191-228) contributes language labels, text-size, high-contrast, speech replay, and text fallback intent. Reconcile supported languages with AVSAR's `hi/mr/te/en`, consent gate, and server-side provider contract.

## Shared Patterns

### One runtime authority

Apply to all Phase 1 service, route, Compose, and CI work: AVSAR FastAPI + canonical Postgres/Redis + Next shell. KaushalVani Node/Express and standalone Python AI are reference-only during migration.

### Mock-first degraded operation

Apply to provider interfaces, readiness, tests, Compose, and Make targets: mock is selected by env, has explicit provider/degraded metadata, never needs credentials, and is the final fallback. Real provider calls remain server-side.

### Speakable structured errors

Apply to routes and readiness failures: AVSAR `main.py` translates DB failures to `503` with `error_payload` and hides tracebacks. Preserve stable machine code, localized human message, and retryability in the unified `/v1` error contract.

### Contract and provenance discipline

Apply to imported KaushalVani fields: canonical IDs, decimal NSQF values, source/version/freshness, consent scope, and `synthetic` propagation must survive profile, recommendation, roadmap, opportunity, outcome, and export boundaries. Never copy generated fallback facts from `recommendation.controller.ts`.

## No Tracked Analog Found

| Area | Result | Action before execution |
|---|---|---|
| AVSAR source tree | Files exist in workspace but are not in the current Git index | Track or otherwise establish the authoritative source snapshot; then re-run pattern mapping gate |
| KaushalVani source tree | Files exist in workspace but are not in the current Git index | Track the reference snapshot or record an approved external provenance source |
| KaushalVani CI workflow | No `.github/workflows` file was found | Use AVSAR CI as the baseline; do not infer a Kaushal CI contract |
| Flutter implementation | No Flutter source was found | Use the Phase 1 device spike only; default to AVSAR Next.js/PWA |
| PostGIS centre readiness | Existing patterns are pgvector/aggregate-oriented | Defer geometry and spatial readiness details to Phase 2 implementation |

## Recommended Execution Order

1. Promote the chosen AVSAR baseline into tracked canonical source and freeze the `/v1` endpoint, role, consent, provenance, and source-field mapping.
2. Adapt `main.py`, `config.py`, Compose, Make, health, and CI as one runnable foundation; prove clean startup and readiness.
3. Copy the provider contracts/router/mock and add provider contract tests before any live adapter work.
4. Copy AVSAR auth/security patterns; map KaushalVani roadmap/outcome/profile concepts into canonical IDs without adding the Node or AI services.
5. Port Sita/scenario and accessibility vocabulary into AVSAR tests/UI only after the backend contract is stable.

## Metadata

**Analog search scope:** `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/research/SUMMARY.md`, AVSAR `services/core`, `infra`, `pipelines`, `scripts`, `.github`, and KaushalVani `backend/src`, `frontend/src/context`, `scripts`, `docker-compose.yml`
**Files scanned:** 18 selected analogs plus architecture/research/planning documents
**Pattern extraction date:** 2026-09-28