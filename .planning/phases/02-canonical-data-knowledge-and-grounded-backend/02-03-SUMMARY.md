---
phase: 02-canonical-data-knowledge-and-grounded-backend
plan: 03
subsystem: grounded-backend
tags: [retrieval, pgvector, postgis, grounding, provenance, recommendations]
requires:
  - phase: 02-canonical-data-knowledge-and-grounded-backend
    plan: 01
    provides: canonical provenance-aware schema and PostGIS-capable models
  - phase: 02-canonical-data-knowledge-and-grounded-backend
    plan: 02
    provides: deterministic snapshots, loaders, and synthetic/provenance propagation
provides:
  - canonical-row-authorized grounded recommendation read path
  - provenance and synthetic metadata in structured recommendation/dashboard payloads
  - bounded PostGIS nearby-centre query with typed spatial outcomes
  - embedding backend and dimension compatibility checks
  - focused retrieval/spatial/recommender acceptance coverage
affects: [phase-04 beneficiary-and-organization-experiences]
tech-stack:
  added: []
  patterns:
    - retrieval is candidate generation; canonical SQL rows authorize facts
    - ST_DWithin radius filtering and ST_Distance ordering remain database-side
    - hashing embeddings remain the zero-network fallback with explicit compatibility checks
key-files:
  created:
    - AVSAR-main/AVSAR-main/services/core/api/recommendations.py
    - AVSAR-main/AVSAR-main/services/core/tests/test_gate_phase2_retrieval.py
  modified:
    - AVSAR-main/AVSAR-main/services/core/rag/retrieve.py
    - AVSAR-main/AVSAR-main/services/core/rag/embedder.py
    - AVSAR-main/AVSAR-main/services/core/api/dashboard.py
    - AVSAR-main/AVSAR-main/services/core/tests/test_gate_phase2_spatial.py
decisions:
  - "The missing recommendations router was added as the owner of the /v1/recommendations/grounded read path already registered by main.py."
  - "No retrieved document or semantic candidate is treated as an entity authority; qualifications, programmes, opportunities, and centres are resolved from canonical SQL rows."
  - "The shared protected outer worktree and untracked source snapshot were preserved; no task or metadata commits were created."
metrics:
  duration: "about 50min"
  completed: 2026-09-29
  commits: 0
  plan_head_before: "not applicable; protected outer worktree"
  status: complete
actuals:
  tokens: 13111
  tasks: 3
  commits: 0
requirements-completed: [KB-02, KB-03]
status: complete
---

# Phase 2 Plan 3: Grounded Retrieval And Spatial Backend Summary

**Canonical-row-authorized retrieval with provenance-aware payloads, bounded PostGIS nearby results, and explicit embedding compatibility checks.**

## Accomplishments

- Added `core.api.recommendations` and the versioned `/v1/recommendations/grounded` path. Retrieval candidates are resolved to canonical qualification rows before qualification, pathway, programme, opportunity, or numeric facts enter the response.
- Preserved Decimal NSQF levels as strings in the structured payload, and propagated source name/version/record identity, verification/freshness fields, fingerprints, and synthetic markers.
- Added a database-side nearby-centre query using parameterized `ST_DWithin` and `ST_Distance`, deterministic distance ordering, a 100 km mobility bound, and typed `missing_origin`, `missing_coordinates`, `stale_coordinates`, and `no_results` outcomes. No application Haversine or fixed origin was introduced.
- Hardened vector retrieval to inspect every populated `doc_chunks` backend/dimension value and fail clearly on mixed backend or dimension spaces. Existing lexical-only degradation remains intact for ordinary dense-half failures, and dense results carry provenance markers.
- Added focused multilingual tsquery, deterministic hashing, backend/dimension mismatch, RRF ordering, canonical authorization, spatial policy, and synthetic/freshness contract tests. Existing dashboard recommendation facts now include source provenance alongside the prior synthetic field.

## Verification Outcomes

- `python -m pytest -q services/core/tests/test_gate_phase2_retrieval.py services/core/tests/test_gate_phase2_spatial.py -x` -> **PASS**; Postgres-backed cases skipped because Postgres is unavailable.
- `python -m pytest -q services/core/tests/test_gate_phase2_retrieval.py services/core/tests/test_gate_phase2_spatial.py services/core/tests/test_gate4_recommender.py -x` -> **PASS**; expected database-dependent skips.
- `python -m pytest -q services/core/tests/test_gate_phase1_contracts.py services/core/tests/test_gate_phase2_retrieval.py services/core/tests/test_gate_phase2_spatial.py services/core/tests/test_gate4_recommender.py -x` -> **PASS**.
- `python -m ruff check` over all touched backend and focused test files -> **PASS**.
- `python -m compileall -q` over touched backend files -> **PASS**.
- Clean Docker Compose runtime started all four services healthy; PostgreSQL exposes `vector 0.8.0`, `pg_trgm 1.6`, and `postgis 3.6.4`, with HNSW, GIN, and centre GiST indexes present.
- Empty-database Alembic upgrade reached `0003_canonical_spatial`; a second upgrade was a no-op. The revision was shortened from the overlong plan label to fit Alembic's `varchar(32)` version column.
- `python scripts/verify_grounding.py --n 50` -> **PASS**: 50 sessions, 211 numerals, 0 invented facts, 9 honest refusals.
- `python scripts/verify_client_contract.py --base-url http://localhost:8000/v1 --lang hi` -> **PASS**; live SSE events were `state`, `transcript`, and `tts`.
- `http://localhost:3000/api/health` -> **PASS**.
- Editor diagnostics for all touched Python modules -> **no errors**.

## Deviations From Plan

### Auto-added missing critical path

**1. [Rule 2 - Missing functionality] Added the absent recommendations router.**
- **Found during:** Task 1.
- **Issue:** `main.py` registered `core.api.recommendations`, but the module did not exist, leaving no owner for the planned grounded `/v1` read path.
- **Fix:** Added canonical authorization, provenance serialization, structured pathway/programme/opportunity reads, and PostGIS nearby-centre results in `services/core/api/recommendations.py`.
- **Verification:** Focused retrieval/spatial/API contract tests and lint pass.

## Runtime Evidence Completed

Docker/PostgreSQL runtime acceptance is complete for this phase. The only remaining warning is expected: the committed E5 embedding rows are not compatible with the mock hashing runtime, so semantic recall is disabled and the safe lexical path is used. No facts are authorized from incompatible vector rows.

## Known Stubs / Deferred Inputs

None introduced by this plan. The existing optional opportunity/demand snapshot absence and synthetic source inputs remain governed by the 02-02 summary.

## Phase Closure

Plan 02-03 and Phase 2 are complete. The live Docker/PostGIS migration, seed, schema, spatial, retrieval, client, and 50-session grounding gates passed.

## Self-Check: PASSED

- Summary file exists at the required path.
- All planned implementation/test files exist and diagnostics are clean.
- No task or metadata commits were created, preserving the protected shared outer worktree and untracked source snapshot.
