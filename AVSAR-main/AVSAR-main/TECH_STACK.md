# TECH_STACK.md — Exact Technologies, Endpoints & Configuration

> Every choice below is justified by a research finding in `research.md` (section refs inline). Companion: `ARCHITECTURE.md`, `PLAN.md`, `FABLE_PROMPT.md`.
> Versions are "known-good as of Aug 2026" — pin at install time; don't chase latest during the hackathon.

---

## 1. Stack summary

| Layer | Choice | Why (research anchor) |
|---|---|---|
| Backend | **Python 3.12 + FastAPI + Uvicorn** | Async-first for SSE voice turns; team familiarity; fastest path to tool-calling LLM integration |
| DB | **PostgreSQL 16 + pgvector 0.7+** | One DB for relational + vector + BM25 (tsvector); fewer moving parts at 3 a.m. |
| Cache | **Redis 7** | Session FSM cache, rate-limit counters, TTS phrase cache |
| Frontend | **Next.js 14 (App Router) + TypeScript + Tailwind** | PWA support; one codebase for beneficiary UI + dashboard + admin console |
| Voice ASR/TTS | **Bhashini ULCA (primary) → Sarvam (secondary) → mock (always-available)** | Govt-sanctioned path (PoC license OK ✅ R-§5.2); Sarvam ₹30/hr STT + failover precedent from Jugalbandi ✅ |
| Embeddings | **multilingual-e5-base** (`intfloat/multilingual-e5-base`, 768-dim) | Strong cross-lingual retrieval hi/mr/te↔en; self-hosted = zero marginal cost |
| LLM | **Claude (Sonnet-class) via Anthropic API** for verbalizer+NLU fallback; strict tool-use | Reliable structured function calling; Hindi/Marathi/Telugu quality; pay-per-token fits demo scale. Open-model swap documented (Llama-3.x-Indic / Airavata) for the sovereignty roadmap slide |
| RAG chunk store | Postgres tsvector + pgvector HNSW | Hybrid retrieval without extra services |
| Auth | **JWT (PyJWT) + argon2id (argon2-cffi)**; OTP-lite adapter pattern | PLAN §5 auth spec |
| IVR (Phase 2) | **Exotel trial account** → `ivr-bridge` (FastAPI WS) ; Twilio documented alternative | Feature-phone reach per Avaaj Otalo evidence ✅ |
| Deploy | Docker Compose on single VPS; Caddy TLS; ngrok for venue | ARCH §10 |
| CI | GitHub Actions: ruff + mypy(light) + pytest + next build | Freeze-quality gate |

---

## 2. External APIs — exact contracts

### 2.1 Bhashini ULCA ✅ (PoC license — fine for SIH)

```
Onboarding:  https://bhashini.gov.in/ulca/user/register#  → verify email → login
Keys:        https://bhashini.gov.in/ulca/profile  ("Generate")   # app name: lowercase+underscores only
Key cap:     5 keys/integrator

# Step 1 — Pipeline Config (fixed URL):
POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
Headers: { userID: <user_id>, ulcaApiKey: <api_key>, Content-Type: application/json }
Body: { "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": "hi"}}}],
        "pipelineRequestConfig": {"id": "<uuid4>"} }
→ response.pipelineInferenceAPIEndPoint.callbackUrl      # inference URL — DYNAMIC, never hardcode
→ response.pipelineInferenceAPIEndPoint.inferenceApiKey.name    # header NAME — dynamic
→ response.pipelineInferenceAPIEndPoint.inferenceApiKey.value   # header VALUE — dynamic
→ task entries carry serviceId per task

# Step 2 — Pipeline Compute (dynamic URL/headers from above):
POST {callbackUrl}
Headers: { "<name-from-config>": "<value-from-config>" }
Body: { "pipelineTasks":[{"taskType":"asr","input":[{"source":""}],"audio":[{ "audioContent": "<base64 wav>" }],
         "config": {"language":{"sourceLanguage":"hi"},"audioFormat":"wav","transcriptionFormat":{"value":"unspecified"}}}] }
Task chains allowed in one call: [ASR] [NMT] [TTS] [ASR+NMT] [NMT+TTS] [ASR+NMT+TTS]
Model explorer: https://bhashini.gov.in/ulca/model/explore-models
Docs: https://bhashini.gitbook.io/bhashini-apis
```

Adapter rules: cache config responses ~10 min per (task,lang); retry once on 5xx then demote provider.

### 2.2 Sarvam AI ✅ (paid fallback; ₹100 free credits)

```
Base:   https://api.sarvam.ai/v1            Docs+pricing: https://docs.sarvam.ai/api/getting-started/pricing.md
Auth:   Header api-subscription-key
STT:    POST /speech-to-text   (multipart audio)   ₹30/hr; diarization ₹45/hr
TTS:    POST /text-to-speech   Bulbul v2 ₹15/10K chars (v3 beta ₹30)
Translate: POST /translate    ₹20/10K chars       LangID: ₹3.5/10K
Limits: Starter 60 req/min account-wide · Pro 200 · Business 1000   # batch canned prompts ahead of demo
```

### 2.3 Data ingestion endpoints ✅ (offline pipelines only; snapshots committed)

```bash
# PM-AJAY GIA course catalogue (~2,360 rows, QP-coded; NO nsqf level inside)
GET  https://pmajay.dosje.gov.in/course-list                 # grab CSRF token + session cookie
POST https://pmajay.dosje.gov.in/front/reportajax            # body: module_type=5&sector_id=all
     Headers: X-CSRFToken, Cookie, Referer: .../course-list

# Kaushalverse (NCVET) — open JSON, no auth:
GET https://kaushalverse.ncvet.gov.in/assets/config/env.json
GET https://kaushalverse.ncvet.gov.in/digigov/homepage/getAllQualApprovedFiles?pageNumber=N   # 20/page ×~71
GET https://kaushalverse.ncvet.gov.in/digigov/homepage/getQualDetailsBasedOnVersionId?versionId=ID
GET https://kaushalverse.ncvet.gov.in/digigov/homepage/getAllRecognisedAB
POST https://kaushalverse.ncvet.gov.in/digigov/homepage/filterQualForms?pageNumber=N  # {"search":"tailor"}

# Cross-check register (HTML scrape, robots allows): https://nqr.gov.in/qualifications/{id}
# Guidelines PDFs (ingest into RAG):
https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf   # OPERATIVE (43 pp)
https://ncvet.gov.in/wp-content/uploads/2022/08/NSQF.pdf                    # gazette
```

Politeness: 1 req/s, identify UA, cache to `seeds/raw/`. If any endpoint 403s at build time, ship with committed seed snapshot (already included).

### 2.4 Optional telephony (Phase-2 stretch)

- Exotel: trial number → inbound call applet → WebSocket stream to `ivr-bridge`; DTMF captured natively.
- Twilio India: document constraints page in runbook; not primary.
- WhatsApp: Meta Cloud API webhook receives voice notes (ogg/opus) → same `/turn` path; reply with audio document. Timebox 4h; skip without regret.

---

## 3. Python dependency pins (services/core/requirements.txt)

```
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.9.*
sqlalchemy==2.0.*          psycopg[binary]==3.2.*
pgvector==0.3.*
alembic==1.13.*
redis==5.0.*
httpx==0.27.*
anthropic==0.34.*          # or current; pin whatever installs
pyjwt==2.9.*               argon2-cffi==23.*
argon2-benchmark           # dev only if needed
openai-whisper             # NOT used at runtime; see note
faster-whisper==1.0.*      # OPTIONAL self-host fallback (IndicWhisper weights)
ctranslate2                # faster-whisper runtime
soundfile==0.12.*          pydub==0.25.*      ffmpeg (system pkg)
pandas==2.2.*              openpyxl==3.1.*    # exports
python-multipart           aiofiles
tenacity==8.5.*            # provider retries
ruff (dev)  pytest==8.*  pytest-asyncio  coverage
```

Notes:
- **Do not use vanilla OpenAI Whisper for the demo** — IndicVoices shows >90% WER on spontaneous Marathi/Telugu ✅. If self-hosting, fetch AI4Bharat IndicWhisper per-language checkpoints (MIT ✅) and run through faster-whisper/CTranslate2 on CPU.
- multilingual-e5 via `sentence-transformers==3.*`; encode with `"query:"`/`"passage:"` prefixes (model requirement).

## 4. Web dependency pins (apps/web/package.json essentials)

```
next@14.2.*  react@18.3.*  typescript@5.5.*
tailwindcss@3.4.*  @headlessui/react@2.*  lucide-react
recharts@2.12.*                      # dashboard charts (accessible defaults)
zustand@4.5.*                        # dialogue FSM client state
recordrtc OR native MediaRecorder    # mic capture → wav 16k mono
idb-keyval                           # IndexedDB draft queue (offline)
next-pwa(workbox)                    # service worker; cache-first static, network-only API
react-simple-maps@3.*                # district choropleth (or SVG map component)
```

Audio capture contract: 16 kHz mono WAV, ≤15 s per turn, opus→wav server-side if WhatsApp source.

## 5. Environment variables (.env.example)

```bash
# Core
ENV=demo                     # demo|prod
DATABASE_URL=postgresql+psycopg://avsar:avsar@db:5432/avsar
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me         JWT_ACCESS_MIN=30  JWT_REFRESH_H=12
# LLM
ANTHROPIC_API_KEY=           CLAUDE_MODEL=claude-sonnet-4-5   LLM_MAX_TOKENS=512
# Speech providers
VOICE_PROVIDER=bhashini      # bhashini|sarvam|azure|mock
BHASHINI_USER_ID=            BHASHINI_API_KEY=
BHASHINI_CONFIG_URL=https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
SARVAM_API_KEY=
AZURE_SPEECH_KEY=            AZURE_SPEECH_REGION=
VOICE_TIMEOUT_S=8            PROVIDER_DEMOTE_AFTER=2
# Ingestion (pipelines only)
PMAJAY_BASE=https://pmajay.dosje.gov.in
KAUSHALVERSE_BASE=https://kaushalverse.ncvet.gov.in
INGEST_QPS=1
# Demo switches
MOCK_OTP=123456              SEED_DEMO_USERS=true
```

Never commit real keys. Venue checklist: keys loaded? credits left? provider health endpoint green? mock toggle reachable in one command (`make mock-on`).

## 6. Model artifacts (self-host fallbacks; download in Phase 1, store on USB)

| Artifact | Source | Size class | Use |
|---|---|---|---|
| IndicWhisper hi checkpoint | github.com/AI4Bharat/vistaar release ZIPs (E2E store links in README table) | ~1–3 GB | offline ASR fallback (CPU via faster-whisper) |
| multilingual-e5-base | HF `intfloat/multilingual-e5-base` | ~1.1 GB | embeddings (also runs in pipeline only) |
| Bhashini/Sarvam TTS samples | record 20 fixture lines in Phase 1 | MBs | mock-mode playback + dead-network demo |

## 7. Commands (Makefile targets the builder must implement)

```make
up          # docker compose up -d db redis core web (+ --profile full for ivr-bridge)
seed        # load seeds/*.json into DB, create demo users, build vector indexes
dev         # uvicorn reload + next dev concurrently
test        # pytest -q && npm -C apps/web run test --if-present
ingest      # run pipelines 01–07 in order (writes seeds/, idempotent)
drill       # scripts/kill_service_drill.sh  # network-off, db-stop, key-revoke scenarios
grounding   # python scripts/verify_grounding.py --n 50
mock-on/off # flip VOICE_PROVIDER in running core (env file + restart core svc)
```

## 8. Performance budget & measurement

Instrument each stage with `time.monotonic()` around: upload_end→asr_final, retrieval_start→end, llm_first_token, tts_first_byte. Emit to logs + `/metrics`. Targets (from Farmer.Chat precedent ✅): p50 ≤9 s, p95 ≤15 s end-to-end; regression alert in CI if unit-test harness sim exceeds budgets by >20%.

## 9. Security quick-list

- All provider calls server-side only; browser never sees BHASHINI_*/ANTHROPIC_* keys.
- CORS locked to web origin; rate-limit `/auth/*` and `/sessions/*/turn` via Redis token bucket.
- Audio blobs never persisted beyond session TTL unless consent granted (default off).
- SQL injection safe (ORM only); YAML crosswalk validated against schema on load.
- Dependency audit in CI (`pip-audit`, `npm audit --production`) — warnings non-blocking, criticals block merge.
