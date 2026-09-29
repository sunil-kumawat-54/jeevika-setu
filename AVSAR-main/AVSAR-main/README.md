# Jeevikasetu — Voice-First Livelihood Bridge

**Jeevikasetu** combines the verified AVSAR implementation with selected KaushalVani concepts to provide multilingual, voice-first livelihood mapping and NSQF-aligned skilling recommendations for communities served by the PM-AJAY Grant-in-Aid programme. AVSAR remains the internal runtime heritage; Jeevikasetu is the unified product and active architecture.

## Files

| File | Read this when… |
|---|---|
| **`research.md`** | You need the evidence. Every claim adversarially verified against primary sources; refuted claims listed in Appendix A so you never quote them. Feeds slides S4/S6 directly. |
| **`PLAN.md`** | You're deciding what/when. Personas, MVP scope, recommendation algorithm, dialogue design, phase-by-phase build, hour-by-hour finale plan, risk register, judging map. |
| **`ARCHITECTURE.md`** | You're building. Monorepo layout, component diagram, data model, API contract, voice/LLM/RAG subsystems, deployment. |
| **`TECH_STACK.md`** | You need exact libs/endpoints/env vars. Pinned dependencies, Bhashini/Sarvam/Kaushalverse contracts, performance budgets. |
| **`FABLE_PROMPT.md`** | You want it built. Paste the prompt into Fable 5; it reads all four files and executes gate-by-gate. |

## Technical Approach

### Architecture decisions

- **One runtime authority:** `services/core` is the only business-logic and provider-egress authority. The Next.js app never calls government portals, speech vendors, LLM vendors, or the database directly.
- **Versioned contract:** public FastAPI routes use `/v1`. Browser code calls `/api/core/*`; the Next.js BFF adds exactly one `/v1` prefix upstream.
- **Deterministic core, generative shell:** SQL rows, scoring, eligibility, crosswalks, and spatial queries authorize facts. Generated language only verbalizes those facts.
- **Provider abstraction:** speech and LLM providers are selected server-side. Failures produce explicit degraded metadata and speech always has a fixture-backed mock floor.
- **Snapshots over scraping:** ingestion pipelines create committed JSON snapshots. Runtime requests never scrape government endpoints.
- **Privacy-safe spatial data:** centre geometry is stored with verification and freshness state. Beneficiary home coordinates are not stored; nearby results require a coarse origin and bounded radius.

### Technology choices

| Layer | Technology | Role |
|---|---|---|
| Web | Next.js 14, React, TypeScript, Tailwind | Beneficiary PWA, officer dashboard, admin console |
| API | Python 3.12, FastAPI, Uvicorn | Sessions, auth, speech, recommendations, exports, health |
| Database | PostgreSQL 16 | Canonical relational data and audit records |
| Spatial | PostGIS geography and GiST | Database-side radius filtering and distance ordering |
| Search | pgvector HNSW, PostgreSQL FTS, `pg_trgm` | Hybrid semantic and lexical retrieval |
| Cache | Redis 7 | Rate limits, session/cache paths, provider/TTS cache |
| Speech | Bhashini, Sarvam, Azure, local Whisper, mock | ASR/TTS provider ladder |
| Operations | Docker Compose, Make, GitHub Actions | Repeatable startup, seed, tests, lint, grounding, and drills |

## Project Workflow

1. **Startup:** Compose starts PostgreSQL/PostGIS, Redis, FastAPI, and Next.js. Health-gated dependencies prevent the API from starting before its database and cache are available.
2. **Session creation:** The PWA creates a session through `POST /v1/sessions` and receives a state-machine snapshot.
3. **Consent and profile:** The conversation asks for missing slots, captures consent before durable storage, and retains minimal structured data. No beneficiary name is required.
4. **Voice or text turn:** Audio or text is sent to `POST /v1/sessions/{id}/turn`. Audio passes through the server-side speech router; text remains a first-class fallback.
5. **Candidate generation:** The crosswalk and hybrid retrieval produce candidate IDs from informal multilingual input.
6. **Canonical authorization:** Candidate IDs are joined to canonical qualification, programme, opportunity, and centre rows. Retrieval text never authorizes a fact by itself.
7. **Spatial filtering:** PostGIS applies `ST_DWithin` and `ST_Distance` using a coarse origin and validated radius. Missing, stale, rejected, and out-of-radius centres are not presented as nearby facts.
8. **Grounded response:** The verbalizer receives structured tool results. Numeral and fact checks reject unsupported generated content and fall back to a safe template.
9. **Operations:** Officers use role-protected dashboards and exports; admin edits are audited. Synthetic records remain visibly labeled.
10. **Ingestion:** Offline pipelines normalize source snapshots, preserve provenance, calculate stable fingerprints, and upsert records using natural keys.

## Data and Grounding Policy

Every canonical record carries source identity and appropriate freshness, verification, fingerprint, and `synthetic` metadata. Synthetic data is allowed for an honest offline demo but is never presented as verified government data.

The system must never invent qualification names, QP codes, decimal NSQF levels, seats, distances, salaries, grants, or opportunities. Decimal values such as NSQF `4.5` are preserved through migration, ORM, loaders, and API responses. See [docs/ingest-report.md](docs/ingest-report.md) for the current source-by-source status.

## Installation and Setup

### Prerequisites

- Docker Desktop with the Linux engine enabled
- Docker Compose v2+
- GNU Make for the shortest command workflow
- Git

Python, Node.js, PostgreSQL, Redis, and provider API keys are not required on the host for the mock Docker demo.

### Docker setup

```bash
git clone <repository-url>
cd AVSAR-main
cp .env.example .env
docker compose -f infra/docker-compose.yml --env-file .env up -d --build db redis core web
docker compose -f infra/docker-compose.yml --env-file .env exec -T core alembic -c services/core/alembic.ini upgrade head
docker compose -f infra/docker-compose.yml --env-file .env exec -T core python scripts/load_demo.py
```

The shorter equivalent is:

```bash
make up
make seed
```

Verify the runtime:

```bash
curl http://localhost:8000/v1/healthz
curl http://localhost:8000/v1/readyz
docker compose -f infra/docker-compose.yml --env-file .env ps
```

On Windows, if Docker is installed but not visible in a VS Code PowerShell session, add Docker Desktop's CLI directory for that session:

```powershell
$dockerDir = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
$env:Path = "$dockerDir;$env:Path"
docker version
```

### Host development

Host development requires Python 3.12, Node 20, PostgreSQL 16 with pgvector/PostGIS, and Redis 7:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/core/requirements.txt
pip install -r services/core/requirements-dev.txt
export PYTHONPATH=services
alembic -c services/core/alembic.ini upgrade head
python scripts/load_demo.py
python -m uvicorn core.main:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
cd apps/web
npm ci
npm run dev
```

## Usage

Open [http://localhost:3000](http://localhost:3000), select a language, grant consent, complete the profile prompts, and describe an aspiration such as `I want to learn tailoring work.` The PWA supports microphone input when permission is available and always keeps text interaction available.

The officer portal is available at [http://localhost:3000/dashboard](http://localhost:3000/dashboard). Default demo accounts are:

| Role | Email | Password |
|---|---|---|
| Viewer | `viewer@demo` | `avsar-demo-2026` |
| Officer | `officer@demo` | `avsar-demo-2026` |
| Admin | `admin@demo` | `avsar-demo-2026` |

The mock beneficiary OTP is `123456` unless `MOCK_OTP` is changed.

### Direct API example

```bash
curl -X POST http://localhost:8000/v1/sessions \
	-H 'content-type: application/json' \
	-H 'x-avsar-lang: hi' \
	-d '{"channel":"pwa","lang":"hi"}'
```

Then submit a text turn as an SSE request:

```bash
curl -N -X POST http://localhost:8000/v1/sessions/<SESSION_ID>/turn \
	-H 'content-type: application/json' \
	-H 'x-avsar-lang: hi' \
	-d '{"text":"I want to learn tailoring work"}'
```

Typical events are `transcript`, `state`, `recs`, `tts`, and `error`.

## API Overview

| Endpoint | Purpose |
|---|---|
| `GET /v1/healthz` | Liveness check |
| `GET /v1/readyz` | Database, Redis, provider, and LLM readiness |
| `POST /v1/auth/login` | Officer/viewer/admin login |
| `POST /v1/auth/request-otp` | Beneficiary OTP request |
| `POST /v1/auth/verify-otp` | Beneficiary OTP verification |
| `POST /v1/sessions` | Create a conversation session |
| `POST /v1/sessions/{id}/turn` | Submit text/audio/DTMF and receive SSE |
| `GET /v1/sessions/{id}/summary` | Read a session summary |
| `POST /v1/sessions/{id}/confirm-rec` | Confirm a recommendation |
| `POST /v1/recommendations/grounded` | Read canonical recommendations and nearby centres |
| `GET /v1/dashboard/stats` | Officer aggregates |
| `GET /v1/dashboard/gap` | Demand/supply gaps |
| `GET /v1/exports/*` | Role-protected CSV/XLSX exports |
| `GET/PUT /v1/admin/crosswalk` | Admin crosswalk review |
| `POST /v1/admin/reembed` | Rebuild a compatible vector index |
| `GET /v1/metrics` | Prometheus-style metrics |

All non-success responses use a structured error payload with a stable code, localized human text, and retryability metadata.

## Project Structure

```text
AVSAR-main/
├── apps/web/                  # Next.js PWA, dashboard, admin, and BFF
├── services/core/
│   ├── api/                   # FastAPI routers and contracts
│   ├── domain/                # Session, scoring, eligibility, recommendations
│   ├── speech/                # Provider interface, adapters, router, fixtures
│   ├── rag/                   # Embeddings and lexical/vector retrieval
│   ├── models/                # SQLAlchemy models
│   ├── alembic/               # Linear migration history
│   └── tests/                 # Gate and integration tests
├── pipelines/                 # Offline source ingestion
├── seeds/                     # Committed data and speech fixtures
├── data/crosswalk/            # Curated aspiration-to-QP mappings
├── infra/                     # Compose, database image, init SQL
├── scripts/                   # Seed, grounding, drill, latency, verification
├── docs/                      # Runbook, provenance, decisions, migration map
├── Makefile                   # Operator command vocabulary
├── .env.example               # Mock-first configuration
├── ARCHITECTURE.md            # Detailed design
├── TECH_STACK.md              # Dependency/provider reference
└── PLAN.md                    # Product plan and acceptance gates
```

## Testing and Verification

```bash
make lint
make test
make grounding
python scripts/verify_client_contract.py --base-url http://localhost:8000/v1 --lang hi
python scripts/verify_service_worker_safety.py
```

Focused Phase 2 gates:

```bash
python -m pytest -q services/core/tests/test_gate1_models.py
python -m pytest -q services/core/tests/test_gate2_ingestion.py
python -m pytest -q services/core/tests/test_gate_phase2_data.py
python -m pytest -q services/core/tests/test_gate_phase2_spatial.py
python -m pytest -q services/core/tests/test_gate_phase2_retrieval.py
python -m pytest -q services/core/tests/test_gate4_recommender.py
python scripts/verify_grounding.py --n 50
```

The grounding check verifies that generated numerals and named recommendation facts came from authorized tool/database results. It is a zero-invention integrity gate, not a general language-quality benchmark.

## Contributing

1. Read [ARCHITECTURE.md](ARCHITECTURE.md), [TECH_STACK.md](TECH_STACK.md), and the relevant plan before changing a subsystem.
2. Keep `services/core` as the single business-logic authority.
3. Add focused tests for every behavior or contract change.
4. Preserve source, version, freshness, verification, fingerprint, and `synthetic` metadata in derived data.
5. Do not add request-time government scraping or browser-side provider calls.
6. Never commit `.env`, API keys, raw beneficiary audio, or unreviewed personal data.
7. Run lint, focused tests, and grounding verification where applicable.
8. Update documentation and ingest reports when data policy or runtime behavior changes.

For data changes, document the source snapshot, natural key, fingerprint behavior, and synthetic policy. For API changes, update versioned contract tests and the BFF path if necessary.

## License

No license file is currently present in the active Jeevikasetu/AVSAR repository. Until the maintainers add a project license, treat the source as **all rights reserved** and obtain permission before redistribution or commercial use. Third-party dependencies retain their own licenses.

## Project Status

Completed and verified:

- Phase 1: unified FastAPI authority, versioned `/v1` contract, provider mock floor, CI grounding, and Next.js/PWA decision.
- Phase 2: provenance-aware canonical schema, decimal-safe NSQF/QP identity, deterministic ingestion, PostGIS spatial queries, grounded retrieval, and 50-session grounding verification.
- Docker runtime: PostgreSQL/PostGIS, Redis, FastAPI, and Next.js build and run together.

Next implementation boundary:

- Phase 3: multilingual voice, conversation, consent, profile extraction, facilitator mode, and resilient text/audio interaction.

Known limitations:

- Some centre and catalogue records are synthetic by design and remain visibly labeled.
- E5 and mock hashing embeddings are separate vector spaces; incompatible semantic recall is disabled until the index is rebuilt with a matching backend.
- Physical Android accessibility/device evidence is still pending.
## The 30-second version

Jeevikasetu is the missing front door: speak your aspiration in Hindi/Marathi/Telugu → get a grounded course recommendation with assistance facts → officers get a livelihood map and AAP-ready exports. It uses committed source snapshots, canonical provenance, PostGIS spatial queries, provider failover, and a mock mode that survives dead venue wifi.

## Quickstart — full offline demo, zero API keys

**Prereqs: Docker Desktop and GNU Make. Nothing else.** No Python, Node,
Postgres or Redis on the host; no API key of any kind; no internet after the
images are built. Everything below was run end to end on a clean Windows 11
machine with Docker 28 and GNU Make 4.4.

```bash
git clone <repo> && cd AVSAR
cp .env.example .env     # mock-first defaults are already set: no keys needed
make up                  # builds + starts db, redis, core, web; waits for healthy
make seed                # migrations + committed seeds + demo users + vector index
```

`make up` prints `ALL HEALTHY` when the four containers pass their healthchecks
(first build takes a few minutes; it downloads the embedding model once).

Open **http://localhost:3000** and press **बात शुरू करें / Start conversation**. The whole beneficiary
journey runs offline on `VOICE_PROVIDER=mock` + `LLM_PROVIDER=mock`: language →
spoken consent → five profile slots → spoken aspiration → grounded NSQF
recommendations → summary. Provider egress happens only if you put real keys in
`.env` and run `make mock-off`.

**Officer console:** http://localhost:3000/dashboard — seeded logins
`officer@demo`, `viewer@demo`, `admin@demo`, password from
`DEMO_*_PASSWORD` in `.env` (default `avsar-demo-2026`). Officers get the
district dashboard, the gap panel and CSV/XLSX export; admin adds the audited
crosswalk console.

Useful afterwards: `make ps` (container status), `make logs SVC=core`,
`make down` (stop, keep data), `make clean` (stop and delete the volume).

### Checks — each must exit 0

| Command | What it actually proves |
|---|---|
| `make lint` | ruff over `services pipelines scripts` |
| `make test` | the backend suite against a live Postgres |
| `make grounding` | RULE 2: across 50 randomised sessions, every numeral in the verbalized recommendation exists in the tool JSON, and no course name or QP code was invented |
| `make drill` | kill-a-service: network off (incl. a real `--network none` container), database stopped, provider key revoked — all three degrade gracefully and recover |
| `make latency` | drives real journeys and reports per-stage p50/p95 against the ARCHITECTURE §3 budget |
| `make purge` | retention policy dry-run (`DAYS=30 APPLY=--apply` to delete) |

> `make test` runs against the same database the demo uses and leaves the demo
> data intact. If a dashboard ever looks empty, `make seed` is idempotent — run
> it again.

### Without Docker

The stack is plain FastAPI + Next.js if you would rather run it on the host —
you need Python 3.12, Node 20, Postgres 16 with `pgvector`, and Redis:

```bash
pip install -r services/core/requirements.txt -r services/core/requirements-ml.txt
export PYTHONPATH=services
alembic -c services/core/alembic.ini upgrade head
python scripts/load_demo.py
python -m uvicorn core.main:app --port 8000       # core API
cd apps/web && npm ci && npm run dev              # web on :3000
```

### Honesty about the data

The demo runs on committed `seeds/*.json`, never by scraping a government site
at request time (RULE 3). Some of it is **synthetic**, because the PM-AJAY
portal was serving a maintenance page throughout the build. Synthetic records
carry `synthetic=true` from ingestion through the database, the dashboard badge,
the CSV/XLSX export and the compliance sheet — they are never presented as real
government data. What is real (785 LGD districts, 1,170 NCVET qualifications,
the 43-page GIA guidelines) and what is not is itemised in
[docs/ingest-report.md](docs/ingest-report.md).

Ops procedures (retention purge cron, rate-limit tuning, troubleshooting) live in [docs/runbook.md](docs/runbook.md); architecture in [ARCHITECTURE.md](ARCHITECTURE.md), build order + gate evidence in [PLAN.md](PLAN.md).

## Presentation artifacts

