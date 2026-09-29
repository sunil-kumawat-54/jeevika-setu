# Phase 2: Canonical Data, Knowledge And Grounded Backend - Research

**Researched:** 2026-09-29  
**Domain:** Canonical PostgreSQL data, provenance-aware ingestion, hybrid knowledge retrieval, and grounded spatial backend  
**Confidence:** HIGH for existing AVSAR behavior; MEDIUM for PostGIS image choice and verified centre source availability

## Scope and Locked Boundaries

Phase 2 implements KB-01 through KB-04 against the AVSAR-shaped FastAPI/PostgreSQL authority established by Phase 1. The active runtime remains one FastAPI service, one PostgreSQL migration lineage, Redis, and the Next.js shell. KaushalVani contributes reviewed vocabulary and source snapshots only; its Node gateway, AI service, schema, and in-memory store are not runtime dependencies.

The runtime never calls government hosts. Pipelines may fetch or consume committed snapshots, but request-time API code reads canonical database rows. Mock providers and deterministic hashing embeddings remain first-class. Docker startup, physical-device checks, and any live government refresh are evidence or operator concerns, not reasons to claim acceptance in this planning session.

## Requirement Coverage

| ID | Required outcome | Phase 2 evidence target |
|---|---|---|
| KB-01 | Store job roles, QP code/version, qualification, decimal NSQF, sector, skills, duration, training/RPL pathways, source, verification date. | Versioned qualification/role records, canonical skills/pathway relations, provenance fields, API fixtures, decimal round-trip tests. |
| KB-02 | Compatible embeddings support semantic matching of informal descriptions to formal roles. | One embedding contract/backend per index, QP/skill vectors, lexical plus vector retrieval, deterministic mock backend and mismatch rejection. |
| KB-03 | Store verified centres, programmes, job/self-employment opportunities, and local demand. | PostGIS centre geometry, programme/opportunity/demand tables, coarse-origin query input, database-side distance/radius tests. |
| KB-04 | Seed/ingestion is idempotent and reports provenance/failures. | Stable natural-key upserts, record fingerprints, source/version/fetched/verified/freshness fields, ingest-run reports, two-run equality tests. |

## Existing Evidence and Controlling Gaps

### Existing migration and ORM

`services/core/alembic/versions/689e6d7eb5f5_initial_schema_per_architecture_section_.py` creates `vector` and `pg_trgm`, 768-dimensional vectors, `courses`, `qualifications`, `qp_descriptions`, `crosswalk`, `doc_chunks`, `centre_supply`, and `ingest_runs`. `0002_doc_chunk_identity.py` is the current head and repaired NULL-safe, digest-based chunk identity. The chain is linear today and must remain linear.

`services/core/models/tables.py` correctly maps `courses.nsqf_level` and `qualifications.nsqf_level` to `Numeric(3,1)` and `Decimal`, and `qualifications.version_id` is unique. The current tables do not provide row-level source/version/freshness metadata consistently, a centre geometry, a centre identity separate from aggregate supply, opportunity/programme/demand entities, or a fingerprinted ingest run.

### Existing ingestion and seeds

`pipelines/common.py` provides provenance envelopes, deterministic `stable_rng`, record-only `seed_fingerprint`, sorted JSON seed output, raw-response caching, and a best-effort `ingest_runs` write. `pipelines/load_to_db.py` performs PostgreSQL upserts on natural keys and preserves row `synthetic` values, but it currently treats the envelope as the main provenance record and cannot load spatial centres or richer opportunity vocabulary.

`pipelines/run_all.py` executes the offline snapshot sequence and prints fingerprints, but it explicitly allows changing provenance timestamps and does not persist a run-level source snapshot/fingerprint manifest. `03_join_qp_level.py` preserves source provenance and marks hours-derived NSQF levels as inferred. `05_seed_district_supply.py` creates intentionally synthetic aggregate rows with deterministic names/seats but no coordinates. `06_load_guidelines_rag.py` creates section-prefixed chunks and compatible embeddings, with a synthetic canonical-fact fallback.

### Existing retrieval

`services/core/rag/retrieve.py` already has safe tokenization for `to_tsquery`, Postgres `tsvector` lexical search, pgvector cosine search, and reciprocal-rank fusion. `services/core/rag/embedder.py` provides `e5` and deterministic `hashing` backends, 768 dimensions, E5 query/passage prefixes, vector normalization, and hard backend mismatch rejection. Retrieval is appropriate for knowledge/document candidate generation. It must not authorize a qualification, centre, opportunity, distance, or other entity; structured database rows remain authoritative.

### Existing tests

`test_gate1_models.py` verifies one Alembic head, schema/ORM presence, vector/HNSW/GIN indexes, decimal NSQF, and half-level round trips. `test_gate2_ingestion.py` verifies seed envelopes, synthetic propagation, half-level ingestion, QP join honesty, runtime prohibition on government hosts, and loader idempotency. `test_gate4_recommender.py` verifies decimal-safe capability ceilings, deterministic semantic candidates, and grounded factor payloads. Phase 2 should extend these gates with spatial, provenance, fingerprints, opportunity vocabulary, and retrieval compatibility tests rather than creating an unrelated test framework.

## Canonical Data Design

### Qualification and QP identity

- Keep `qualifications.version_id` as the immutable source-version identity and retain `nqr_code`, `qp_code`, name, sector, validity, and source record identity together.
- Do not use `qp_code` alone as a qualification primary identity: the same QP can have multiple versions.
- Keep NSQF in PostgreSQL `NUMERIC(3,1)` and Python `Decimal`; display flooring for speech is presentation-only.
- Add an explicit qualification-to-course/role relation or stable canonical role key so PM-AJAY course rows can point to a versioned qualification without copying facts.
- Preserve the join strategy and `level_inferred` flag. An hours-derived level is never relabeled as register-assigned.

### Provenance, freshness, and synthetic propagation

Every seedable source or derived canonical row needs a shared provenance shape: `source_kind`, `source_name`, `source_url`, `source_record_id`, `source_version`, `fetched_at`, `last_verified_at`, `verification_status`, `freshness_at` or a deterministic freshness policy, `verification_note`, `synthetic`, and a stable `record_fingerprint`. The exact implementation may be shared columns or a provenance table plus foreign key, but API payloads and test queries must expose the same semantics.

Derived rows inherit the strongest synthetic status of their inputs. A live qualification joined to synthetic centre supply is not a live opportunity claim. Freshness is evaluated by entity type and is used by query policy: stale or missing coordinates cannot satisfy a nearby-centre result, and stale availability cannot be presented as current without an explicit stale marker.

### Centre geometry and privacy-safe origin

Use PostGIS `geography(Point,4326)` for centre points and a GiST index. Centre rows need coordinate status and verification metadata. A stored beneficiary home point is out of scope: the query accepts a coarse origin derived from an allowed district/block reference or an explicit coarse point supplied for the request, and the raw home coordinate is neither required nor persisted. The default nearby query must:

1. accept a coarse origin and mobility radius;
2. use `ST_DWithin` for radius exclusion and `ST_Distance` for ordering in the database;
3. return distance only for rows with allowed coordinate status and current freshness;
4. return an explicit `missing_origin`, `missing_coordinates`, or `stale_coordinates` outcome rather than a fabricated distance;
5. keep synthetic fixture geometry visibly synthetic and never infer coordinates from an aggregate district row.

### Opportunities and canonical vocabulary boundary

Phase 2 owns canonical storage and read contracts for training/RPL programmes, workshops, jobs, self-employment opportunities, and district/block demand signals. It does not build organization CRUD, candidate visibility, outcome workflows, or UI presentation; those belong to later phases. KaushalVani vocabulary such as `employment_preference`, `desired_occupation`, `mobility_km`, `training`, `certification`, `employment`, `self_employment`, `roadmap`, and `outcome` is normalized into canonical enums/keys only where it points to a sourced row.

No generated `qual-custom-*` entity, arbitrary fallback job, fixed distance, salary, grant, or centre is loadable. No-match is a typed empty/refusal result.

## PostgreSQL Capability Decision

Retain PostgreSQL as the single database with all three capabilities in one schema: `vector` for semantic retrieval, `pg_trgm` plus generated `tsvector`/GIN for text search, and `postgis` plus geography/GiST for spatial queries. The implementation must verify the selected pinned Compose image or a project-built image supports all three extensions before changing the runtime image. If the current `pgvector/pgvector:pg16` image lacks PostGIS, build one pinned PostGIS/PG16 image with the required pgvector package/extension; do not add a second database or silently drop vector support.

The Alembic chain must be exactly one head: `0002_doc_chunk_identity` remains the parent and the Phase 2 migration(s) follow it linearly. Fresh empty databases run `upgrade head`; already-seeded databases migrate without destructive data loss. `infra/db/init.sql` may create extensions for boot speed, but migrations remain self-sufficient and are the authority.

## Seed and Load Contract

- Every seed file remains an envelope with deterministic, sorted records and a provenance block.
- Fingerprints hash canonical record content, not volatile fetch timestamps.
- Natural keys are explicit per entity: qualification version, QP code, centre identity, programme/opportunity source record, demand geography plus role/time period, crosswalk phrase/language/version, and document source/page/section/content digest.
- Upserts update the same canonical row and preserve stable IDs; rerunning a pipeline does not increase counts or change record fingerprints.
- Loader output reports input rows, loaded/updated/skipped rows, failures, fingerprints, source modes, and synthetic counts. A failed input is visible and cannot be reported as a successful live load.
- A source snapshot manifest records source URL/name, retrieval date, source version or dataset fingerprint, local file hash, and whether data is live, synthetic, or mixed. No runtime code imports `pipelines` or makes HTTP calls to government hosts.

## Retrieval Contract

Structured lookup is authoritative for roles, qualifications, programmes, centres, opportunities, demand, distance, and numeric facts. Hybrid retrieval is for candidate generation and guideline/document questions. Each vector-bearing table stores embedding backend and dimension compatibility. Mock mode uses `hashing`; an E5 load uses `e5`; mixing them is a hard error, not a degraded approximation. Retrieval results carry source/provenance/synthetic markers and stable citations. The grounded backend must join retrieved candidate IDs back to canonical rows before response construction.

## Focused Verification Matrix

| Area | Command / check | Expected evidence |
|---|---|---|
| Migration | `alembic -c services/core/alembic.ini upgrade head` on empty DB, then repeat | One head; extensions and indexes exist; second run is a no-op. |
| Schema | `python -m pytest -q services/core/tests/test_gate1_models.py -x` | Decimal NSQF, version identity, provenance, PostGIS, vector/text/spatial indexes. |
| Ingestion | `python -m pytest -q services/core/tests/test_gate2_ingestion.py -x` | Snapshot shape, source manifest, synthetic/freshness propagation, no runtime government egress. |
| Idempotency | `python -m pytest -q services/core/tests/test_gate_phase2_data.py -x` | Two pipeline/load passes have equal counts, natural-key sets, and record fingerprints. |
| Retrieval | `python -m pytest -q services/core/tests/test_gate_phase2_retrieval.py -x` | Lexical/vector/RRF behavior, backend mismatch refusal, canonical-row authorization. |
| Spatial | `python -m pytest -q services/core/tests/test_gate_phase2_spatial.py -x` | Database-side sort/radius exclusion and honest missing/stale behavior. |
| Grounding | `python scripts/verify_grounding.py --n 50` | Zero invented names, QP codes, numbers, distances, centres, opportunities, or citations. |
| Portable preflight | `python scripts/preflight_phase1.py --compose infra/docker-compose.yml --env-file .env.example` | Reports unavailable Docker as blocked runtime evidence, never PASS. |

Docker-backed migration, seed, readiness, and end-to-end evidence is required during execution on a Docker-capable host. This session does not claim it.

## Source Snapshot and Provenance Assumptions

The Phase 1 pattern map records that the AVSAR and KaushalVani trees are currently untracked workspace references. Before implementation edits under those paths, execution must validate an accepted source snapshot manifest (relative path, byte hash, and Git status) or an equivalent tracked-source promotion. This planning package assumes the executor will satisfy that gate and will not treat an untracked working tree as a stable release source.

The committed seed snapshots are the authoritative offline inputs for this phase. The Kaushalverse snapshot currently reports 1,170 live qualification rows and 22.9% half-levels; centre supply is intentionally synthetic. These are source-state assumptions, not claims that the government endpoints are currently reachable or that synthetic centre geometry is official.

## Multi-Source Coverage Audit

| Source | ID | Feature / constraint | Plan | Status |
|---|---|---|---|---|
| GOAL | - | Every recommendation-ready fact comes from one searchable, spatially aware, provenance-labelled, repeatably loaded authority. | 02-01, 02-02, 02-03 | COVERED |
| REQ | KB-01 | Versioned QP/qualification, decimal NSQF, skills, duration, pathways, source and verification date. | 02-01, 02-02 | COVERED |
| REQ | KB-02 | Compatible role/skill embeddings and semantic matching. | 02-03 | COVERED |
| REQ | KB-03 | Verified centres, programmes, opportunities, local demand and spatial querying. | 02-01, 02-03 | COVERED |
| REQ | KB-04 | Idempotent seeds/loaders with provenance and failure reports. | 02-02 | COVERED |
| RESEARCH | R-01 | One linear Alembic head and self-sufficient vector/text/PostGIS extensions. | 02-01 | COVERED |
| RESEARCH | R-02 | Decimal-safe QP join and no generated fallback entities. | 02-01, 02-02 | COVERED |
| RESEARCH | R-03 | Provenance/synthetic/freshness propagation and source snapshot assumptions. | 02-01, 02-02, 02-03 | COVERED |
| RESEARCH | R-04 | Stable fingerprints and deterministic loader convergence. | 02-02 | COVERED |
| RESEARCH | R-05 | Hybrid lexical/vector retrieval; vectors never authorize facts. | 02-03 | COVERED |
| RESEARCH | R-06 | PostGIS database-side distance, radius exclusion, and honest missing/stale behavior. | 02-01, 02-03 | COVERED |
| RESEARCH | R-07 | KaushalVani vocabulary is canonicalized without duplicate runtime/schema. | 02-01, 02-02 | COVERED |
| CONTEXT | - | AVSAR FastAPI and one PostgreSQL lineage remain authority. | 02-01, 02-03 | COVERED |
| CONTEXT | - | Runtime never scrapes government hosts; committed snapshots and mock mode remain first-class. | 02-02, 02-03 | COVERED |
| CONTEXT | - | PostGIS centre geometry and privacy-safe origin are Phase 2 decisions. | 02-01, 02-03 | COVERED |
| CONTEXT | - | Docker/device evidence is deferred and must not be falsely claimed. | 02-01, 02-02, 02-03 | COVERED |

## Implementation Notes

No new Python dependency is required by the research. The implementation should prefer the existing SQLAlchemy/Alembic/pgvector/pytest patterns. PostGIS availability is the only infrastructure compatibility gate; it must be proven by extension/version queries before implementation claims spatial acceptance.
