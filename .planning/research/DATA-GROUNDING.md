# Jeevikasetu Data and Grounding Research

**Scope:** Existing AVSAR and KaushalVani implementations compared with the Jeevikasetu PRD, with emphasis on NSQF/QP knowledge, PostgreSQL/PostGIS/pgvector, ingestion, synthetic-data provenance, recommendation explainability, and verification.

**Researched:** 2026-09-28

## Executive Finding

AVSAR is the reusable foundation for the unified project. It has the stronger relational schema, Alembic migration discipline, committed seed envelopes, provenance model, idempotent loaders, NSQF/QP join logic, pgvector retrieval, deterministic recommendation engine, and executable grounding/offline gates. Its data layer is deliberately honest about synthetic PM-AJAY course membership and district supply.

KaushalVani is useful mainly as a domain vocabulary and demo-flow reference: its qualification, centre, employment, enterprise, roadmap, and outcome concepts map well to the PRD, and its recommendation payload shape is UI-friendly. However, the runtime is primarily an in-memory TypeScript store; the SQL schema is not the active source of truth, the seed script only prints a summary, and the AI/fallback paths contain fabricated or hard-coded values that cannot satisfy Jeevikasetu's grounding guarantee.

The largest shared gap is geographic data. Neither implementation currently provides the PRD's PostGIS centre model: AVSAR stores district/QP/centre seat aggregates without coordinates, while KaushalVani uses latitude/longitude columns but calculates distance from a hard-coded beneficiary coordinate in application code. The unified project must add real centre-level geometry, source/provenance, and database-side distance queries before claiming nearby-centre recommendations.

## Reusable Assets

### AVSAR data and ingestion

- [AVSAR initial Alembic schema](../../AVSAR-main/AVSAR-main/services/core/alembic/versions/689e6d7eb5f5_initial_schema_per_architecture_section_.py) provides `courses`, `qualifications`, `qp_descriptions`, `crosswalk`, `doc_chunks`, `centre_supply`, `districts`, `sessions`, `recommendations`, `consents`, `transcripts`, `audit_log`, and `ingest_runs`.
- `qualifications` preserves `qp_code`, optional NQR code/version, NSQF level as `NUMERIC(3,1)`, hours, credits, JSON eligibility, awarding body, validity, and `synthetic`. This is the best starting point for half-level-safe NSQF handling.
- `courses` keeps PM-AJAY catalogue identity separate from the register and records `source`, `level_inferred`, and `synthetic`. The join pipeline explicitly distinguishes register-assigned levels from hours-derived inference.
- [Pipeline common utilities](../../AVSAR-main/AVSAR-main/pipelines/common.py) define provenance (`live`, `synthetic`, `mixed`), deterministic synthetic RNG, raw-response caching, stable record fingerprints, and seed envelopes.
- [AVSAR loader](../../AVSAR-main/AVSAR-main/pipelines/load_to_db.py) performs bulk PostgreSQL upserts on natural keys and carries row flags into the database. It is the right loader pattern for a unified `make seed`.
- [Pipeline ordering](../../AVSAR-main/AVSAR-main/pipelines/run_all.py) is important: qualifications precede the PM-AJAY fallback, then QP/NSQF joining, crosswalk, supply, RAG, and demo data.
- [QP join](../../AVSAR-main/AVSAR-main/pipelines/03_join_qp_level.py) supports exact QP code, code serial, name matching, and an explicitly flagged hours-to-level fallback. It records coverage and warns when a match rate is tautological because the fallback catalogue came from the same register.
- [Guidelines RAG ingestion](../../AVSAR-main/AVSAR-main/pipelines/06_load_guidelines_rag.py) downloads/caches PM-AJAY and NSQF PDFs, chunks by section/page, prefixes section context into chunk text, embeds offline, and falls back only to cited canonical facts marked synthetic.
- [Ingest report](../../AVSAR-main/AVSAR-main/docs/ingest-report.md) is a valuable honesty template. It records that the current PM-AJAY catalogue membership and district supply are synthetic, while QP identities and the downloaded guideline corpus are source-backed.

### AVSAR retrieval and recommendation

- [AVSAR recommender](../../AVSAR-main/AVSAR-main/services/core/domain/recommender.py) separates curated crosswalk candidates from semantic candidates, applies a capability ceiling without integer-casting NSQF half levels, filters eligibility, scores deterministically, and returns top-N items with factors, weights, supply counts, sources, `synthetic`, `level_inferred`, and `stretch` state.
- Its score weights are explicit and sum to one: semantic fit, local supply, level fit, placement prior, and equity boost. `factors.weighted` makes the score auditable and reproducible.
- [Hybrid RAG retrieval](../../AVSAR-main/AVSAR-main/services/core/rag/retrieve.py) combines PostgreSQL `tsvector` lexical search and pgvector cosine search with reciprocal-rank fusion. It returns citations and synthetic markers.
- [Embedding adapter](../../AVSAR-main/AVSAR-main/services/core/rag/embedder.py) records the backend name and refuses to compare vectors created by an incompatible backend. This should remain a hard invariant during migration.
- [LLM guardrails](../../AVSAR-main/AVSAR-main/services/core/llm/guardrails.py) normalize Indic digits and Indian-number grouping, compare spoken numerals to the exact tool payload, and detect invented QP codes/course names in the grounding script.
- [Guarded verbalization ladder](../../AVSAR-main/AVSAR-main/services/core/llm/guarded.py) implements first attempt, one regeneration, then a deterministic template fallback. The fallback is grounded by construction and records degraded mode.

### KaushalVani domain assets

- [KaushalVani SQL schema](../../KaushalVani-main/KaushalVani-main/database/schema.sql) contains useful concepts: beneficiary profile fields, qualification eligibility/skills/NOS/progression, training centres, employment opportunities, enterprise pathways, recommendations, roadmaps, and outcomes.
- [KaushalVani store types](../../KaushalVani-main/KaushalVani-main/backend/src/db/store.ts) provide a UI-oriented vocabulary for recommendation factors, skill gaps, nearby centres, employment pathways, enterprise pathways, roadmaps, and outcome states.
- KaushalVani's `source_url`, `source_name`, and `last_verified_at` fields are worth retaining, but they must be augmented with explicit `source_record_id`, retrieval timestamp, verification status, and `synthetic` provenance.
- [Scenario script](../../KaushalVani-main/KaushalVani-main/scripts/test-scenarios.js) supplies six useful persona shapes for unified journey fixtures, although its assertions are too shallow for the PRD.

## Data and Schema Findings

### NSQF/QP knowledge

AVSAR's register-oriented model is more appropriate than KaushalVani's flattened qualification table. It preserves both QP and NQR identity, version identity, multiple duration components, JSON eligibility, validity, and source metadata. NSQF must remain decimal: AVSAR evidence shows approximately 23% of the current catalogue at half levels. Any migration to integer types or `int()` filters is a correctness bug.

KaushalVani stores `nsqf_level` as an integer and uses mostly level-4 demo records. Its roadmap and UI also hard-code level 4 in several places. Those values can seed persona fixtures but must not become the canonical knowledge model.

The curated AVSAR crosswalk is especially reusable: reviewed multilingual phrases map informal aspirations to exact QP codes, with declared gaps that cause refusal rather than an unrelated recommendation. Retain `status`, reviewer, version, language, and source-file fields. Treat semantic vector recall as candidate generation, never as permission to invent a qualification.

### PostgreSQL, pgvector, and PostGIS

AVSAR correctly enables `vector` and `pg_trgm`, uses 768-dimensional vectors, HNSW indexes, and a generated `tsvector` plus GIN index for hybrid retrieval. Its migrations are self-sufficient on a clean database. These are direct reuse candidates.

AVSAR does **not** enable PostGIS and has no geometry column. `centre_supply` contains `district_code`, `qp_code`, `centre_name`, and `seats`; recommendation logic only aggregates seats and centre counts per district. It cannot sort actual centres by distance or return a map location.

KaushalVani has `lat`/`lng` numeric columns and an application Haversine helper, but no PostGIS extension, spatial index, beneficiary coordinates in the request, or database-side radius query. The recommendation controller hard-codes the beneficiary point near Aurangabad. This is unsuitable for real district/block recommendations and can silently produce false proximity claims.

Unified schema recommendation:

- Enable `postgis` alongside `vector` and `pg_trgm` in the migration and local image.
- Add `training_centres.geom geography(Point,4326) NOT NULL` where coordinates are verified, plus source and verification metadata.
- Store beneficiary location as privacy-conscious district/block or coarse geography; do not require precise home coordinates.
- Add a GiST index on centre geometry and query `ST_DWithin`/`ST_Distance` against an explicit origin and mobility radius.
- Keep district/QP supply aggregates as a separate derived or aggregate table; do not treat them as centre locations.
- Make distance, centre identity, coordinates, and availability part of the tool payload before verbalization.

### Synthetic-data provenance

AVSAR has the correct end-to-end pattern: provenance at the seed envelope, `synthetic` on every record, database columns, API/dashboard summaries, exports, and recommendation items. `ingest_runs` records pipeline mode and failure notes. The current data report correctly distinguishes synthetic catalogue membership from real QP identities.

KaushalVani has a dashboard disclaimer and generates a synthetic cohort in `store.ts`, but there is no per-record `synthetic` field in the SQL schema or TypeScript interfaces, and the standalone [seed script](../../KaushalVani-main/KaushalVani-main/scripts/seed-demo-data.js) does not write data. Qualification and opportunity records appear official because they have government-looking URLs without an enforceable provenance flag. This is a migration and trust risk.

The unified project should require `synthetic`, `source_kind`, `source_url`, `source_record_id`, `fetched_at`, `last_verified_at`, and `verification_note` on every seedable catalogue/opportunity/centre record. Derived records should retain the strongest synthetic status of their inputs; joins must never relabel synthetic data as live.

## Recommendation and Explainability Findings

AVSAR's deterministic engine is the preferred core. It produces a score breakdown whose components, weights, raw values, and weighted contributions can be replayed. It uses explicit refusal states for declared coverage gaps and avoids gender-based filtering. It also persists enough recommendation data to restate the original decision.

KaushalVani's factor list is a useful presentation contract, but its implementation has serious grounding risks:

- The Python AI service assigns fixed scores and claims a centre is within the beneficiary's radius without calculating it from the supplied centres.
- The TypeScript fallback uses a hard-coded origin, fixed default distance, loose string matching, and fixed demand assumptions.
- When no catalogue item scores well, it creates a `qual-custom-*` qualification with a generated QP code, NSQF level, duration, skills, and source URL. This directly violates the PRD's no-invention rule.
- It falls back to arbitrary first jobs/enterprise paths when no real match exists.
- `missingSkills = bestQual.skills.slice(2)` is not a comparison against the beneficiary profile.
- The AI path returns only the first centre with a hard-coded `8.4` km distance.

Migration rule: remove the custom qualification path entirely. A no-match result must be a refusal/handoff or a recommendation backed by a real database row. Every explanation sentence must be generated from persisted factor values and entity payloads, not from templates containing independent numbers or claims.

## Verification Gates for the Unified Project

Retain and promote these AVSAR gates:

1. **Clean schema gate:** Alembic applies from an empty PostgreSQL database; `vector`, `pg_trgm`, and `postgis` extensions exist; migrations are repeatable; exactly one head exists.
2. **Schema fidelity gate:** ORM and live schema agree; vector dimensions, NSQF `NUMERIC(3,1)`, unique natural keys, HNSW/GIN/GiST indexes, and foreign keys are checked.
3. **Seed provenance gate:** committed seed envelopes contain provenance, row counts, source, mode, and failure/fallback explanation. Synthetic snapshots have every row flagged.
4. **Idempotency gate:** run ingestion and loading twice; natural-key counts and record fingerprints converge without duplicates.
5. **QP/NSQF gate:** exact/serial/fuzzy join coverage is reported; half levels survive; inferred levels are visibly marked; tautological fallback coverage is disclosed.
6. **Embedding gate:** all vectors in an index use one backend and dimension; runtime refuses incompatible vectors; crosswalk/QP/RAG embeddings are deterministic in mock mode.
7. **Recommendation gate:** deterministic repeatability, score weights sum to one, eligibility and mobility filters are tested, no-match and declared-gap refusal paths exist, and every output item contains `score_breakdown`, explanation, source, and synthetic status.
8. **Geospatial gate:** database-side PostGIS distance results are checked against known fixtures; centres are sorted by distance; out-of-radius and missing-coordinate cases do not claim proximity.
9. **Grounding gate:** at least 50 randomized sessions exercise curated and free-text aspirations across supported languages. Check numerals, QP codes, qualification names, NSQF levels, hours, money, percentages, centre names, distances, seat counts, and citations against the exact tool payload. Zero invented entities.
10. **Grounded verbalizer gate:** force an ungrounded provider response; verify one regeneration, then template fallback, `grounded=true` only after passing, and `degraded=true` when fallback is used.
11. **Synthetic visibility gate:** synthetic markers survive DB -> API -> UI -> CSV/XLSX export and appear on recommendation, centre, opportunity, and analytics records.
12. **Offline/provider gate:** with network blocked, DB unavailable, and provider credentials revoked, mock/template paths complete or return an honest degraded/refusal response. No runtime government-site calls.
13. **Journey gate:** the PRD persona completes consent, five profile slots, aspiration, recommendation, nearest centre, and outcome update in mock mode. Assert the recommendation is backed by a real row and all spoken facts pass grounding.
14. **Explainability gate:** replay the stored score from persisted factors and weights; verify the displayed explanation names only factors that contributed to that score.

## Gaps and Migration Risks

- **Active source of truth:** KaushalVani's SQL schema and in-memory store diverge. Do not migrate both independently. Choose AVSAR/FastAPI/PostgreSQL as the canonical backend and import KaushalVani only as reviewed seed/domain fixtures.
- **PostGIS absence:** neither project meets the PRD's spatial requirement. Adding geometry requires coordinate quality rules, privacy decisions, source verification, and a new distance test suite.
- **Centre granularity:** AVSAR aggregate supply rows cannot be converted into real centre coordinates. They must remain synthetic aggregate availability or be replaced by a verified centre feed.
- **Synthetic ambiguity:** source URLs alone are not evidence of live data. Add explicit row-level provenance before importing KaushalVani records.
- **Fabricated fallback entities:** generated QP codes, durations, centre distances, salaries, grant claims, and arbitrary fallback opportunities must be deleted or changed to refusal/handoff behavior.
- **Grounding scope:** AVSAR's numeral checker is strong but does not fully prove that arbitrary spoken names, paraphrased claims, spelled-out numbers, or salary/distance claims are grounded. Add structured entity token checks and prefer template/tool rendering for high-risk facts.
- **RAG authority:** retrieved guideline text is suitable for scheme-fact Q&A with citations, but it must not select courses or override the deterministic recommendation engine.
- **Privacy:** KaushalVani carries more direct beneficiary PII fields; importing them requires consent, retention, audit, and synthetic tagging decisions. AVSAR's session/consent model is the safer base.
- **Versioning:** qualification revisions need stable version identity and effective/valid dates. A QP code alone is not sufficient as a durable foreign key.
- **Data freshness:** `last_verified_at` should be enforced in API/UI behavior, not merely displayed. Stale source-backed rows should be marked stale or withheld from claims of current availability.

## Recommended Unification Order

1. Adopt AVSAR's PostgreSQL/Alembic model, seed envelope, provenance, loader, and test-gate patterns.
2. Import KaushalVani's domain fields and six persona scenarios as reviewed fixtures, adding explicit synthetic metadata.
3. Add PostGIS centre geometry and privacy-safe beneficiary origin handling before implementing nearby-centre ranking.
4. Preserve AVSAR's decimal NSQF/QP join and crosswalk; expand qualification pathways, RPL, opportunities, and outcomes around those stable identities.
5. Keep recommendation selection deterministic and database-backed; use an LLM only as a constrained verbalizer over a strict tool payload.
6. Expand AVSAR grounding and offline drills to cover all numeric and named entities exposed by the richer unified payload.

## Source Files Consulted

- [Jeevikasetu PRD](../../JEEVIKASETU-GSD-PRD.md)
- [AVSAR migration](../../AVSAR-main/AVSAR-main/services/core/alembic/versions/689e6d7eb5f5_initial_schema_per_architecture_section_.py)
- [AVSAR ingestion utilities](../../AVSAR-main/AVSAR-main/pipelines/common.py)
- [AVSAR DB loader](../../AVSAR-main/AVSAR-main/pipelines/load_to_db.py)
- [AVSAR QP join](../../AVSAR-main/AVSAR-main/pipelines/03_join_qp_level.py)
- [AVSAR RAG ingestion](../../AVSAR-main/AVSAR-main/pipelines/06_load_guidelines_rag.py)
- [AVSAR recommender](../../AVSAR-main/AVSAR-main/services/core/domain/recommender.py)
- [AVSAR hybrid retrieval](../../AVSAR-main/AVSAR-main/services/core/rag/retrieve.py)
- [AVSAR grounding guardrails](../../AVSAR-main/AVSAR-main/services/core/llm/guardrails.py)
- [AVSAR guarded verbalizer](../../AVSAR-main/AVSAR-main/services/core/llm/guarded.py)
- [AVSAR grounding script](../../AVSAR-main/AVSAR-main/scripts/verify_grounding.py)
- [AVSAR offline drill](../../AVSAR-main/AVSAR-main/scripts/drill_offline.py)
- [AVSAR ingestion tests](../../AVSAR-main/AVSAR-main/services/core/tests/test_gate2_ingestion.py)
- [AVSAR schema tests](../../AVSAR-main/AVSAR-main/services/core/tests/test_gate1_models.py)
- [AVSAR recommendation tests](../../AVSAR-main/AVSAR-main/services/core/tests/test_gate4_recommender.py)
- [AVSAR guardrail tests](../../AVSAR-main/AVSAR-main/services/core/tests/test_gate7_llm_guardrails.py)
- [KaushalVani SQL schema](../../KaushalVani-main/KaushalVani-main/database/schema.sql)
- [KaushalVani store](../../KaushalVani-main/KaushalVani-main/backend/src/db/store.ts)
- [KaushalVani recommendation controller](../../KaushalVani-main/KaushalVani-main/backend/src/controllers/recommendation.controller.ts)
- [KaushalVani AI recommendation service](../../KaushalVani-main/KaushalVani-main/ai-service/main.py)
- [KaushalVani seed script](../../KaushalVani-main/KaushalVani-main/scripts/seed-demo-data.js)
- [KaushalVani scenarios](../../KaushalVani-main/KaushalVani-main/scripts/test-scenarios.js)
