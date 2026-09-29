# Jeevikasetu

## What This Is

Jeevikasetu, "Bridging Skills to Brighter Futures," is a voice-first, multilingual livelihood mapping and skilling platform for SC communities under the PM-AJAY Grant-in-Aid component. A beneficiary or facilitator speaks about work, education, aspirations, and location; the system builds a structured profile, maps informal skills to NSQF-aligned qualifications, recommends grounded training or RPL pathways and nearby opportunities, and tracks outcomes through certification and livelihood. Organizations, district officers, and administrators use a role-aware portal for opportunities, matching, analytics, exports, and governance.

This project combines the strongest verified implementation surfaces from the existing AVSAR and KaushalVani codebases into one coherent platform: AVSAR's mock-first offline journey, FastAPI core, grounded recommendation safeguards, committed data pipelines, and officer console; and KaushalVani's explicit livelihood roadmap, accessible beneficiary journey, multilingual voice framing, and modular AI-service boundaries.

## Core Value

A low-literacy beneficiary can speak in a local language and receive a trustworthy, explainable, locally relevant path from existing skills to a better livelihood, even when providers or connectivity fail.

## Business Context

- **Customer**: PM-AJAY implementing agencies, district/state officers, CSC facilitators, training providers, and livelihood organizations.
- **Revenue model**: Not defined for the hackathon; deployment is public-program and grant-funded.
- **Success metric**: A complete grounded beneficiary journey from consent through recommendation and outcome tracking in offline mock mode, with zero invented facts.
- **Strategy notes**: `JEEVIKASETU-GSD-PRD.md` is the product and acceptance source document.

## Requirements

### Validated

(None yet — the combined product must be verified as one system.)

### Active

- [ ] Deliver the v1 requirements defined in `.planning/REQUIREMENTS.md` across voice, profile, knowledge base, recommendations, beneficiary experience, portal, outcomes, security, and operations.
- [ ] Preserve the PRD's non-negotiables: voice with text fallback, database-grounded facts, mock providers, explainability, synthetic-data honesty, privacy by design, and graceful degradation.
- [ ] Merge the AVSAR and KaushalVani implementation assets without retaining conflicting duplicate sources of truth for business logic, data, or provider integration.
- [ ] Demonstrate the full Sita-like journey offline: consent, profile slots, aspiration, grounded recommendation with nearby centre, and outcome update.

### Out of Scope

- Payments or grant disbursement — explicitly excluded by the PRD and not required for the hackathon demo.
- Hosting training content or issuing official certifications — the platform tracks pathways and outcomes but does not replace training or certifying authorities.
- Biometric or Aadhaar-linked identity verification — privacy and scope boundary.
- Live government API dependencies in the request path — committed seed snapshots and offline ingestion are required for reliability and honest demos.
- v2 entry doors (WhatsApp/IVR), direct live NQR/Skill India/NCS/PM-AJAY integrations, premium analytics, dialect adaptation, and advanced assessment tools — design for extension, defer implementation.

## Context

- The source workspace contains `AVSAR-main/AVSAR-main`, an advanced FastAPI + Next.js PWA implementation with PostgreSQL/pgvector/PostGIS-oriented data, ingestion pipelines, mock providers, grounding checks, offline drills, latency reports, and dashboard/admin surfaces.
- The source workspace contains `KaushalVani-main/KaushalVani-main`, a React/Vite frontend, Node/Express backend, Python FastAPI AI service, PostgreSQL schema, multilingual voice UX, demo persona, and API/deployment documentation.
- The PRD's decided target stack is Flutter beneficiary app, Next.js organization/admin portal, Python/FastAPI core, provider-abstracted LLM and voice services, PostgreSQL/PostGIS/pgvector, Docker Compose, and GitHub Actions. The Flutter versus Next.js beneficiary-client choice is explicitly open and should be resolved by a focused spike before the client phase.
- The primary demonstration persona is Sita: a 24-year-old agricultural labourer, 10th-pass, interested in solar/electrical work, with a 15 km mobility radius. Existing projects already contain closely related seeded/demo data and should be reconciled rather than duplicated.
- The combined system must remain usable with no API keys or internet after images are built. Synthetic records must remain marked end-to-end.

## Constraints

- **Architecture**: Use a single coherent backend source of truth; clients must not call government portals or AI vendors directly.
- **Grounding**: Qualification names, QP codes, NSQF levels, durations, centres, jobs, and numeric facts must come from database/tool output; generated language can explain but cannot invent.
- **Provider resilience**: STT, TTS, LLM, and embeddings require real and mock implementations selected by environment configuration.
- **Accessibility**: Voice-first interaction, text fallback, audio replay, high contrast, scalable type, screen-reader labels, and touch targets of at least 72 px.
- **Privacy**: Consent before storage, minimal PII, server-side RBAC, auditability, encryption, configurable retention, and no raw-audio retention by default.
- **Performance**: Audio round-trip p95 target under 4 seconds per turn, with measured stage-level latency and graceful degradation.
- **Delivery**: Docker Compose and Make targets must start, seed, test, lint, ground, drill, and measure the full journey in mock mode.
- **Repository**: Planning is initialized inside the existing outer Git worktree at `C:/Users/Asus/OneDrive/Desktop/SIH Code Lab`; no nested repository should be created.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Jeevikasetu is the unified product name and scope | AVSAR and KaushalVani implement the same PM-AJAY livelihood journey; one product avoids duplicated business logic | — Pending |
| AVSAR's FastAPI/Next.js offline-first core is the initial integration anchor | It already contains the strongest grounding, seed, drill, latency, and dashboard patterns | — Pending |
| KaushalVani assets are integrated selectively behind the unified contracts | Its journey, accessibility, demo persona, and service boundaries add useful coverage without preserving a second backend truth | — Pending |
| Facts are deterministic and generated language is a verbalization layer | Prevents hallucinated government data and supports automated grounding tests | — Pending |
| Mock mode is a first-class deployment mode | Enables judging, development, and recovery testing without API keys or network access | — Pending |
| Beneficiary client choice remains a spike | Flutter is the PRD default, but AVSAR's mature PWA may reduce delivery risk; the decision should be evidence-based | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections.
2. Core Value check: still the right priority?
3. Audit Out of Scope: reasons still valid?
4. Update Context with current state, users, feedback, and metrics.

---
*Last updated: 2026-09-28 after initialization*
