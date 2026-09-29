# Jeevikasetu Requirements

## Product Boundary

Jeevikasetu is a voice-first, multilingual livelihood mapping and skilling platform for SC communities under PM-AJAY GIA. It must let a beneficiary or facilitator move from consent and lived experience to a grounded, explainable NSQF pathway, nearby opportunity, and tracked outcome. Organizations and officers use the same canonical backend for opportunities, matching, analytics, exports, and governance.

The v1 system has one public FastAPI `/v1` contract and one canonical PostgreSQL migration set. AVSAR is the runtime and data-integration anchor. KaushalVani is source material for reviewed domain vocabulary, journey presentation, accessibility intent, persona fixtures, and outcome concepts; its Node gateway, standalone AI service, duplicate schema, and ungrounded fallback facts are not v1 runtime authorities.

## V1 Requirements

Every requirement below is atomic, user-observable, and assigned to exactly one roadmap phase in the traceability table.

### Voice And Language

- **VOI-01** Beneficiary can speak and receive spoken replies in Hindi, English, and one configured additional Indian language.
- **VOI-02** Beneficiary can choose a language with one tap on the first screen, or the system can detect it and show the selected language.
- **VOI-03** STT and TTS are selected through server-side provider interfaces with real and mock implementations, including Bhashini, Whisper/fallback, and mock configuration paths.
- **VOI-04** Every conversational step provides text input and audio replay when audio is available.
- **VOI-05** The latency report measures audio round trips and demonstrates a target p95 below 4 seconds per turn in the supported demo environment.

### Conversation And Profile

- **CNV-01** The system requests spoken and tap consent before storing beneficiary data, and the consent decision is recorded.
- **CNV-02** The conversation asks only for missing skills, education, experience, aspirations, location, and preferences, while accepting free-form answers.
- **CNV-03** Speech or text is converted into a structured profile with per-field confidence, and low-confidence fields are confirmed with the beneficiary.
- **CNV-04** Beneficiary can ask an open question during the flow and receive an answer grounded in the knowledge base.
- **PRF-01** A beneficiary or authorized facilitator can view and edit the persisted profile.
- **PRF-02** A facilitator can start and manage a profile for someone else on a shared device without confusing facilitator and beneficiary identity.

### Knowledge Base And Data

- **KB-01** The knowledge base stores job roles, QP code and version, qualification name, decimal-safe NSQF level, sector, required skills, duration, training/RPL pathways, source, and verification date.
- **KB-02** Roles and skills have compatible pgvector embeddings that support semantic matching of informal descriptions to formal roles.
- **KB-03** The system stores local training centres with verified spatial data, workshops/programmes, job or self-employment opportunities, and local demand by district or block.
- **KB-04** Seed and ingestion commands are idempotent: re-running them does not create duplicate canonical records and reports provenance and failures.

### Skill Gap And Recommendation

- **GAP-01** For a selected role, the system returns the beneficiary skills that match and the required skills that are missing.
- **REC-01** Ranking combines eligibility, education, distance, language, local supply, and AI/semantic matching without allowing semantic retrieval to invent an entity.
- **REC-02** A recommendation contains a training and/or RPL-to-certification-to-livelihood pathway, nearby centres sorted by database distance, relevant opportunities, and a human-readable reason.
- **REC-03** Each recommendation exposes a reproducible multi-factor score breakdown.
- **REC-04** Every named or numeric fact in a written or spoken recommendation, including qualification, QP, level, duration, distance, centre, opportunity, and citation, exists in the exact database/tool payload; the grounding suite reports zero invented facts.

### Beneficiary Experience

- **APP-01** Beneficiary sees a mic-first home screen with minimal text, icon-led navigation, and a primary voice target of at least 72 px.
- **APP-02** Beneficiary can view pathway steps, nearby centres on a map, opportunities, the explanation, synthetic-data status, and audio playback on the results view.
- **APP-03** On a low-end Android device and poor connectivity, the app preserves safe profile drafts in an offline outbox and shows queued, synced, failed, and retry states without replaying conversational turns blindly.
- **APP-04** Beneficiary experience supports high contrast, scalable text, screen-reader labels, visible focus, and usable interaction at 200 percent text scaling.

### Organization And Administration

- **ADM-01** An authorized organization can create, edit, and publish its own training, workshop, and job opportunities with location, eligibility, provenance, and synthetic status.
- **ADM-02** An authorized organization can find privacy-minimized matching beneficiary summaries using skill, district/block, language, and NSQF-level filters, subject to beneficiary visibility rules.
- **ADM-03** An officer can view district/block skill-gap maps, demand-versus-supply charts, and the enrolment-to-livelihood programme funnel.
- **ADM-04** Server-side access control distinguishes beneficiary, facilitator, organization, officer, and admin permissions.
- **ADM-05** Authorized users can export dashboard data as CSV/XLSX and every synthetic-data marker remains present in the export.

### Outcome Tracking

- **OUT-01** A recommendation can move through recommended, enrolled, training, certified, employed, or self-employed statuses.
- **OUT-02** Authorized organizations and officers can update outcome statuses, and beneficiaries can confirm their own status.
- **OUT-03** Recorded outcome and demand signals can feed a documented, reproducible update to pathway ranking or local-demand data.

### Security And Platform

- **SEC-01** JWT login, refresh/expiry, and server-side RBAC protect all role-sensitive operations.
- **SEC-02** Sensitive data is encrypted in transit and at rest, and secrets are supplied only through environment configuration.
- **SEC-03** Access to beneficiary data by non-beneficiary roles creates an auditable log entry.
- **SEC-04** Raw audio and transcripts follow a configurable retention/purge policy, with raw audio deleted after transcription by default.
- **SEC-05** Public endpoints validate input and enforce rate limits.
- **NFR-01** Docker Compose or `make up` starts the canonical stack, `make seed` loads demo data, and the complete journey runs offline with mock providers and zero API keys after images/assets are prepared.
- **NFR-02** CI runs lint, unit/integration tests, and the grounding test on every pull request.

## V2 Deferred Requirements

These are designed for extension but are not acceptance gates for v1:

- WhatsApp and toll-free IVR entry doors sharing the same backend and recording `entry_mode`.
- Direct live integrations with NQR, Skill India Digital, NCS, and PM-AJAY APIs.
- Premium analytics, CSR/grant reporting, and richer labour-market intelligence.
- Additional languages, dialect adaptation, and language-specific model tuning beyond the v1 language set.
- Assessment tools and advanced skilling pathways.

## Out Of Scope

| Boundary | Explicit exclusion | v1 treatment |
|---|---|---|
| Payments | Payments or grant disbursement | No payment, wallet, or disbursement workflow |
| Training content | Building or hosting training content | Link to pathways and providers only |
| Certification authority | Replacing official certification issuing | Track certification status; do not issue certificates |
| Identity | Biometric or Aadhaar-linked verification | Use minimal consented identity data |
| Runtime data access | Request-time scraping of government sites | Use committed, provenance-labelled offline seeds and ingestion |
| Duplicate runtimes | KaushalVani Node/AI services as parallel authorities | Port reviewed behavior into the canonical FastAPI boundary or omit it |

## User Stories

### Beneficiary

As a low-literacy beneficiary, I want to speak in my language, so I can describe my work and goals without completing forms.

As a beneficiary, I want to understand why a pathway was recommended and what is nearby, so I can make a trustworthy decision.

As a beneficiary with unreliable connectivity, I want my safe draft and sync status to be visible, so I know whether I need help from a facilitator.

As a beneficiary, I want to confirm progress from recommendation through work, so my outcome is represented accurately.

### Facilitator

As a facilitator, I want to onboard someone on a shared device with clear identity separation, so I can help without storing the wrong person’s answers.

### Organization

As a training or livelihood organization, I want to publish opportunities and find consent-eligible matching summaries, so I can connect people to real options without seeing unnecessary PII.

### Officer And Admin

As a district officer, I want grounded maps, demand/supply trends, funnel analytics, and honest exports, so I can plan programmes without mistaking synthetic data for official data.

As an admin, I want role controls, audit history, provenance, and retention controls, so the system remains governable and privacy-respecting.

## Definition Of Done

The v1 milestone is done when:

- The canonical AVSAR-shaped stack starts cleanly with one FastAPI authority, one database migration lineage, one web client path, and no active KaushalVani duplicate runtime.
- The Sita demo persona completes consent, five profile slots, aspiration, grounded recommendation, nearest-centre result, and outcome update in mock mode with the network disabled after preparation.
- All 39 v1 requirements pass their phase verification criteria and each requirement is mapped exactly once below.
- `make seed` is repeatable; every seedable and derived record preserves source/provenance and `synthetic` status through API, UI, analytics, and CSV/XLSX.
- Grounding, RBAC, PostGIS distance, accessibility, latency, offline/provider-failure, retention, and organization privacy tests pass with no invented course, QP, number, centre, or opportunity.
- CI passes lint, unit/integration tests, and grounding checks; documented manual target-device checks pass for the selected beneficiary client.

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| VOI-01 | Phase 3 | Pending |
| VOI-02 | Phase 3 | Pending |
| VOI-03 | Phase 1 | Pending |
| VOI-04 | Phase 3 | Pending |
| VOI-05 | Phase 3 | Pending |
| CNV-01 | Phase 3 | Pending |
| CNV-02 | Phase 3 | Pending |
| CNV-03 | Phase 3 | Pending |
| CNV-04 | Phase 3 | Pending |
| PRF-01 | Phase 3 | Pending |
| PRF-02 | Phase 3 | Pending |
| KB-01 | Phase 2 | Pending |
| KB-02 | Phase 2 | Pending |
| KB-03 | Phase 2 | Pending |
| KB-04 | Phase 2 | Pending |
| GAP-01 | Phase 4 | Pending |
| REC-01 | Phase 4 | Pending |
| REC-02 | Phase 4 | Pending |
| REC-03 | Phase 4 | Pending |
| REC-04 | Phase 4 | Pending |
| APP-01 | Phase 4 | Pending |
| APP-02 | Phase 4 | Pending |
| APP-03 | Phase 4 | Pending |
| APP-04 | Phase 4 | Pending |
| ADM-01 | Phase 4 | Pending |
| ADM-02 | Phase 4 | Pending |
| ADM-03 | Phase 4 | Pending |
| ADM-04 | Phase 4 | Pending |
| ADM-05 | Phase 4 | Pending |
| OUT-01 | Phase 5 | Pending |
| OUT-02 | Phase 5 | Pending |
| OUT-03 | Phase 5 | Pending |
| SEC-01 | Phase 5 | Pending |
| SEC-02 | Phase 5 | Pending |
| SEC-03 | Phase 5 | Pending |
| SEC-04 | Phase 5 | Pending |
| SEC-05 | Phase 5 | Pending |
| NFR-01 | Phase 1 | Pending |
| NFR-02 | Phase 1 | Pending |

**Coverage:** 39/39 v1 requirements mapped exactly once.
