# Jeevikasetu — GSD Core Build Brief

> **How to use:** Save this file in your empty project root, install GSD Core, then run
> `/gsd-new-project --auto @JEEVIKASETU-GSD-PRD.md`
> GSD will ingest this file, run its research agents, and create `.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`. Section 11 has the full command runbook.

---

## 1. Project

**Name:** Jeevikasetu — "Bridging Skills to Brighter Futures"
**Tagline:** From Voice → Skills → Better Livelihood Opportunities
**Event:** Smart India Hackathon 2026 · Problem Statement ID 97 · Software · Ministry of Social Justice and Empowerment (MoSJE)
**Problem statement:** AI-driven voice assistant for livelihood mapping and NSQF-aligned skilling recommendations for SC communities under the GIA component of PM-AJAY.

**One-paragraph vision:** A voice-first, multilingual platform where a beneficiary (often low-literacy, low-bandwidth) speaks about their work, education, and goals in a local language. The system builds a structured livelihood profile, finds the gap between existing skills and NSQF qualification requirements, recommends training / RPL pathways with nearby centres and local opportunities, explains *why*, and tracks the person from training to certification to livelihood. Organizations and district officers use a portal to post opportunities, find matching beneficiaries, and see district/block analytics.

**Users**
| Persona | Needs |
|---|---|
| Beneficiary (SC community member, may be low-literacy) | Talk instead of type, local language, simple recommended pathway, nearby training, reason for recommendation |
| Facilitator (CSC operator / field worker) | Onboard someone else on their behalf, shared device use |
| Training provider / organization | Post courses & jobs, find eligible candidates, monitor progress |
| District / state officer (authority) | Skill-gap heatmaps, funnel from enrolment → certification → livelihood, exports |
| Admin | Manage users, roles, knowledge-base sources |

---

## 2. Non-negotiable principles (apply to every phase)

1. **Voice-first, text always available.** Every voice step has a text fallback. Large touch targets (≥ 72 px for the hold-to-speak button), audio replay, high contrast.
2. **Grounding over generation.** Qualification names, QP codes, NSQF levels, durations, centres, and job listings come **only** from the database/knowledge base. The LLM may phrase and explain; it must never invent a course, code, number, or centre. Enforced by an automated grounding test (see §9).
3. **Provider abstraction with mock mode.** STT, TTS, LLM, and embeddings sit behind interfaces with `real` and `mock` implementations. The complete beneficiary journey must run with zero API keys and no internet (`VOICE_PROVIDER=mock`, `LLM_PROVIDER=mock`).
4. **Explainable recommendations.** Every recommendation returns a score breakdown and human-readable "why this was recommended".
5. **Honest data.** Any synthetic/seed record carries `synthetic=true` end-to-end (DB, API, UI badge, exports). Never scrape government sites at request time; use committed seed files + offline ingestion scripts.
6. **Privacy by design.** Spoken consent up front, minimal PII, encryption at rest and in transit, role-based access, audit log, retention policy.
7. **Graceful degradation.** Provider down, DB slow, network off → the app still responds with a clear fallback.

---

## 3. Tech stack (from the submitted slides — treat as decided unless a spike says otherwise)

| Layer | Choice |
|---|---|
| Beneficiary app | Flutter (Android + PWA/web build) |
| Org / Admin portal | React / Next.js |
| Backend API | Python + FastAPI (REST + WebSocket) |
| AI / NLP | LLM + LangChain (provider-agnostic) |
| Voice | Bhashini (Indian-language STT/TTS/translation) primary; Whisper fallback; mock provider |
| Database | PostgreSQL + PostGIS |
| Vector store | pgvector (Chroma acceptable for dev) |
| Maps | Leaflet.js (Mapbox optional) |
| Charts | Recharts / Chart.js |
| Auth | JWT + role-based access control (beneficiary, facilitator, organization, officer, admin) |
| Hosting | Containerised (Docker Compose locally); AWS / Azure / GCP deployable |
| Version control / CI | GitHub + GitHub Actions |

**Open decision D-01 (run `/gsd-spike`):** Flutter vs. a Next.js PWA for the beneficiary client. Slides say Flutter. Comparable projects (AVSAR) use Next.js for both. Default: Flutter, unless the spike shows Bhashini/WebSocket audio streaming or mic permission handling is materially worse.

**Constraint:** keep dependencies minimal and audited; every new package goes through GSD's package-legitimacy check.

---

## 4. Architecture (12 components from the slide)

```
[1 Beneficiary Input]  voice/text, local language, Flutter app
        │  API / WebSocket
[2 Voice & Language Processing]  STT · language detection · TTS
        │
[3 AI / NLP Engine]  intent · information extraction · profile generation · conversation manager
        │
[4 Livelihood Profile]  skills · education · experience · aspirations · location · preferences
        │
[5 Skill Gap Analysis] ◄── [6 NSQF Knowledge Base]  (roles, QPs, skill reqs, training/RPL pathways)
        │
[8 Recommendation Engine] ◄── [7 Local Opportunity Data]  (centres, workshops, jobs, local demand)
   AI + rules · personalised pathway · explainable
        │                              │
[9 Beneficiary Output]          [10 Org / Admin Portal + Dashboard & Reports]
        │                              │
        └────────► [11 PostgreSQL+PostGIS] ◄────────┘
                          │
                  [12 Outcome Tracking]  enrolment · certification · employment · impact
                          └─► continuous-improvement feedback loop → 7, 8
```

**Suggested monorepo layout**
```
/apps/mobile          Flutter beneficiary app
/apps/portal          Next.js org/admin portal
/services/core        FastAPI (api, voice, conversation, profile, gap, recommend, tracking)
/services/core/providers   stt/, tts/, llm/, embeddings/  (real + mock)
/pipelines            ingestion scripts (NSQF/QP, centres, jobs) → /seeds
/seeds                committed JSON/CSV seed data (flagged synthetic where applicable)
/infra                docker-compose, Dockerfiles, CI workflows
/docs                 ARCHITECTURE.md, API.md, DATA_SOURCES.md, decisions.md
/scripts              demo persona loader, grounding test, latency test
Makefile              up, seed, test, lint, grounding, drill, latency
```

---

## 5. Requirements (IDs are stable — plans must cite them)

### v1 (must ship for the hackathon demo)

**Voice & language**
- **VOI-01** Beneficiary can speak and receive spoken replies in at least Hindi, English, and one more Indian language (default: Marathi or Telugu; target list configurable).
- **VOI-02** Language is auto-detected or chosen with one tap on the first screen.
- **VOI-03** STT/TTS run through a provider interface (Bhashini, Whisper, mock) selected by env var.
- **VOI-04** Text input and audio replay available on every conversational step.
- **VOI-05** Audio round trip meets a latency budget (target p95 < 4 s per turn; measured by `make latency`).

**Conversation & profile**
- **CNV-01** Consent is requested and recorded (spoken + tap) before any data is stored.
- **CNV-02** Conversation manager asks only for *missing* profile slots (skills, education, experience, aspirations, location, preferences) and accepts free-form answers.
- **CNV-03** Information extraction converts speech to a structured profile with confidence per field; low-confidence fields are confirmed back to the user.
- **CNV-04** Beneficiary can ask open questions mid-flow (e.g., "how long is this course?") answered from the knowledge base.
- **PRF-01** Profile stored in PostgreSQL; editable by beneficiary/facilitator.
- **PRF-02** Facilitator mode: start a profile "for someone else" from a shared device.

**Knowledge base & data**
- **KB-01** NSQF knowledge base: job roles, qualification packs (QP code, NSQF level, sector), required skills, duration, training and RPL pathways, with `source` and `last_verified` fields.
- **KB-02** Embeddings of roles/skills in pgvector for semantic matching of informal descriptions ("I fix motors") to formal roles.
- **KB-03** Local opportunity data: training centres (PostGIS geometry), workshops/programmes, job/self-employment opportunities, local demand by district/block.
- **KB-04** Seed + ingestion pipeline is idempotent (`make seed` can be re-run safely).

**Skill gap & recommendation**
- **GAP-01** Compare profile skills to the target role's required skills and return matched and missing skills.
- **REC-01** Recommendation engine combines rule-based filters (eligibility, education, distance, language) with AI/semantic matching.
- **REC-02** Output includes: recommended pathway (training and/or RPL → certification → livelihood), nearby centres sorted by distance, relevant opportunities, and the reason for recommendation.
- **REC-03** Every recommendation exposes a multi-factor score breakdown.
- **REC-04** Grounding guarantee: every course name, QP code, number, and centre in a spoken/written recommendation exists in the tool/DB output (test in §9).

**Beneficiary app**
- **APP-01** Mic-first home screen, no forms, minimal text, icon-led navigation.
- **APP-02** Results screen: pathway steps, map of nearby centres, jobs, "why this", audio playback.
- **APP-03** Works on low-end Android and on poor connectivity (offline queue for profile data; clear retry states).
- **APP-04** Accessibility: high-contrast mode, scalable type, screen-reader labels.

**Org / admin portal**
- **ADM-01** Organizations can post training courses, workshops, and job opportunities.
- **ADM-02** Organizations can find matching beneficiaries (filters: skill, district/block, language, NSQF level) with privacy-respecting views.
- **ADM-03** Officer dashboard: district/block skill-gap map (Leaflet), demand vs supply charts, program funnel.
- **ADM-04** Role-based access: beneficiary, facilitator, organization, officer, admin.
- **ADM-05** CSV/XLSX export of dashboard data with synthetic-data flags preserved.

**Outcome tracking**
- **OUT-01** Track status: recommended → enrolled → training → certified → employed / self-employed.
- **OUT-02** Organizations/officers can update statuses; beneficiaries can confirm.
- **OUT-03** Impact analytics feed back into ranking of pathways and local-demand data.

**Security & platform**
- **SEC-01** JWT auth, RBAC enforced server-side, refresh/expiry handled.
- **SEC-02** Encryption in transit (TLS) and at rest for sensitive fields; secrets only via env.
- **SEC-03** Audit log for data access by non-beneficiary roles.
- **SEC-04** Configurable retention/purge policy for raw audio and transcripts (default: do not store raw audio after transcription).
- **SEC-05** Rate limiting and input validation on all public endpoints.
- **NFR-01** `docker compose up` (or `make up`) starts everything; `make seed` loads demo data; full journey works in mock mode offline.
- **NFR-02** CI runs lint, unit/integration tests, and the grounding test on every PR.

### v2 (design for it, don't build now)
- WhatsApp / IVR (toll-free) entry doors sharing the same backend, tagged with `entry_mode`
- Direct live integration with NQR / Skill India Digital / NCS / PM-AJAY APIs
- Premium analytics tier, CSR/grant reporting, labour-market insights
- Additional languages beyond the first set, dialect adaptation
- Assessment tools and advanced skilling pathways

### Out of scope
- Payments or disbursement of grants
- Building or hosting training content itself
- Replacing official certification issuing
- Biometric or Aadhaar-linked identity verification

---

## 6. Data model (starting point — planner may refine)

- `users(id, role, language, created_at, …)`
- `beneficiaries(id, user_id?, facilitator_id?, consent_at, district_lgd, block, geom, language, entry_mode)`
- `profiles(id, beneficiary_id, education, experience_years, current_occupation, aspirations, preferences, mobility_radius_km, confidence jsonb, version)`
- `skills(id, name, embedding vector, source)` · `profile_skills(profile_id, skill_id, level, confidence)`
- `job_roles(id, name, sector, embedding)` · `qualifications(id, qp_code, name, nsqf_level, duration_hours, source, last_verified)`
- `role_skill_requirements(role_id, skill_id, importance)` · `qualification_pathways(qualification_id, type[training|rpl], prerequisites)`
- `training_centres(id, name, geom, district, contact, qualifications[])` · `opportunities(id, org_id, type[job|self_employment|workshop], geom, district, demand_score)`
- `recommendations(id, profile_id, qualification_id, score, score_breakdown jsonb, explanation, created_at)`
- `outcomes(id, recommendation_id, status, updated_by, updated_at)`
- `consents`, `audit_log`, and `synthetic boolean` on every seedable table

---

## 7. API contract (sketch)

- `POST /v1/sessions` start session (language, consent, entry_mode)
- `WS  /v1/sessions/{id}/stream` audio/text turns in, transcript + reply + TTS audio out
- `GET/PATCH /v1/profiles/{id}`
- `POST /v1/profiles/{id}/gap-analysis` → matched + missing skills
- `POST /v1/profiles/{id}/recommendations` → ranked pathways with `score_breakdown` and `explanation`
- `GET /v1/centres?near=lat,lng&qualification=…`
- `GET/POST /v1/opportunities` (org) · `GET /v1/candidates` (org, filtered)
- `GET /v1/analytics/district/{lgd}` · `GET /v1/exports/…` (officer)
- `PATCH /v1/outcomes/{id}`
- `POST /v1/auth/login|refresh`, `GET /v1/health`

Full OpenAPI generated by FastAPI and committed to `/docs/API.md`.

---

## 8. Suggested roadmap (GSD phases)

Each phase ends with something demoable and verifiable.

| # | Phase | Goal | Requirements |
|---|---|---|---|
| 1 | **Foundation** | Monorepo, Docker Compose, CI, env/secrets, provider interfaces with mock implementations, health endpoints, Makefile | NFR-01, NFR-02, VOI-03 (interfaces) |
| 2 | **Data & NSQF knowledge base** | Schema + migrations, seeds, ingestion scripts, pgvector embeddings, PostGIS centres, `synthetic` flagging | KB-01..04 |
| 3 | **Voice pipeline** | STT/TTS/language detection through Bhashini + Whisper + mock; WebSocket turn loop; latency measurement | VOI-01..05 |
| 4 | **Conversation & profile engine** | Consent flow, slot filling, extraction with confidence, profile persistence, KB Q&A | CNV-01..04, PRF-01..02 |
| 5 | **Skill gap & recommendation engine** | Gap analysis, rule + semantic ranking, distance via PostGIS, explainability, grounding test | GAP-01, REC-01..04 |
| 6 | **Beneficiary Flutter app** | Mic-first UI, results screen, map, offline queue, accessibility (run `/gsd-ui-phase`) | APP-01..04 |
| 7 | **Org/Admin portal** | Post opportunities, candidate matching, RBAC, officer dashboard, Leaflet map, exports (run `/gsd-ui-phase`) | ADM-01..05, SEC-01 |
| 8 | **Outcome tracking & feedback loop** | Status pipeline, funnels, feedback into ranking | OUT-01..03 |
| 9 | **Security & privacy hardening** | Encryption, audit log, retention purge, rate limiting, consent records | SEC-01..05 |
| 10 | **Demo readiness & submission** | Persona seed, offline drill, latency report, demo script/video shotlist, README, architecture docs | all (audit) |

Phases 6 and 7 can run in parallel workstreams after phase 5 (`/gsd-workstreams`).

---

## 9. Acceptance criteria and quality gates

- **Journey test:** a scripted persona (e.g., 24-year-old agricultural labourer, 10th pass, interested in solar/electrical work, 15 km mobility) completes: consent → 5 profile slots → aspiration → recommendation with nearest centre → outcome status update, in mock mode, offline.
- **`make grounding`:** across ≥ 50 randomised sessions, every numeral, course name, QP code, and centre in the verbalised recommendation exists in the DB/tool JSON. Zero invented entities.
- **`make drill`:** network off, DB stopped, and provider key revoked each degrade gracefully and recover.
- **`make latency`:** reports per-stage p50/p95 for STT, LLM, retrieval, TTS.
- **`make lint` / `make test`:** exit 0 in CI.
- **RBAC tests:** each role can access only its allowed endpoints.
- **Accessibility check:** contrast and touch-target audit on the beneficiary app.
- **Explainability check:** every recommendation payload contains `score_breakdown` and `explanation`.

---

## 10. Risks and mitigations (from the submitted feasibility slide)

| Risk | Mitigation |
|---|---|
| Sensitive beneficiary data | Encryption, RBAC, consent, retention purge, no raw-audio storage by default |
| Integration with government platforms and heterogeneous data | Standard APIs, modular adapters, seed-first design, `source`/`last_verified` |
| Low digital literacy and adoption | Voice-first UI, facilitator mode, deployment via CSCs/training centres |
| Incomplete/inconsistent data | Confidence scores, confirm-back prompts, `synthetic` flags, data-quality checks in ingestion |
| Provider outage / poor venue network | Mock and fallback providers, offline queue, `make drill` |
| LLM hallucination | Grounded tool outputs, verbalisation-only LLM role, automated grounding test |

---

## 11. GSD Core runbook

**Install (GSD Core, the community-maintained continuation of Get Shit Done):**
```
npx @opengsd/gsd-core@latest --claude --global
claude --dangerously-skip-permissions     # GSD is designed for this; use only in a trusted, sandboxed repo
```
> Package names have moved during the original project's transition. If the command above fails, check the `open-gsd/gsd-core` README for the current install line. Verify with `/gsd-help`. Do **not** install the old `get-shit-done-cc` package.

**Bootstrap**
```
/gsd-new-project --auto @JEEVIKASETU-GSD-PRD.md
/gsd-settings        # suggested: mode interactive, granularity standard, profile balanced, research on, plan-check on, verifier on
```

**Feasibility spikes before planning (recommended)**
```
/gsd-spike "Bhashini STT/TTS latency and streaming for Hindi and one regional language"
/gsd-spike "Flutter vs Next.js PWA for mic capture + WebSocket audio on low-end Android"
/gsd-spike "pgvector semantic match of informal skill descriptions to NSQF roles"
/gsd-spike --wrap-up
```

**Per-phase loop (repeat for phases 1–10)**
```
/clear
/gsd-discuss-phase N
/gsd-ui-phase N          # only phases 6 and 7
/gsd-plan-phase N
/gsd-execute-phase N
/gsd-code-review N --fix
/gsd-verify-work N
/gsd-ship N              # optional PR per phase
/gsd-progress --next     # if unsure what's next
```

**Finish**
```
/gsd-audit-milestone
/gsd-complete-milestone
```

**Discuss-phase decisions to lock early (write into CONTEXT.md)**
- Target languages for the demo and which provider is primary per language
- Flutter vs PWA (D-01) outcome from the spike
- Which LLM provider for the real mode and the fallback order
- Which government datasets are ingested for real vs shipped as synthetic seeds
- Consent wording (reviewed by a domain expert or NGO partner)

---

## 12. Reference projects (similar problem, comparable architecture)

Studied while preparing this brief. Use them for ideas and patterns, not for copying code. Check each licence before reusing anything.

| Repo | Why it's relevant |
|---|---|
| `Akshat-code17/AVSAR` | Closest match: FastAPI + Next.js + Postgres/pgvector + Redis, Bhashini voice, RAG, mock-first offline mode, grounding test, kill-a-service drill, latency budget, synthetic-data flagging, officer dashboard with exports |
| `DIPAK-RATHOD/KaushalVani` | Modular monolith (React/Vite + Node/Express + Python FastAPI AI service + Postgres), Bhashini ASR/TTS, explainable multi-factor scoring, personalised roadmap, UX4G/GIGW accessible UI, district officer dashboard, docker-compose |
| `varuntutejaa/Saksham` | Mobile (Expo) + website + server, 10 Indian languages, Sarvam/Whisper/Bhashini STT fallback chain, RAG knowledge base, large real NSQF/PM-AJAY course seed, WhatsApp webhook |
| `bandarivinaygoud28-ui/jeevika-ai` | Open-ended conversational counsellor that asks only for missing info, livelihood readiness assessment, transparent scoring |
| `subash9940/AI-livelihood-guidance-assistant` | Three entry doors (app, facilitator handoff, IVR simulation) against one backend, 4-step roadmap generation |
| `sjkaran/livelihood_SIH` | Minimal Flask + Whisper + gTTS/pyttsx3 offline fallback pipeline, officer dashboard, text fallback for every voice step |
| `Roshanshinde123/Disha-Sarthi`, `Potri2357/KuralSevi` | Same problem statement; multilingual voice-first intake, explainable recommendations, district planning views |

**Patterns adopted from them:** mock-provider mode (AVSAR, livelihood_SIH), automated grounding test (AVSAR), "zero government data hallucination" principle and score breakdown (KaushalVani), facilitator handoff and multiple entry modes (subash9940), real NSQF seed data (Saksham), fallback chains for STT (Saksham, livelihood_SIH).

**Differentiators to keep from the Jeevikasetu slides:** two-sided platform (beneficiaries + organizations), Flutter mobile app, PostGIS-based local opportunity and district analytics, closed-loop outcome tracking feeding recommendations.
