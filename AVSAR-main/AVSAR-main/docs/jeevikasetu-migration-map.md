# Jeevikasetu Migration Boundary

Reviewed source snapshot: `.planning/source-snapshot-manifest.json` records the
untracked AVSAR and KaushalVani trees used for this map. The snapshot is an
input artifact only; the active implementation below is the AVSAR FastAPI
runtime and its PostgreSQL lineage.

AVSAR FastAPI, PostgreSQL, and the Next.js BFF are the only active runtime. KaushalVani is reference material for vocabulary and journey design; its Node API, AI service, database, and Vite app are not started or proxied by Jeevikasetu.

## Canonical Mapping

| KaushalVani concept | Canonical owner | Phase | Boundary |
|---|---|---:|---|
| Beneficiary profile | `sessions` profile fields + consent | 3 | Store only after consent; no raw audio by default |
| Qualification / QP | `qualifications`, `courses` | 2 | Preserve decimal NSQF and QP version/source |
| Training centre | `centre_supply` | 2 | Coordinates and freshness require verified provenance |
| Employment opportunity | future canonical opportunity record | 4 | Never import fallback jobs or invented salaries |
| Roadmap step | recommendation/pathway records | 4 | Every fact must resolve to canonical IDs |
| Outcome | outcome records linked to recommendation ID | 5 | Organization updates require RBAC and audit |
| Official/admin roles | `viewer`, `officer`, `admin` | 1 | Enforced server-side; no client-only role trust |
| Consent | `consents` linked to `sessions` | 3 | Durable profile writes require consent |
| Source metadata | source/version/fetched-at fields | 2 | Preserve freshness and synthetic status |
| Beneficiary name, age, location, skills | `sessions` slots and consent-scoped profile fields | 3 | Optional/minimal PII; retain only with consent and visibility policy |
| Qualification identity | `qualifications` with canonical ID, QP code, QP version, decimal NSQF | 2 | Never coerce NSQF to integer or infer a QP code |
| Centre identity and coordinates | `centre_supply` with verified geometry and freshness | 2 | Do not import fixed coordinates or distances |
| Wage/enterprise pathway | canonical opportunity/pathway records | 4 | Salary, grant, and vacancy facts require sourced rows |
| Roadmap baseline, gap, training, certification, opportunity, outcome | recommendation-linked pathway steps | 4-5 | Each step carries canonical IDs and provenance |
| Outcome status and timestamps | canonical outcome record | 5 | Enum validation, RBAC, consent, and audit required |
| Provenance and synthetic state | source/version/fetched-at/synthetic fields | 2 | Propagate through recommendations and exports |

## Route Policy

The public contract is `/v1`. The browser calls `/api/core/*`; the Next.js BFF adds exactly one `/v1` prefix and forwards only to FastAPI. There are no active KaushalVani `/api/*` routes.

| Reference concept | Jeevikasetu destination |
|---|---|
| beneficiary intake | `POST /v1/sessions`, `POST /v1/sessions/{id}/turn` |
| recommendations | streamed `recs` event and session summary |
| officer dashboard | `/v1/dashboard/*` |
| crosswalk administration | `/v1/admin/crosswalk` |
| exports | `/v1/exports/*` |

## Route And Role Inventory

| KaushalVani reference route | Canonical Jeevikasetu contract | Owner |
|---|---|---|
| `POST /api/auth/login` | `/v1/auth/*` | AVSAR auth, JWT/RBAC |
| `/api/beneficiaries*` | `/v1/sessions*` and consent-scoped profile fields | AVSAR sessions |
| `/api/voice/*` | speech inside `/v1/sessions/{id}/turn` | AVSAR SpeechRouter |
| `/api/qualifications*` | `/v1/recommendations/*` backed by canonical qualifications | AVSAR data/recommender |
| `/api/training-centres*` | recommendation centre supply | Phase 2 spatial data |
| `/api/jobs`, `/api/enterprise-pathways` | canonical opportunities/pathways | Phase 4 opportunity domain |
| `/api/roadmap*` | recommendation-linked pathway steps | Phase 4 pathway domain |
| `/api/outcomes*` | canonical outcomes | Phase 5 outcomes domain |
| `/api/admin/*` | `/v1/dashboard/*`, `/v1/admin/*`, `/v1/exports/*` | AVSAR role-gated portal |

Canonical roles are `viewer`, `officer`, `admin`; KaushalVani's `official`
maps to `officer` only after server-side authentication. An `organization`
role is a later-phase addition and must not inherit officer access.

## Explicit Exclusions

The following remain inactive and must not be added to the Compose stack or browser BFF:

- `KaushalVani-main/backend/src/index.ts`
- `KaushalVani-main/docker-compose.yml`
- `KaushalVani-main/ai-service/main.py`
- browser-side provider calls, generated QP codes, fixed distances, invented salaries, grants, or arbitrary fallback jobs

## Forbidden Runtime Authority

| Reference artifact | Decision | Reason |
|---|---|---|
| `KaushalVani-main/backend/src/index.ts` | reference-only | Its Express `/api` gateway would create a second business-logic authority |
| `KaushalVani-main/docker-compose.yml` | reference-only | Its Node/AI/PostgreSQL topology duplicates the canonical stack |
| `KaushalVani-main/ai-service/main.py` | reference-only | Its extraction and browser-facing voice fallback can fabricate facts |
| KaushalVani in-memory store/schema | reference-only | AVSAR Alembic/PostgreSQL is the sole persistence lineage |

Generated QPs, fixed distances, salaries, grants, and arbitrary fallback jobs
are never imported. They are not placeholders for Phase 2-5 data.

All imported records must retain source identity, verification/freshness metadata, version identity, and `synthetic` propagation.
