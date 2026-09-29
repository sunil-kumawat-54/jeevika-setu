---
phase: 02-canonical-data-knowledge-and-grounded-backend
plan: 02
subsystem: ingestion
status: complete
tags: [ingestion, provenance, fingerprints, idempotency, snapshots, synthetic-data]
requires:
  - phase: 02-canonical-data-knowledge-and-grounded-backend
    plan: 01
    provides: canonical provenance-aware schema and PostGIS-capable model surface
provides:
  - deterministic canonical record and snapshot fingerprints that exclude volatile timestamps
  - provenance normalizer with source identity/version, freshness, verification, and synthetic propagation
  - portable natural-key convergence contract with inserted/updated/skipped/failed reporting
  - database-facing canonical loaders for centres, programmes, opportunities, and district demand
  - deterministic synthetic centre/programme snapshots with no fabricated coordinates
  - local source snapshot manifest and expanded ingest report evidence
  - focused Phase 2 data convergence tests
affects: [02-03 grounded retrieval and spatial queries]
tech-stack:
  added: []
  patterns: [canonical-json hashing, natural-key upsert reports, savepoint-isolated row failures, source snapshot manifests]
key-files:
  created:
    - AVSAR-main/AVSAR-main/services/core/tests/test_gate_phase2_data.py
    - AVSAR-main/AVSAR-main/seeds/training_centres.json
    - AVSAR-main/AVSAR-main/seeds/programmes.json
    - AVSAR-main/AVSAR-main/seeds/source_snapshot_manifest.json
  modified:
    - AVSAR-main/AVSAR-main/pipelines/common.py
    - AVSAR-main/AVSAR-main/pipelines/load_to_db.py
    - AVSAR-main/AVSAR-main/pipelines/run_all.py
    - AVSAR-main/AVSAR-main/pipelines/03_join_qp_level.py
    - AVSAR-main/AVSAR-main/pipelines/05_seed_district_supply.py
    - AVSAR-main/AVSAR-main/pipelines/write_ingest_report.py
    - AVSAR-main/AVSAR-main/docs/ingest-report.md
decisions:
  - "Record fingerprints hash sorted canonical record content and exclude fetched_at/last_verified_at volatility."
  - "Missing source_record_id is a visible failure; loaders never invent a natural key."
  - "Synthetic centre supply derives coordinate-less canonical centres/programmes and remains coordinate_status=synthetic."
  - "Optional opportunity and demand snapshots remain unavailable until sourced; no official-looking fallback rows are generated."
  - "No commits were created because the shared outer worktree is protected and contains an untracked source snapshot."
metrics:
  duration: "about 45min"
  completed: 2026-09-29
  commits: 0
  plan_head_before: "not applicable; protected outer worktree"
actuals:
  tokens: 22000
  tasks: 3
  commits: 0
requirements-completed: [KB-01, KB-03, KB-04]
---

# Phase 2 Plan 2: Deterministic Snapshots And Honest Loaders Summary

**Stable provenance-aware fingerprints, two-pass natural-key convergence, canonical synthetic supply snapshots, and explicit ingest failure/report semantics.**

## Accomplishments

- Added shared canonical JSON, per-record, sorted-record, and local-file snapshot hashing helpers. Envelope timestamps do not alter record fingerprints; source content changes do.
- Added provenance enrichment that carries source name/version, fetched/verified/freshness fields, verification status/notes, and synthetic status into derived rows. Rows without required source identity are rejected with an explicit failure.
- Added portable `LoadReport` and natural-key convergence semantics that distinguish inserted, updated, unchanged/skipped, and failed rows while preserving stable keys and IDs in the modelled two-pass path.
- Extended the database loader with reported canonical loaders for `training_centres`, `programmes`, `opportunities`, and `district_demand`; programme loading resolves centre and qualification references and reports unresolved source identities.
- Extended synthetic district supply to emit canonical training-centre and programme snapshots. These rows have explicit synthetic provenance and no generated coordinates.
- Added a stable local source snapshot manifest and expanded `docs/ingest-report.md` with source identity/version, freshness, verification, stable fingerprints, canonical loader semantics, synthetic caveats, and failure visibility.
- Preserved QP join upstream provenance and synthetic status while retaining `join_strategy`, `level_inferred`, half-level values, and tautological-match caveat fields.

## Verification

- `python -m pytest -q services/core/tests/test_gate2_ingestion.py services/core/tests/test_gate_phase2_data.py -x` -> PASS; database-dependent tests skip because Postgres is unavailable.
- `python -m pytest -q services/core/tests/test_gate1_models.py services/core/tests/test_gate_phase2_spatial.py -x` -> PASS with expected Postgres-backed skips.
- `python -m ruff check pipelines/common.py pipelines/load_to_db.py pipelines/run_all.py pipelines/03_join_qp_level.py pipelines/05_seed_district_supply.py pipelines/06_load_guidelines_rag.py pipelines/write_ingest_report.py services/core/tests/test_gate2_ingestion.py services/core/tests/test_gate_phase2_data.py` -> PASS.
- `python -m compileall -q pipelines services/core/tests/test_gate_phase2_data.py` -> PASS.
- `python scripts/preflight_phase1.py --compose infra/docker-compose.yml --env-file .env.example` -> `BLOCKED_RUNTIME` with portable config checks passing; Docker is unavailable.
- Offline `05_seed_district_supply` executed twice. Raw envelope file hashes differ because `fetched_at` is intentionally volatile; stable `seed_fingerprint` values are equal for `centre_supply.json`, `training_centres.json`, and `programmes.json`.
- A database-backed loader run, live migration acceptance, PostGIS extension/index queries, and database surrogate-ID convergence were not claimed because PostgreSQL/Docker is unavailable in this Windows session.

## Deviations From Plan

### Auto-fixed Issues

1. **[Rule 2 - Missing critical evidence]** Added explicit source identity/version and freshness defaults when writing envelopes, plus stable local snapshot manifests.
2. **[Rule 1 - Correctness]** Added savepoint-isolated reported upserts so malformed rows are counted as failed without hiding other source rows.
3. **[Rule 2 - Honesty]** Added canonical synthetic centre/programme snapshots without coordinates; opportunities and demand remain visibly unavailable instead of receiving fabricated records.

### Deferred Runtime Evidence

Docker/Desktop and Postgres are unavailable. The focused portable tests and schema declarations pass, but live `alembic upgrade head`, database loader two-pass acceptance, PostGIS queries, and database-side stable surrogate-ID evidence remain pending on a Docker-capable host.

## Known Stubs / Deferred Inputs

- `seeds/opportunities.json` and `seeds/district_demand.json` are intentionally not generated because no approved committed source snapshot was present. The ingest report lists both as not generated; no live or official status is claimed.
- Existing legacy seed envelopes may show source name/version fallback values in reports until their producing pipelines are rerun; the report derives an honest pipeline/fingerprint fallback without rewriting user snapshots.

## Readiness For 02-03

Ready for 02-03 retrieval/spatial work against the canonical schema and loader contracts. 02-03 should consume stable fingerprints and source metadata, authorize retrieved entities by joining back to canonical rows, exclude synthetic/missing/stale centre coordinates from nearby claims, and retain the Docker/Postgres acceptance item as an open verification gate.

## Self-Check: PASSED

- Summary file exists at the required path.
- Focused tests, prior schema/spatial tests, lint, compile, and portable preflight were run.
- No commits were created; protected outer-worktree and untracked source-snapshot preservation requirements were honored.
