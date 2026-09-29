---
phase: 02-canonical-data-knowledge-and-grounded-backend
plan: 01
subsystem: database
tags: [postgresql, alembic, sqlalchemy, postgis, pgvector, provenance, spatial]

requires:
  - phase: 01-unified-foundation-and-migration-boundary
    provides: AVSAR FastAPI/PostgreSQL authority, linear Alembic baseline, Decimal NSQF conventions
provides:
  - Linear 0003 canonical knowledge/provenance/spatial migration
  - Matching SQLAlchemy models for source snapshots, skills, pathways, centres, programmes, opportunities, and demand
  - Single PostgreSQL image build path with pgvector, pg_trgm, and PostGIS
  - Focused schema and privacy-safe spatial acceptance tests
affects: [02-02 deterministic loaders, 02-03 grounded retrieval and spatial queries]

actuals:
  tokens: 17922
  tasks: 3
  commits: 0

tech-stack:
  added: [PostGIS extension, pinned pgvector/PostGIS database image build]
  patterns: [linear Alembic lineage, explicit provenance fields, Decimal NSQF identity, geography(Point,4326), coordinate eligibility statuses]

key-files:
  created:
    - AVSAR-main/AVSAR-main/services/core/alembic/versions/0003_canonical_knowledge_provenance_spatial.py
    - AVSAR-main/AVSAR-main/infra/db/Dockerfile
    - AVSAR-main/AVSAR-main/services/core/tests/test_gate_phase2_spatial.py
  modified:
    - AVSAR-main/AVSAR-main/services/core/models/tables.py
    - AVSAR-main/AVSAR-main/infra/db/init.sql
    - AVSAR-main/AVSAR-main/infra/docker-compose.yml
    - AVSAR-main/AVSAR-main/services/core/tests/test_gate1_models.py

key-decisions:
  - "Keep 0003 as the sole child of 0002_doc_chunk_identity; migrations remain authoritative for extensions and schema."
  - "Use one locally built pinned PostgreSQL image based on pgvector with PostGIS packages; do not introduce a second database."
  - "Persist centre geography only as geography(Point,4326) with explicit verified/synthetic/missing/stale/rejected status; beneficiary home coordinates are not modeled."
  - "Do not commit in the protected shared outer worktree; preserve the untracked application source snapshot and existing user changes."

patterns-established:
  - "Canonical rows carry source name/version/record identity, verification status, freshness timestamps, synthetic state, and fingerprints."
  - "Nearby-centre claims require coarse request origin, eligible coordinate status, freshness, ST_DWithin radius filtering, and ST_Distance ordering."

requirements-completed: [KB-01, KB-03]

coverage:
  - id: D1
    description: "A linear 0003 migration and matching ORM define provenance-aware qualifications, pathways, centres, programmes, opportunities, and demand."
    requirement: KB-01
    verification:
      - kind: unit
        ref: "python -m pytest -q services/core/tests/test_gate1_models.py services/core/tests/test_gate_phase2_spatial.py -x"
        status: pass
    human_judgment: false
  - id: D2
    description: "The single database image/init path declares vector, pg_trgm, and PostGIS capabilities with vector/text/spatial indexes."
    requirement: KB-03
    verification:
      - kind: other
        ref: "python scripts/preflight_phase1.py --compose infra/docker-compose.yml --env-file .env.example"
        status: unknown
    human_judgment: true
    rationale: "Docker is unavailable in this Windows session; runtime extension/version and clean upgrade acceptance require a Docker-capable host."
  - id: D3
    description: "Focused tests cover Decimal half-levels, version identity, provenance, synthetic coordinate labels, privacy-safe origin, and spatial radius/distance behavior."
    requirement: KB-03
    verification:
      - kind: unit
        ref: "python -m pytest -q services/core/tests/test_gate1_models.py services/core/tests/test_gate_phase2_spatial.py -x"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-09-29
status: complete
---

# Phase 2 Plan 1: Canonical Data, Knowledge And Grounded Backend Summary

**Linear canonical migration with provenance-aware Decimal qualifications, PostGIS centre geography, opportunity/demand entities, and privacy-safe spatial tests**

## Performance

- **Tasks:** 3 completed in the source worktree.
- **Files created:** 3.
- **Files modified:** 4.
- **Commits:** 0 by explicit outer-worktree instruction; the current branch is protected `main` and the application tree is an untracked source snapshot.

## Accomplishments

- Added `0003_canonical_knowledge_provenance_spatial.py` as the exact child of `0002_doc_chunk_identity`. It self-enables `vector`, `pg_trgm`, and `postgis`, preserves existing rows, adds qualification provenance/version identity, and creates canonical source snapshots, skills, qualification skills, pathways, centres, programmes, opportunities, and district/block demand tables.
- Expanded the SQLAlchemy model surface with Decimal-safe NSQF/provenance fields, reusable enum contracts, a dependency-free `geography(POINT,4326)` type, GiST metadata, and matching natural keys/check constraints.
- Switched Compose to one pinned local PostgreSQL image build based on `pgvector:0.8.0-pg16` with PostgreSQL 16 PostGIS packages; `init.sql` and the migration both enable all required capabilities.
- Added schema/spatial tests for one-head lineage, extension/index declarations, Decimal 4.5 round trips, provenance/synthetic labels, privacy-safe origin columns, verified centre/programme/opportunity tracing, PostGIS `ST_DWithin`/`ST_Distance`, and negative capacity/radius rejection.

## Verification Outcomes

- `python -m ruff check services/core/models/tables.py services/core/tests/test_gate1_models.py services/core/tests/test_gate_phase2_spatial.py` -> **PASS**.
- `python -m pytest -q services/core/tests/test_gate1_models.py services/core/tests/test_gate_phase2_spatial.py -x` -> completes successfully; database-backed cases are skipped by the existing `db_available` fixture because Postgres is unavailable.
- `python -m compileall -q ...` -> **PASS**.
- `python scripts/preflight_phase1.py --compose infra/docker-compose.yml --env-file .env.example` -> **BLOCKED_RUNTIME** (`docker: false`); portable config checks passed, Compose startup was not claimed.
- Alembic revision import -> **PASS**, identifiers are `0003_canonical_knowledge_provenance_spatial` and `0002_doc_chunk_identity`.
- Editor diagnostics for changed Python files -> **no errors**.

## Deviations from Plan

### Auto-added critical infrastructure

**1. [Rule 2 - Missing capability] Added a pinned database image recipe**
- **Found during:** Task 2.
- **Issue:** The existing `pgvector/pgvector:pg16` image did not establish PostGIS capability, while the plan requires vector, text, and spatial extensions in one database.
- **Fix:** Added `infra/db/Dockerfile`, based on `pgvector/pgvector:0.8.0-pg16`, installing the pinned PostgreSQL 16 PostGIS packages; Compose builds this single image.
- **Verification:** Compose references the build/image, init and healthcheck name all three extensions, and portable preflight reports the configuration while correctly blocking runtime acceptance.

## Issues Encountered

Docker/Desktop is unavailable in this session. Runtime acceptance remains **BLOCKED_RUNTIME**: no clean empty-database `alembic upgrade head`, repeat upgrade, extension/version query, live index query, or database-backed tracer result is claimed here.

## User Setup Required

A Docker-capable host is required to complete runtime acceptance. Run the plan’s empty-database migration twice, query `vector`, `pg_trgm`, and `postgis` versions plus HNSW/GIN/GiST indexes, then rerun the focused tests.

## Next Phase Readiness

02-02 can proceed with deterministic snapshot/loaders against this canonical contract. It should preserve the source/version/fetched/verified/freshness/fingerprint and synthetic fields, and it should add its own idempotency tests. The Docker/PostGIS runtime gate remains an open verification item rather than a blocker to loader implementation.

---
*Phase: 02-canonical-data-knowledge-and-grounded-backend*
*Plan: 01*
*Completed: 2026-09-29*

## Self-Check: PASSED

- Summary file exists at the required path.
- Migration, Dockerfile, ORM, init/Compose, and focused test files exist.
- No task or metadata commits were created because the user instructed preservation of the protected shared outer worktree.
