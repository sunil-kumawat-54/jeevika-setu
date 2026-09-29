# Phase 1 Plan Verification

**Phase:** Unified Foundation And Migration Boundary  
**Reviewed:** 2026-09-28  
**Result:** **BLOCKED** pending plan revision and environment/source-boundary decisions

## Scope Reviewed

Read `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, every file under `.planning/research/`, every file under this phase directory, and the cited AVSAR/KaushalVani source paths. Inspected the FastAPI factory and health/session routes, speech contract/router/mock, Next BFF proxy and session client, Compose, Makefile, CI workflow, and service worker.

## Requirement Coverage

| Requirement | Plan coverage | Result |
|---|---|---|
| VOI-03 | 01-01 | **FLAG:** server-side provider/mock contract is planned, but the named Whisper/fallback interpretation remains unresolved. |
| NFR-01 | 01-02, 01-03 | **BLOCK:** clean-stack/mock journey and client offline evidence cannot be completed in the current environment; no unavailable-tool gate or equivalent Windows fallback is planned. |
| NFR-02 | 01-02 | **PASS in intent:** CI explicitly adds grounding alongside lint, migrations/tests, and frontend checks. |

All three roadmap IDs appear in plan frontmatter. No other Phase 1 requirement is silently omitted.

## PASS Findings

### PASS-1: Goal and requirement mapping

The plans cover one FastAPI authority, provider selection/mock fallback, Compose/Make/CI, migration mapping, and the reversible client-platform gate. `VOI-03`, `NFR-01`, and `NFR-02` are assigned to the expected plans.

### PASS-2: Dependency order

The graph is acyclic and coherent: `01-01` is Wave 1; `01-02` and `01-03` are Wave 2 and both depend on `01-01`. No same-wave file overlap is declared between 01-02 and 01-03.

### PASS-3: Migration/source-boundary intent

The plans prohibit KaushalVani's Node gateway, standalone AI service, duplicate schema, generated QPs, fixed distances, and arbitrary fallback facts. The mapping scope includes roles, consent, provenance, synthetic markers, decimal NSQF, QP versions, and later-phase ownership.

### PASS-4: Reversibility intent

The Flutter/PWA gate preserves the `/v1` backend and Next.js organization/officer/admin portal whichever beneficiary client is selected. The service-worker plan preserves GET-only behavior and prohibits conversational POST replay.

## BLOCK Findings

### BLOCK-1: The planned BFF wiring does not reach `/v1`

**Required property:** The browser BFF and FastAPI contract must be wired to the same versioned route family.

**Evidence:** `apps/web/lib/session.ts` calls `/api/core/sessions`; the actual BFF at `apps/web/app/api/core/[...path]/route.ts` constructs `${CORE_URL}/${suffix}`. Plan 01-01 lists only `lib/session.ts` among web files and says to update the “Next BFF” there; it does not modify the proxy or `lib/api.ts`, nor specify a `/v1`-suffixed upstream. Plan 01-02 requires Compose healthchecks to call `/v1/healthz`. The tracer can therefore create FastAPI `/v1/*` routes while the BFF still forwards to unprefixed routes.

**Required correction:** Name and verify the actual proxy/upstream prefix wiring and prove session creation plus streamed turns traverse `/v1` without a second handler.

### BLOCK-2: Source provenance is an execution precondition but no plan establishes it

**Required property:** Planned source modifications must belong to an explicit authoritative source snapshot that execution can preserve and validate.

**Evidence:** `PATTERNS.md` says all AVSAR and KaushalVani files are untracked workspace references. Live `git ls-files AVSAR-main KaushalVani-main` returns no application paths, and `git status` shows both directories as untracked. The plans list many modifications under those paths but no source-snapshot/authority gate.

**Required correction:** Add a pre-execution gate that tracks or pins the accepted source snapshot and validates it before source edits.

### BLOCK-3: The client decision gate has no concrete target matrix

**Required property:** A blocking platform decision must be reproducible from named devices, browser versions, assistive technology, connectivity conditions, and pass/fail thresholds.

**Evidence:** Research and STATE identify the target Android models, browsers, screen readers, and disconnected scope as unspecified. Plan 01-03 says “the exact ... matrix supplied by the implementer,” but no matrix exists in the plan or context. Task 3 cannot distinguish material failure from untested conditions.

**Required correction:** Put the minimum target matrix and material-failure rule in plan/context before execution, or route the decision through an explicit escalation gate.

### BLOCK-4: NFR-01 verification is not feasible in the current Windows environment

**Required property:** The phase needs an executable, honest acceptance path for Compose startup, readiness, seed, and the mock journey, including unavailable-tool behavior.

**Evidence:** Neither `docker` nor `make` is available in this session. Plan 01-02 Task 1 verifies only `docker compose ... config`, which does not start services, check readiness, seed data, or run the journey. The broader verification assumes Docker and GNU Make/bash; no PowerShell/direct-command fallback or blocked preflight is planned. The client probe also requires a running API.

**Required correction:** Add a tool preflight that records Docker/GNU Make absence as blocked acceptance, plus supported Windows fallbacks for checks that can run without Make. Do not mark NFR-01 complete from config parsing.

### BLOCK-5: VOI-03's named Whisper/fallback path is unresolved

**Required property:** Phase 1 must deliver or explicitly resolve Bhashini, Whisper/fallback, and mock configuration through server-side interfaces.

**Evidence:** AVSAR contains `mock`, `bhashini`, `sarvam`, and `azure`; no named Whisper adapter exists. Plan 01-01 Task 2 says to document the unresolved interpretation and treat current paths as satisfying the contract, but neither records an accepted requirement decision nor adds an approved Whisper implementation/test.

**Required correction:** Resolve the interpretation before execution or add a concrete approved Whisper/fallback adapter and contract test. A documentation note alone is not exact requirement coverage.

## FLAG Findings

### FLAG-1: Draft/outbox behavior is asserted without an artifact or probe

**Required property:** A client spike criterion claiming queued/synced/failed/retry behavior needs a concrete artifact and executable evidence path.

**Evidence:** Research says the service worker is GET-only and no IndexedDB outbox exists. Plan 01-03 demands draft/outbox evidence but lists no outbox module, browser test harness, or fixture. The action does not clearly permit recording this criterion as unavailable, although the research assigns the gap to later work.

**Suggested resolution:** Narrow the Phase 1 spike to proving safe non-replay and record outbox as a later-phase gap, or add an explicit idempotent outbox probe/implementation.

### FLAG-2: Task verification commands under-test their claims

**Required property:** Each automated task check must distinguish task completion from a weaker static or unrelated check.

**Evidence:** Plan 01-02 Task 1 checks Compose syntax only; Tasks 2 and 3 reuse the same Gate 0 pytest command even though Task 3 changes CI and requires grounding as a blocking PR gate. Plan 01-03 Task 3 has no machine-checkable service-worker GET-only assertion.

**Suggested resolution:** Add clean-start/readiness/seed smoke verification where Docker is available, a workflow-content assertion for grounding, and a focused worker-safety test.

### FLAG-3: Decision references are not traceable

**Required property:** Locked-decision references must resolve to named planning decisions.

**Evidence:** Tasks refer to `D-01` and `D-02`, but `STATE.md` has no numbered decision table and no `D-02` entry. The roadmap mentions D-01 only in prose.

**Suggested resolution:** Replace references with exact decision names or add stable IDs before execution.

### FLAG-4: Low-confidence estimates deserve re-slicing review

**Required property:** Plan scope must stay within the context budget with enough confidence to preserve verification quality.

**Evidence:** 01-01 estimates 32,000 tokens, 01-02 30,000, and 01-03 28,000; all are `confidence: low`. 01-01 combines API versioning, provider contracts, and cross-repository mapping; 01-03 combines an HTTP/SSE probe, mapping docs, and a human device gate.

**Suggested resolution:** Run the calibrated estimate check and split migration or client evidence work if over budget.

## Verification Command Review

| Check | Result |
|---|---|
| Focused `pytest` commands | Planned and structurally appropriate, but depend on runtime/database assumptions not established by the plans. |
| `docker compose ... config` | **PASS as render check only; insufficient for NFR-01 runtime acceptance.** |
| `make ...` commands | **FLAG:** GNU Make is unavailable; add direct Windows commands or an explicit preflight block. |
| Client probe | **BLOCKED here:** requires a running `/v1` service and depends on unresolved BFF wiring. |
| Human device gate | **BLOCKED:** target matrix is unnamed. |
| CI grounding | Planned as blocking; add a focused assertion against the actual workflow and clean-checkout paths. |

## Overall Gate

**BLOCK.** Requirement assignment, dependency order, migration-boundary intent, and reversibility intent pass. Execution cannot reliably achieve the phase goal until BFF-to-`/v1` wiring, source provenance, target-device matrix, current-tooling preflight/fallback, and the VOI-03 Whisper interpretation are resolved. The outbox and task-specific verification gaps should be corrected in the same revision.

No application source files were modified and no commit was created during this review.
