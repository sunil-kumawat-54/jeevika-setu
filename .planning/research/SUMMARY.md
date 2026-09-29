# Jeevikasetu Research Synthesis

**Scope:** Combining the existing AVSAR and KaushalVani codebases into Jeevikasetu, evaluated against `JEEVIKASETU-GSD-PRD.md` and `.planning/PROJECT.md`.
**Research date:** 2026-09-28

## Executive Recommendation

Build Jeevikasetu around AVSAR as the initial runtime and source of truth. AVSAR is materially closer to the PRD's acceptance contract: a single FastAPI core, PostgreSQL-oriented schema and migrations, committed and provenance-aware seed pipelines, provider abstractions with mock implementations, grounded recommendation and verbalization safeguards, offline/failure drills, latency measurement, and an existing Next.js beneficiary/officer experience. Keeping these capabilities together minimizes integration risk and preserves the PRD's central invariant: the system must remain useful and honest when providers or connectivity fail.

Integrate KaushalVani selectively behind AVSAR's contracts. Its strongest reusable contributions are the livelihood-roadmap vocabulary, outcome detail, multilingual and accessibility intent, opportunity/enterprise presentation, and persona scenarios. Its Node/Express gateway, standalone AI service, in-memory runtime store, permissive fallback behavior, integer NSQF assumptions, and generated recommendation facts must not become parallel production paths. Jeevikasetu should have one `/v1` API, one profile and recommendation model, one provider boundary, and one database authority.

The immediate product risk is not framework choice; it is completing the unified data and operational contract. Neither codebase currently satisfies the PRD's centre-level PostGIS requirement, full organization workflow, or true disconnected beneficiary write continuity. The roadmap should therefore sequence contract consolidation, canonical data/provenance, grounded journey delivery, and portal gaps before investing in a second beneficiary client. Use Next.js/PWA for the first integrated journey unless target-device testing demonstrates a material browser/audio failure that justifies Flutter.

## Confirmed Reusable Assets

### AVSAR: adopt as the integration baseline

- **FastAPI core and `/v1` boundary:** central router registration, health/readiness behavior, error handling, sessions, profiles, recommendations, dashboards, exports, outcomes, and admin concerns belong here.
- **Provider abstractions:** speech, LLM, retrieval, and embeddings have server-side interfaces with mock paths. Preserve provider selection, failover/demotion, degraded metadata, and fixture-backed mock behavior.
- **Grounding safeguards:** deterministic recommendation scoring, tool-output-only facts, guarded verbalization with regeneration/template fallback, numeral/entity checks, and the grounding test are mandatory product assets.
- **Data foundation:** Alembic migrations, decimal-safe NSQF levels, QP/NQR identity, crosswalk joins, source metadata, versioning fields, `synthetic` propagation, idempotent loaders, seed envelopes, and ingestion reports.
- **Retrieval:** PostgreSQL lexical search plus pgvector hybrid retrieval and embedding-backend compatibility checks. Semantic retrieval may generate candidates but cannot authorize facts or qualifications.
- **Operational gates:** Compose/runbook patterns, `make up/seed/test/drill/grounding/latency`, health checks, provider/database/network failure drills, retention/purge patterns, and offline demo fixtures.
- **Next.js web shell:** guided beneficiary flow, consent, profile capture, free-form aspiration, confidence/confirmation, grounded results, TTS replay, accessibility patterns, officer dashboard, audit/session inspection, exports, and synthetic-data labels.
- **Security posture:** consent before storage, JWT/RBAC, audit logging, server-side provider calls, restrictive configuration, retention controls, and no raw-audio retention by default.

### KaushalVani: import as reviewed domain and UX assets

- **Livelihood vocabulary:** desired occupation, employment preference, mobility, interests, experience, skill gaps, qualifications, training, employment, enterprise, roadmap steps, certification, placement, and outcome concepts.
- **Roadmap presentation:** a user-readable progression from aspiration to profile, gap, qualification, training/RPL, opportunity, and outcome. Represent these as structured steps linked to a canonical AVSAR recommendation.
- **Outcome richness:** training, certification, employment/self-employment, placement date, income-band, and feedback concepts can extend AVSAR outcomes, subject to consent, role permissions, provenance, and retention rules.
- **Accessibility and language intent:** large voice control, high contrast, scalable text, audio read-aloud/replay, and Hindi/Marathi/English framing. Port behavior and copy only after fitting the AVSAR design and acceptance tests.
- **Persona fixtures:** the Sita scenario and additional scenario shapes can expand journey tests, but must be reconciled into one canonical seeded identity and recommendation path.
- **UI-oriented API concepts:** nearby centres, jobs, enterprise pathways, roadmap, and outcomes can fill product gaps when redesigned under the unified `/v1` contract.
- **Source metadata vocabulary:** `source_url`, `source_name`, and `last_verified_at` are useful, but the unified model also needs `source_kind`, `source_record_id`, retrieval time, verification status, and `synthetic`.

## Conflicts Requiring Decisions

| Conflict | Decision required | Recommended resolution |
|---|---|---|
| Two backend authorities | Which service owns public business logic? | AVSAR FastAPI is the only public backend. Port useful Node/AI behavior into core modules; do not compose Node/Express or KaushalVani AI as runtime authorities. |
| Incompatible APIs | Which session, voice, profile, and roadmap contracts survive? | Keep AVSAR sessions/turn streaming and `/v1` endpoints. Add roadmap/outcome fields there; do not support `/api/*` indefinitely. |
| Duplicate schemas and stores | Which IDs, migrations, and records are canonical? | Keep AVSAR Alembic/PostgreSQL as canonical. Create an explicit field/ID mapping for imported KaushalVani concepts; never migrate both schemas independently. |
| NSQF representation | Integer levels versus real half-levels | Preserve AVSAR `NUMERIC(3,1)` semantics. Never integer-cast levels or inherit KaushalVani's level-4 hard-coding. |
| Recommendation truth | Caller/AI-composed facts versus database-backed facts | Core retrieval and deterministic scoring create the recommendation object. LLM/templates only verbalize exact tool output. No generated QP, qualification, duration, centre, distance, salary, or fallback opportunity. |
| Geographic model | Aggregate district supply versus nearby centres | Add verified centre geometry and database-side PostGIS distance queries. Keep aggregate supply separate from centre identity; do not infer coordinates from aggregate rows. |
| Synthetic provenance | Dashboard disclaimer versus row-level flags | Require provenance and `synthetic` on every seedable and derived record, including UI and exports. Derived records inherit the strongest synthetic status of their inputs. |
| Identity and privacy | Named beneficiary schema versus minimal PII | Make names optional, require consent before durable storage, and import only necessary fields with role-based visibility and retention rules. |
| Runtime/deployment | AVSAR Compose/Postgres 16/Redis versus KaushalVani Compose/Postgres 15 | Use one active AVSAR-shaped Compose project and volume. Add PostGIS deliberately; do not run both stacks or merge ports and health models casually. |
| Beneficiary client | Flutter default in PRD versus mature AVSAR PWA | Use AVSAR Next.js/PWA for the first integrated journey, then resolve D-01 with target-device evidence. Keep the portal Next.js either way. |
| Voice provider policy | Bhashini preference versus available credentials | Keep a provider-neutral policy and mock floor. Use Bhashini when access/licensing is available; configure Sarvam or another approved fallback based on measured availability, cost, and data policy. |

## Risks and Mitigations

1. **Grounding regression during migration.** KaushalVani contains generated QP codes, fixed distances, arbitrary fallback jobs, and hard-coded scores. Delete these paths, require refusal/handoff on no-match, and run randomized grounding checks over names, numbers, QP codes, levels, durations, centres, distances, seats, and citations.
2. **False nearby-centre claims.** Current AVSAR supply is aggregate-only and KaushalVani uses a hard-coded origin. Add `geography(Point,4326)`, verified source metadata, privacy-safe coarse beneficiary origin, GiST indexing, `ST_DWithin`/`ST_Distance`, and fixtures for missing/out-of-radius coordinates.
3. **Two sources of truth.** Running both backends or stores would fork sessions, auth, profiles, and recommendations. Keep source directories reference-only during integration, publish one endpoint/data mapping, and make clean Compose startup prove only the canonical stack is active.
4. **Synthetic data presented as official.** Government-looking URLs are not provenance. Propagate `synthetic`, `source_kind`, record IDs, verification dates, and notes from seed through API, recommendation, UI, analytics, and CSV/XLSX export.
5. **Offline claim overstated.** AVSAR's service worker caches the shell but does not safely replay conversational POSTs; KaushalVani has no implemented offline queue. Define offline layers separately: preloaded shell/data, local-stack mock journey, and disconnected beneficiary continuity. Add an IndexedDB outbox with idempotency keys and explicit queued/synced/failed states; never blindly replay audio turns.
6. **Provider and browser variability.** Browser mic permissions, codecs, autoplay, Bhashini access, and live credentials are unverified on target devices. Keep mock fixtures first-class, expose provider/degraded/latency metadata, test permission and playback recovery, and validate Hindi plus the selected regional language on low-end Android hardware.
7. **Privacy expansion through KaushalVani fields.** More profile and outcome detail can increase PII exposure. Make fields consent-scoped, names optional, raw audio ephemeral, organization views privacy-minimized, and non-beneficiary access audited.
8. **Organization workflow gap.** Existing officer/admin evidence does not prove the PRD's organization posting, candidate matching, or outcome-update workflow. Add server-side `organization` RBAC, organization ownership, consent-aware candidate summaries, audit entries, and focused integration tests.

## Flutter vs Next.js/PWA Decision

**Recommendation: choose Next.js/PWA for the first integrated beneficiary client, pending a narrow target-device gate.** This is evidence-based rather than a dismissal of Flutter:

- AVSAR already supplies the beneficiary flow, browser audio normalization, streamed replay, accessibility/focus patterns, service worker, mock journey, and the same Next.js shell needed for officer/admin/organization surfaces.
- Flutter has no inspected implementation evidence in this workspace. It would add a new audio path, permissions model, accessibility audit, offline state model, build/distribution pipeline, and client integration surface while the backend and data contracts are still being consolidated.
- Both clients still require the same backend, provider fixtures, privacy rules, sync conflict handling, and offline semantics. Flutter improves native audio and local persistence ergonomics but does not solve the missing PostGIS, organization, or grounding work.
- A PWA is sufficient for the hackathon if it passes mic permission/capture/playback, text fallback, accessibility at 200% scaling, preloaded mock journey with network disabled, and the planned outbox sync checks on target low-end Android devices.

Run the spike against the integrated core and decide Flutter only if the PWA fails materially on those checks, or if measured requirements include background audio, call interruption handling, Bluetooth/device integration, or an installed-app distribution model. Flutter would replace or complement only the beneficiary client; the Next.js organization/officer/admin portal remains the shared portal.

## Research Implications for Requirements and Roadmap

### Requirements implications

- Add an explicit architecture requirement for one public FastAPI contract and one canonical PostgreSQL migration set; source repositories remain reference material, not parallel services.
- Strengthen KB requirements with QP version identity, decimal NSQF levels, provenance fields, freshness/verification behavior, and refusal for unresolved joins.
- Refine local-opportunity requirements to require centre-level verified geometry, privacy-safe origin handling, database-side radius/distance queries, and honest missing-coordinate behavior.
- Expand grounding requirements to every named and numeric fact in the richer pathway payload, including distances, seat counts, wages/income bands, enterprise claims, and citations.
- Add a synthetic-provenance requirement for derived recommendations, centres, opportunities, analytics, and exports, not only source rows.
- Clarify offline requirements into local-stack offline demo versus disconnected browser continuity; require an idempotent outbox and visible sync states for the latter.
- Add organization requirements: organization role, owned opportunity CRUD, privacy-minimized candidate matching, consent/visibility rules, and audited outcome updates.
- Preserve the PRD's explicit non-goals: no payments, training-content hosting, official certification replacement, biometrics, request-time government scraping, or v2 entry doors.

### Recommended roadmap shape

1. **Integration contract and foundation**
   - Freeze AVSAR as runtime anchor; publish API, ID, role, consent, provenance, and source mapping decisions.
   - Consolidate one Compose stack, environment model, health checks, Make targets, and CI.
   - Risk focus: duplicate backends, ports, auth paths, and deployment assumptions.

2. **Canonical data, provenance, and spatial model**
   - Reconcile KaushalVani profile/roadmap/outcome vocabulary into AVSAR migrations and seeds.
   - Preserve decimal NSQF/QP identity, add PostGIS geometry and verified centre data, and make ingestion idempotent.
   - Risk focus: false proximity, stale sources, synthetic ambiguity, and schema drift.

3. **Voice, session, and profile journey**
   - Keep AVSAR consent/session/turn state machine and provider router; import KaushalVani language vocabulary and scenario fixtures.
   - Deliver text fallback, replay, confidence confirmation, facilitator mode, mock providers, and degraded responses.
   - Risk focus: browser/provider failure and simulated audio being mistaken for real recognition.

4. **Grounded gap, recommendation, and pathway experience**
   - Use deterministic AVSAR retrieval/scoring/crosswalk as authority.
   - Add structured roadmap steps, explicit matched/missing skills, enterprise/wage alternatives, factor explanations, source metadata, and grounding status.
   - Risk focus: generated facts, arbitrary fallbacks, and untestable explanations.

5. **Beneficiary PWA continuity and platform gate**
   - Reuse AVSAR UX and add the minimal IndexedDB draft/outbox model, idempotency, recovery states, and target-device accessibility/audio tests.
   - Make the Flutter/PWA decision from the measured gate, not before the shared contract works.
   - Research flag: targeted device/browser spike required.

6. **Organization, officer, admin, and outcomes**
   - Retain AVSAR officer dashboard, exports, audit, and crosswalk patterns.
   - Add organization-owned opportunities, candidate matching, privacy-aware views, RBAC, and richer KaushalVani-inspired outcome states.
   - Risk focus: missing organization authority and PII leakage.

7. **Hardening and demo readiness**
   - Run clean migration, seed idempotency, grounding, PostGIS distance, synthetic visibility, RBAC, accessibility, latency, provider-revocation, DB-down, network-off, retention, and full Sita journey gates.
   - Keep live provider and government API work behind v2 boundaries unless explicitly validated.

### Research flags

- **Needs focused research/spike:** Flutter versus Next.js/PWA on specified low-end Android devices; Bhashini access/licensing and language latency; PostGIS centre-data availability and coordinate quality; actual disconnected/offline scope; organization candidate privacy policy.
- **Can use established patterns:** AVSAR FastAPI/provider boundary, mock mode, seed/provenance pipeline, deterministic recommendation, guarded verbalization, officer dashboard, exports, and CI/drill structure.
- **Must be validated in implementation:** KaushalVani field mapping, roadmap/outcome schema additions, organization portal behavior, and all imported UI/accessibility patterns.

## Confidence Assessment

| Area | Confidence | Basis and remaining uncertainty |
|---|---|---|
| Architecture | HIGH | Both implementations were inspected and AVSAR's single-core alignment with the PRD is clear. The decision to avoid dual runtime authorities is strong. |
| Data grounding | HIGH for existing behavior; MEDIUM for unified schema | AVSAR's gates and provenance patterns are concrete. PostGIS geometry, centre freshness, and full KaushalVani field mapping still require implementation evidence. |
| UX and providers | HIGH for repository behavior; MEDIUM for production deployment | AVSAR has working browser/mock evidence and provider adapters. Target devices, live Bhashini access, licensing, and field audio quality were not exercised. |
| Flutter vs PWA | MEDIUM-HIGH for hackathon sequencing | PWA has direct reusable evidence; Flutter has no local implementation evidence. Native-device requirements could change the result. |
| Overall integration recommendation | HIGH | All three research files independently converge on AVSAR as baseline and selective KaushalVani reuse. |

## Remaining Gaps

- `.planning/STATE.md` now records the initialized scope; implementation should keep using it alongside `.planning/PROJECT.md` and the PRD.
- Exact target Android models, browsers, screen readers, and connectivity conditions are not specified.
- The intended offline promise is not yet separated into local-stack judging mode versus disconnected field continuity.
- Live Bhashini credentials/licensing and the approved fallback provider are not confirmed.
- Verified centre-level coordinates and freshness policy are not available in either existing implementation.
- Organization consent and candidate-contact policy needs a product decision before implementation.

## Sources

Primary planning and product sources:

- [JEEVIKASETU-GSD-PRD.md](../../JEEVIKASETU-GSD-PRD.md)
- [PROJECT.md](../PROJECT.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DATA-GROUNDING.md](DATA-GROUNDING.md)
- [UX-PROVIDERS.md](UX-PROVIDERS.md)

The three research files contain the detailed source-file inventories for AVSAR and KaushalVani, including migrations, loaders, recommenders, grounding guards, provider adapters, client flows, dashboards, schemas, controllers, deployment files, and scenario scripts.
