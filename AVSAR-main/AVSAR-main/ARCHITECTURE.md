# ARCHITECTURE.md — Project AVSAR System Design

> Companion files: `research.md` (why), `PLAN.md` (what/when), `TECH_STACK.md` (exact libs/endpoints), `FABLE_PROMPT.md` (build instructions).

---

## 1. Monorepo layout

```
avsar/
├── apps/
│   ├── web/                    # Next.js PWA (beneficiary flow + dashboard + admin) 
│   │   ├── app/(beneficiary)/  # voice conversation screens
│   │   ├── app/dashboard/      # officer views (role-gated)
│   │   ├── app/admin/          # crosswalk console (admin role)
│   │   └── app/api/            # BFF route handlers (thin proxy to core API)
│   └── ivr-bridge/             # OPTIONAL Phase-2: WebSocket media bridge for telephony
├── services/
│   └── core/                   # FastAPI: all business logic, one deployable
│       ├── api/                # routers: sessions, recommendations, ingest, admin, auth, exports
│       ├── domain/             # pure logic: scoring, eligibility, capability ceiling
│       ├── llm/                # provider adapters, tool schemas, guardrail post-checks, prompts/
│       ├── speech/             # provider abstraction: bhashini | sarvam | azure | mock
│       ├── rag/                # chunking, embedding jobs, hybrid retrieval
│       └── models/             # SQLAlchemy ORM + Pydantic schemas
├── pipelines/                  # one-shot ingestion scripts 01–07 (see PLAN §5.1)
├── data/
│   ├── crosswalk/*.yaml        # curated aspiration→QP mappings (the moat artifact)
│   └── prompts/dialogue.{hi,mr,te,en}.json
├── seeds/                      # committed snapshots: pmajay_courses.json, kaushalverse/*.json, fixtures/
├── infra/
│   ├── docker-compose.yml      # postgres+pgvector, redis, core, web; profile:full adds ivr-bridge
│   └── nginx.conf
├── scripts/                    # verify_grounding.py, kill_service_drill.sh, load_demo.py
├── docs/                       # ingest-report.md, crosswalk-method.md, runbook.md
├── Makefile                    # up, seed, dev, test, drill, freeze-tag
└── .env.example
```

Rule: `services/core` is the single source of truth; the Next.js app never talks to gov portals or LLM providers directly — everything goes through core's API (keeps keys server-side and lets IVR reuse identical logic).

## 2. Component diagram

```
                        ┌──────────────────────────── Browser (PWA) ────────────────────────────┐
                        │  Beneficiary voice UI        Officer dashboard        Crosswalk console│
                        │  (mic · captions · chips)    (map/charts/export)      (review table)   │
                        └───────┬──────────────────────────┬────────────────────────┬──────────┘
                                │ HTTPS/JSON (+audio blobs)│                        │
┌──────────────┐   optional     ▼                          ▼                        ▼
│ Feature phone│   Exotel/Twilio ┌──────────────────────────────────────────────────────────────┐
│ (IVR, DTMF)  │◄────────────────┤  apps/ivr-bridge : WS media ↔ same /session protocol         │
└──────────────┘                 └──────────────────────────────┬───────────────────────────────┘
                                                                │ REST (JWT)
        ┌───────────────────────────────────────────────────────▼───────────────────────────────┐
        │                            services/core (FastAPI)                                     │
        │                                                                                        │
        │  Session FSM ──► Speech Router ──► NLU/Slotter ──► Recommender ──► Verbalizer          │
        │                     │                   │                 │               │           │
        │            ┌────────┴────────┐   multilingual-e5    pgvector+BM25   LLM (tools-only)   │
        │            ▼                 ▼            retrieval        │  ▲ post-hoc fact check    │
        │     [bhashini] [sarvam] [azure] [mock]   (crosswalk+QP     │  │                        │
        │      ASR/TTS chains  failover→     descriptions+guidelines)▼  │                        │
        └──────────────┬──────────────────────────────────┬──────────┴───────────────┬──────────┘
                       │ HTTPS (server-side keys only)     │ SQL                      │ read-only
                ┌──────▼───────┐                  ┌────────▼─────────┐       ┌────────▼────────┐
                │ Bhashini ULCA │                  │ Postgres 16      │       │ Redis           │
                │ Sarvam APIs   │                  │ + pgvector       │       │ session cache,  │
                │ Azure (fail)  │                  │ users/sessions/  │       │ rate-limit,     │
                └──────────────┘                   │ courses/quals/   │       │ TTS phrase cache│
                                                   │ crosswalk/docs/  │       └─────────────────┘
                                                   │ centre_supply/   │
                                                   │ audit_log        │
                                                   └────────▲─────────┘
                                                            │ loads seeds
                                    ┌───────────────────────┴───────────────────────────┐
                                    │ pipelines/01–07 → seeds/ (committed snapshots):    │
                                    │ pmajay.dosje.gov.in · kaushalverse.ncvet.gov.in ·  │
                                    │ guidelines PDFs · synthetic centre_supply          │
                                    └───────────────────────────────────────────────────┘
```

Design invariants:
1. **Provider abstraction everywhere** (`speech/`, `llm/`) — every external dependency has a `mock` twin selected by env var; demo never hard-depends on any vendor.
2. **Seeds over live fetches**: gov endpoints are ingested offline into committed snapshots; live fetch is an optional garnish endpoint clearly labeled in UI.
3. **Deterministic core, generative shell**: DB/scoring decides facts; LLM only verbalizes tool outputs and is post-checked (any numeral in output must exist in the tool JSON, else regenerate→template fallback).
4. **One brain, many ears**: PWA mic, recorded audio, and IVR all feed the same `/sessions/{id}/turn` protocol.

## 3. Key sequence — one voice turn (happy path)

```
Client                core/sessions              speech router        recommender        LLM
  │ POST /turn {audio?|text?, state} │                │                    │              │
  ├─────────────────────────────────►│                │                    │              │
  │                                  │ if audio: ASR ─►│ (lang from session │              │
  │                                  │◄─ transcript+conf│ or LID sniff)     │              │
  │                                  │ FSM advance: slot fill / intent parse               │
  │                                  │ if intent complete: build_candidates() ─►           │
  │                                  │                  C=C1∪C2∩eligibility, score, top3   │
  │                                  │ verbalize(structured_recs) ─────────────────────────►│
  │                                  │◄────────────────── text (tool-grounded) ────────────│
  │                                  │ post_check(text, tool_json): numerals ⊆ json?       │
  │                                  │   ok → proceed ; fail → regen once → template       │
  │                                  │ TTS sentence-chunks ◄─ speech router (streaming)    │
  │◄─ SSE {state, transcript, recs[], tts_url|audio_stream, suggestions[]}                 │
```

Latency budget (target ≤9 s p50, precedent Farmer.Chat 9.05 s ✅):
ASR final ≤2.5 s (short utterances) · retrieval+scoring ≤0.5 s · LLM first token ≤1.5 s · TTS first byte ≤1.5 s · overlap where possible (start TTS of sentence N while generating N+1).

## 4. Data model (Postgres)

```sql
users(id PK, role ENUM('beneficiary','viewer','officer','admin'), phone UNIQUE NULL, email UNIQUE NULL,
      password_hash NULL, lang_pref, created_at)                       -- beneficiary rows are phone-only
consents(id PK, session_id FK, mode ENUM('spoken','tapped'), granted bool, ts, playback_ref)

sessions(id PK, user_id FK NULL, channel ENUM('pwa','ivr','whatsapp','demo'),
         lang, state JSONB,            -- FSM snapshot: current step, slots, retries
         district_code, age_band, gender, edu_level, current_work,
         consent_id FK, created_at, ended_at, degraded bool)          -- degraded=true when fallback used

transcripts(id PK, session_id FK, turn_no, asr_provider, raw_text, confidence real,
            parsed_slots JSONB, latency_ms)

courses(id PK, qp_code, sector, sub_sector, course, sub_course,
        nsqf_level NUMERIC(3,1) NULL, hours_min INT NULL, hours_max INT NULL,
        credits NUMERIC NULL, source ENUM('pmajay','kaushalverse','both'))  -- seeded ~2,360/~1,893 QPs

qualifications(id PK, nqr_code, version_id BIGINT, name, category,        -- Kaushalverse detail cache
               nsqf_level NUMERIC(3,1), sector, min_hours, max_hours,
               th_hrs, pr_hrs, ojt_hrs, es_hrs, credits_min, credits_max,
               eligibility JSONB, progression_vertical TEXT, valid_till DATE,
               fetched_at)

qp_descriptions(id PK, course_id FK, embedding VECTOR(768))               -- multilingual-e5

crosswalk(id PK, phrase TEXT, lang, gia_domain SMALLINT CHECK(1..10),
          qp_codes TEXT[], status ENUM('auto','reviewed'),
          reviewed_by FK NULL, version INT, updated_at)                   -- the moat table

doc_chunks(id PK, source ENUM('pmajay_gia_2023','nsqf_gazette'), page INT,
           section TEXT, chunk TEXT, embedding VECTOR(768))

centre_supply(id PK, district_code, qp_code, centre_name, seats INT,
              synthetic bool DEFAULT true)                                -- honesty flag surfaces in UI

recommendations(id PK, session_id FK, rank SMALLINT, course_id FK, score REAL,
                factors JSONB, verbalized TEXT, grounded bool)

audit_log(id PK, actor FK, action, entity, entity_id, before JSONB, after JSONB, ts)  -- officer edits
```

Indexes: `courses(qp_code)` unique; `centre_supply(district_code,qp_code)`; HNSW on both vector columns; `sessions(district_code, created_at)`.

District codes: use Census 2011 LGD-style codes (state+district); a static `districts(code,name_hi,name_en)` seed ships in-repo.

## 5. API contract (v1, JWT unless noted)

```
POST /auth/request-otp {phone}            → {otp_hint}        # mock mode returns fixed OTP
POST /auth/verify-otp {phone, otp}        → {access_token}
POST /auth/login {email, password}        → {access_token}    # officers/admin
POST /sessions {channel, lang}            → {session_id, state}
POST /sessions/{id}/turn {text?|audio_b64?, dtmf?} → SSE stream:
        events: transcript{...} | state{step,slots} | recs[{qp_code,...}] | tts{url|chunk_b64} | error{code}
POST /sessions/{id}/confirm-rec {course_id} → {summary_text, summary_lang}
GET  /sessions/{id}/summary               → printable/text summary
GET  /dashboard/stats?district&from&to    → {by_domain[], top_concepts[], women_pct, priority_income_pct}
GET  /dashboard/gap?district              → [{concept, demand_n, supply_seats}]
GET  /exports/sessions.csv | /exports/aap.xlsx                # officer+
GET/PUT /admin/crosswalk[/{id}]                               # admin; writes audit_log
POST /admin/reembed                       → job id            # rebuild vector index after edits
GET  /healthz | /readyz                                        # readyz pings DB+providers(mock counts ok)
```

Error contract: every non-2xx carries `{code, human_{lang}, retryable}` so the client can SPEAK errors ("network issue, aap phir koshish karein").

## 6. Voice subsystem

- **SpeechRouter** picks provider per call: `VOICE_PROVIDER=mock|bhashini|sarvam|azure`; runtime health probe demotes a failing provider automatically (Jugalbandi failover pattern ✅).
- **Bhashini adapter**: config call to fixed URL with `userID`+`ulcaApiKey` headers; inference URL + auth header name/value READ FROM CONFIG RESPONSE each time (hardcoding breaks ✅). Chains `[ASR]`, `[TTS]`, or `[ASR+NMT+TTS]`.
- **Mock provider**: replays fixture WAVs/transcripts from `seeds/fixtures/` keyed by dialogue step — full flow works airplane-mode.
- **Streaming rules**: TTS synthesized per-sentence; first sentence dispatches while later ones generate; mic stays open for barge-in; echo-cancel via browser AEC.
- **DTMF (IVR)**: tones map to menu indices; digits always accepted wherever speech options appear.
- **LID front-end**: first utterance scored by keyword-spotting/LID (IndicSUPERB task list justifies ✅); low-confidence → ask language again.

## 7. LLM layer & guardrails

- Tools exposed to the model (strict schemas): `search_courses(query, filters)`, `get_qualification(qp_code)`, `scheme_fact(question)` (RAG w/ citations), `compute_assistance(course_cost_band)` (returns guideline constants ₹50k/50% project-cost).
- System prompt contract: "You may ONLY state facts present in tool results. If absent, say you don't know and offer handoff." Output post-check enforces numerals ⊆ tool JSON (regex extract + compare).
- Language policy: reason in English internally, respond in session language, back-translation pattern (Farmer.Chat evidence ✅).
- Refusal/handoff: scheme-advice outside GIA scope → polite redirect + officer-callback flag set on session.

## 8. Retrieval (two stores, one interface)

1. **Structured lookup** (primary for recommendations): SQL against courses/quals/crosswalk/centre_supply — deterministic, testable.
2. **Hybrid RAG** (for open scheme questions): BM25 (Postgres tsvector w/ Hindi analyzer config 'simple' + custom stopwords) ∩ pgvector cosine (multilingual-e5-normalized), reciprocal-rank fusion, top-6 chunks into `scheme_fact`.

## 9. AuthN/AuthZ

- Beneficiary: phone → OTP-lite (mock OTP printed to server log in demo; pluggable SMS adapter for prod). No password. Minimal PII: no name required ever.
- Officers: email+password (argon2id), roles viewer/officer/admin; route-level guards + row-level (individual beneficiary rows hidden from `viewer`).
- JWT access 30 min + refresh 12 h; all admin mutations audited (`audit_log`).
- Consent record bound to session before any profile slot is stored; consent playback endpoint for verification.

## 10. Deployment & ops

- `docker compose --profile full up`: `db(pg16+pgvector)`, `redis`, `core`, `web`, optional `ivr-bridge`, caddy/nginx TLS terminator.
- Single VPS (4 vCPU/8 GB) suffices for finale + pilot scale; embeddings computed in pipelines, not at request time (except crosswalk edits → async reindex job).
- Backups: nightly `pg_dump` to object storage; `seeds/` are in git anyway.
- Observability: structured JSON logs w/ session_id correlation; `/metrics` (Prometheus-format) counting turns, provider failures, degradation switches, latencies per stage; simple Grafana dashboard optional.
- Runbook (`docs/runbook.md`): venue checklist (wifi hotspot backup, USB, ngrok auth token, volume levels), kill-drill procedure, OTP demo values, judge-login accounts.

## 11. Privacy & compliance posture (build-time)

- Data minimization by schema (no name column exists); district-level aggregation for public views.
- Spoken-consent capture stored as data (mode/ts/playback ref) — demonstrable DPDP-style consent trail.
- Keys only in `.env` (gitignored); provider calls egress exclusively from `services/core`.
- Retention: sessions purgeable by script after N days (`scripts/purge_old.py`) for the pilot story.
