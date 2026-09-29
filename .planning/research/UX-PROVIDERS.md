# Jeevikasetu UX, Voice Providers, Offline Behavior, and Portal Research

**Project:** Jeevikasetu
**Research date:** 2026-09-28
**Scope:** Existing PRD, AVSAR web app, KaushalVani frontend/backend/AI service, provider adapters, demo scripts, and deployment documents.
**Overall confidence:** HIGH for repository behavior; MEDIUM for production provider/platform conclusions because live credentials and field devices were not exercised.

## Executive Recommendation

Use AVSAR's Next.js PWA as the smallest evidence-based beneficiary and officer-portal path for the hackathon milestone. It is the only inspected implementation that already connects the major UX requirements into one coherent flow: language selection, consent, guided profile capture, free-speech aspiration, confidence/confirmation, grounded recommendations, streamed TTS, accessible focus handling, officer analytics, exports, synthetic-data labels, and a mock mode that is tested for airplane-mode operation.

Do not interpret this as evidence that Flutter is technically unsuitable. Flutter remains a reasonable later choice if native Android audio behavior, background recording, device integration, or a true offline-first data store becomes the dominant constraint. The current evidence does not justify paying the cost of a second client while the shared backend, organization workflows, and real offline write semantics are incomplete.

Adopt a short decision gate before committing beyond the PWA: validate the AVSAR PWA on the target low-end Android devices and target browsers, with microphone permissions denied/granted, network disabled after initial install, and Marathi/Hindi/Telugu recordings. Proceed with PWA if those tests pass and add a small explicit offline outbox for profile/session writes. Reconsider Flutter only for a measured failure such as unreliable capture/playback on the target device, unacceptable browser permission friction, or a required native capability that cannot be delivered by the PWA.

## Evidence Base

| Area | Strongest evidence | What it proves |
|---|---|---|
| Product constraints | `JEEVIKASETU-GSD-PRD.md` | Voice-first, text fallback, 72 px touch target, mock/offline journey, accessibility, and distinct org/officer requirements are non-negotiable. |
| Beneficiary UX | `AVSAR-main/AVSAR-main/apps/web/app/start/StartClient.tsx`, `apps/web/components/ui.tsx` | A working PWA flow implements the core journey and accessible interaction patterns. |
| Browser audio | `AVSAR-main/AVSAR-main/apps/web/lib/audio.ts` | Browser capture is normalized to 16 kHz mono WAV, capped at 15 seconds, with echo cancellation/noise suppression and streamed TTS playback. |
| Provider resilience | `AVSAR-main/AVSAR-main/services/core/speech/router.py`, `bhashini.py`, `sarvam.py`, `mock.py` | Provider abstraction, failover/demotion, dynamic Bhashini endpoint handling, and a nontrivial fixture-backed mock exist in code. |
| Offline/demo | `AVSAR-main/AVSAR-main/docs/runbook.md`, `scripts/drill_offline.py`, `apps/web/public/sw.js` | Full stack mock mode and failure drills are documented/tested; browser caching is intentionally conservative. |
| Officer workflow | `AVSAR-main/AVSAR-main/apps/web/app/dashboard/DashboardClient.tsx`, `services/core/api/dashboard.py`, `api/exports.py` | Role-gated aggregate/drill-down dashboard, gap view, session inspection, crosswalk review, audit and export paths exist. |
| Alternate frontend | `KaushalVani-main/KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`, `pages/AdminDashboardPage.tsx`, `pages/OpportunitiesPage.tsx` | React/Vite demonstrates a quick prototype UX, browser speech fallback, accessibility toolbar, beneficiary opportunity pages, and a dashboard, but with weaker provider/offline guarantees. |

The workspace hook referenced `.planning/STATE.md`, but that file is not present in the workspace root. This research therefore uses the PRD and checked-in project documents as the scope boundary and does not modify planning state.

## Beneficiary UX Findings

### AVSAR PWA: strongest current baseline

The AVSAR flow is deliberately guided before open speech. It selects language, records consent, uses option grids for profile slots, then offers aspiration suggestions plus a microphone. This matches the PRD and the AVSAR plan's field-informed rule: guided choices first, free speech second, with menu fallback.

Concrete strengths:

- `StartClient.tsx` updates the document language, moves focus to each new question, has a skip link, uses `aria-live` for speech/errors, exposes captions/transcripts, and provides text choices alongside voice.
- `MicButton` is 128 by 128 CSS pixels, has `aria-pressed`, a screen-reader label, and a visible state label. This exceeds the PRD's 72 px target.
- `audio.ts` requests echo cancellation, noise suppression, and auto gain control; converts browser-native WebM/Opus or another supported format to mono 16 kHz PCM WAV; and hard-caps a turn at 15 seconds.
- TTS is sentence-chunked and queued. A new turn stops current playback, providing barge-in behavior. Audio errors resolve without blocking the text path.
- Recommendation cards show the reason, NSQF level, duration, sector, QP, assistance text, seats, synthetic badge, and a grounded/template status. This supports explainability and trust.
- Error payloads are intended to be human-readable and speakable; the UI has retry controls and explicit degraded/offline notices.

Limitations to carry into the Jeevikasetu design:

- The PWA is still a browser microphone experience. Secure-context rules, browser permission prompts, device codec support, and autoplay policies remain operational risks.
- Text fallback is present through choices and `postTurn` text payloads, but the UX should make that fallback prominent on every voice step, not only when menu mode is entered.
- The flow's offline notice is honest, but the complete journey depends on the local core/database being up. Browser offline alone is not enough for a fresh user session.

### KaushalVani frontend: useful UX ideas, weaker behavioral contract

KaushalVani has a large voice recorder, audio replay/read-aloud, Marathi/Hindi/English labels, a high-contrast/text-size toolbar, and a multi-page journey from assessment through skill gap, recommendations, training, opportunities, and roadmap. It is a useful information-architecture reference for outcome tracking and beneficiary-facing opportunity presentation.

However, `VoiceRecorder.tsx` prefers the browser Web Speech Recognition API, falls back to `MediaRecorder` and a server call, then falls back to a canned sample transcript or simulated capture. That is useful for a demo, but it can silently turn microphone failure into a plausible transcript. Jeevikasetu should label simulated/mock input prominently and require explicit confirmation before treating it as a beneficiary statement.

The frontend package has no PWA, IndexedDB, or service-worker dependency. The inspected source has no offline queue or offline event handling. Its accessibility toolbar is valuable, but the implementation should be treated as a prototype pattern rather than proof of WCAG compliance.

## Accessibility Findings

AVSAR has the more directly testable accessibility implementation: skip link, semantic headings, `lang` updates, focus management, screen-reader-only labels, `aria-live`, accessible table captions, labelled district controls, visible high-contrast states, and a large mic target. The checked-in Lighthouse JSON files show that accessibility was at least measured for home and start routes.

KaushalVani offers high contrast, text scaling, language selection, screen-reader-oriented copy, and audio read-aloud. Its recorder also has an accessible label, but several controls rely on title text and small toolbar targets. Its admin dashboard contains dense cards, tables, and filters; it needs a real keyboard/contrast audit before being considered compliant.

Recommended acceptance checks for Jeevikasetu:

1. Keyboard-only completion of consent, profile choices, text fallback, recommendation replay, and retry.
2. Screen-reader announcement of language, current question, transcript confidence, degraded state, and recommendation grounding.
3. 72 px minimum touch target for all primary beneficiary actions, with scalable text and no clipping at 200 percent zoom.
4. Contrast and focus-visible checks on beneficiary and officer routes separately.
5. Target-device tests with browser microphone permission denied, revoked, and restored.

## Voice, STT, and TTS Provider Findings

### AVSAR provider architecture

AVSAR has the clearest production-shaped provider boundary. `SpeechRouter` selects the configured provider, orders fallbacks, counts failures, demotes a failing provider, and always leaves `mock` as the floor. Results are marked degraded when they come from below the configured primary, so the UI can tell the truth.

The provider path is:

`Sarvam or Bhashini or Azure -> mock`

The router comments explain that Sarvam is currently the live choice when configured because Bhashini approval is unavailable to the team. This is a practical distinction from the PRD's preferred ordering: Bhashini can remain the policy-level primary, but the deployed configuration should reflect credentials and licensing actually available.

The Bhashini adapter correctly resolves the dynamic callback URL and dynamic inference header name/value from the pipeline-config response. It caches configuration per task/language and retries a 5xx once. This avoids a common integration failure: hardcoding the inference endpoint or auth header.

The Sarvam adapter uses server-side credentials, language locales such as `hi-IN` and `mr-IN`, a 15-second browser cap with a 30-second server guard, retry-on-5xx, and non-retryable handling for missing/rejected credentials. Its confidence behavior is conservative: it uses 1.0 for a nonempty transcript, 0.0 for empty, and 0.5 when the detected language differs from the session language. This is preferable to fabricating a vendor confidence value, but it is not a calibrated ASR confidence score.

The mock provider is unusually strong for a demo: it replays per-language, per-dialogue-step fixtures; generates playable 16 kHz mono WAV tones; and has empty, low-confidence, unknown, and gap variants to exercise FSM branches. The fixture audio is explicitly not human speech. The UI and demo script must say that mock audio validates the transport and journey, not speech recognition quality.

### KaushalVani provider path

KaushalVani places a Node controller in front of a Python FastAPI AI service. The controller forwards audio/text to `/ai/bhashini/stt`, but when the AI service fails it returns a canned transcript. Its TTS route returns real audio only if the AI service supplies it; otherwise it returns JSON containing the input text and a message that synthesis was simulated. The frontend's language context can use browser `speechSynthesis`, which is device/browser dependent and not equivalent to a controlled TTS provider.

This path is adequate as a prototype fallback, but it lacks AVSAR's provider contract, explicit degraded metadata, failure demotion, dynamic Bhashini contract handling, and playable offline TTS fixtures. Jeevikasetu should adopt the AVSAR adapter/router contract rather than the KaushalVani fallback semantics.

### Provider recommendation

Keep one server-side speech interface with `transcribe`, `synthesize`, `health`, provider name, latency, and degraded state. Use:

1. `mock` as an always-available, fixture-backed acceptance path.
2. Bhashini when the project has the required access and production licensing path.
3. Sarvam as the practical live fallback if its credentials and cost/rate limits are acceptable.
4. A self-hosted Indic ASR/TTS path only after measuring target-device/server CPU and language quality; do not call generic Whisper the default Indic fallback without evidence.

Do not expose provider keys to either client. Keep all provider calls in the core service and preserve provider, confidence, latency, and degraded metadata in the session record.

## Mock and Offline Behavior

### What AVSAR actually guarantees

The documented AVSAR runbook and tests support a strong demo claim: with `VOICE_PROVIDER=mock` and `LLM_PROVIDER=mock`, the full journey can run without API keys and without internet, provided the Docker images, local database, Redis, seeds, and assets have already been built/loaded. `make drill` covers network loss, database interruption, and provider-key failure. `make grounding` validates that verbalized recommendation facts come from tool/DB data.

The browser service worker is intentionally conservative:

- It precaches the shell routes and icons.
- It caches revisioned assets cache-first.
- It uses network-first with a short timeout for HTML and same-origin GET/API requests.
- It never caches or replays non-GET requests, specifically to avoid duplicating conversational POST turns.

This is the correct safety choice for a conversational FSM, but it means the PWA is not yet a complete offline-first beneficiary application. `idb-keyval` is listed as a dependency, but the inspected app source does not use it. There is no implemented offline outbox for profile/session writes. A no-network fresh session works only when the local core is available, not merely because the browser has cached pages.

### Required offline addition

For Jeevikasetu, define offline scope precisely:

- Cache prompts, language assets, UI shell, and a bounded set of seeded recommendations/centres for the demo.
- Store consent/profile drafts and unsent user actions in IndexedDB with an idempotency key and session state version.
- Sync only safe, idempotent operations when connectivity returns; never blindly replay a conversational POST.
- Show `queued`, `synced`, `failed`, and `needs facilitator` states.
- Keep raw audio out of durable storage by default; retain only the minimum needed to retry, with consent and a size/expiry limit.
- Run the same journey against `docker run --network none` or an equivalent local stack, plus a browser-level offline test. The two tests prove different things.

Flutter would make an offline local database and native audio stack more natural, but it does not remove the need for sync conflict handling, provider fixtures, privacy rules, or a local backend. It is not a substitute for the missing data contract.

## Organization and Officer Portal Workflows

### AVSAR officer/admin evidence

AVSAR implements a useful officer workflow: viewer/officer/admin roles, JWT-based auth, aggregate dashboard access, officer-only individual session drill-down, district filtering, aspiration demand versus local supply, consent and demographic compliance chips, session transcript/recommendation inspection, CSV/XLSX export, and an admin-only crosswalk editor with audit log. The runbook provides a concrete demo sequence: filter a district, open a session, inspect consent and recommendation, export data, and view supply gaps.

This is strong evidence for the officer side of the PRD, but it is not the full portal requirement. The inspected AVSAR routes and role model use `viewer`, `officer`, and `admin`; they do not implement the PRD's `organization` role, organization-owned course/job/workshop posting, candidate matching filters, or organization outcome updates.

### KaushalVani portal evidence

KaushalVani has an administrator dashboard with district/gender filters, cohort funnel, sector demand, beneficiary list, and outcome status update. Its opportunities page is beneficiary-facing and presents wage and enterprise pathways. Its API documentation covers qualifications, centres, jobs, enterprise pathways, dashboard analytics, and outcome updates.

It does not provide evidence of a real organization portal. The auth route accepts a small hard-coded official/admin demo credential shape and returns mock JWT strings; there is no visible organization role, organization ownership, candidate search/filter endpoint, opportunity creation endpoint, or audited server-side RBAC. The opportunity records are generated/seeded by the backend store and rendered to beneficiaries.

### Smallest portal implementation path

Keep AVSAR's officer dashboard and add the missing organization slice after the core beneficiary/recommendation contract is stable:

- Add `organization` to the server-side role enum and JWT/RBAC tests.
- Add organization-owned opportunities with source, synthetic flag, status, location, eligibility, and audit fields.
- Add organization views for posting/editing its own opportunities and searching privacy-minimized candidate summaries by district/block, language, skill, and NSQF level.
- Keep raw transcripts, phone identifiers, and unnecessary PII hidden from organizations by default.
- Add explicit beneficiary consent/visibility rules and outcome-update audit entries.
- Reuse the same Next.js shell and API contracts; do not create a separate mobile organization client.

## Flutter Versus Next.js/PWA

| Criterion | Next.js/PWA | Flutter |
|---|---|---|
| Existing evidence | AVSAR already implements the beneficiary and officer surfaces, service worker, browser audio normalization, and deployment. | PRD chooses Flutter, but this workspace contains no Flutter client evidence to validate. |
| Smallest implementation | Reuse AVSAR components, API, tests, mock fixtures, and Docker deployment. | Build a new client, native audio path, accessibility layer, auth/session state, and portal remains separate. |
| Browser/device reach | Immediate URL, installable PWA, can run on shared Android devices and desktop. | Strong Android packaging and native APIs, but requires app distribution/install and a second build pipeline. |
| Audio | MediaRecorder plus Web Audio conversion works where secure-context browser APIs are available; permission/autoplay/codec differences are risks. | More predictable native recording/playback and background/device integration; plugin quality and platform permissions are still risks. |
| Offline | Service worker can cache shell; explicit IndexedDB outbox is still required. | Local persistence is straightforward, but sync and backend availability are still required. |
| Accessibility | Existing semantic HTML, focus, ARIA, browser screen readers, and Lighthouse evidence. | Can be strong, but requires a separate semantics/large-text/screen-reader audit. |
| Portal reuse | Same Next.js codebase can host beneficiary, officer, admin, and organization routes. | Flutter beneficiary app would still need a separate React/Next.js portal per the PRD. |
| Demo operations | Docker Compose already starts core and web; no app install. | Adds APK/build/signing/device setup and a second failure surface. |
| Future IVR/WhatsApp | Client-independent because AVSAR core owns the session protocol. | Same backend benefit; Flutter does not help telephony integration. |

### Decision gate

Choose **Next.js/PWA now** if these four checks pass on target Android hardware:

1. Mic permission, 15-second capture, WAV conversion, and playback complete in Chrome or the supported browser.
2. Hindi/Marathi/Telugu text fallback, screen-reader labels, and 200 percent text scaling remain usable.
3. A preloaded local stack completes the mock journey with network disabled, and the planned IndexedDB outbox can safely sync a draft.
4. First-load/install and recovery instructions are acceptable for a shared-device facilitator workflow.

Choose **Flutter for the beneficiary client** only if a measured check fails materially or if the product requires native capabilities such as background audio, device-level integrations, or a distribution model where an installed Android app is clearly more practical. Keep the Next.js portal regardless.

## Deployment Implications

AVSAR's Docker Compose runs Postgres/pgvector, Redis, FastAPI core, and Next.js web, with optional nginx. The runbook is unusually explicit about prebuilding images, seeding data, checking health, running grounding/drill/latency tests, and demoing with Wi-Fi off. This is the best deployment baseline in the workspace.

KaushalVani's Compose stack is a conventional four-service deployment: Postgres, Node backend, Python AI service, and Vite frontend. Its deployment documentation covers startup URLs but does not document an offline drill, health-gated startup, provider failover, retention, or browser service-worker strategy. It is easier to understand, but less proven for the PRD's failure-mode requirements.

For Jeevikasetu, keep deployment local-first and single-command for the demo, but separate these claims:

- **Offline demo:** local core/database/seeds plus mock providers, verified by network isolation.
- **Offline browser shell:** service worker and cached assets, verified with a fresh installed PWA.
- **Offline beneficiary continuity:** IndexedDB outbox and sync semantics, verified by a browser integration test.
- **Provider resilience:** server-side failover and degraded UI, verified by key rejection/5xx drills.

## Roadmap Implications

1. **Foundation and provider contract:** copy the AVSAR speech/router/mock contract and its explicit degraded metadata; retain the shared session protocol.
2. **Beneficiary PWA slice:** reuse AVSAR's guided flow and accessibility patterns; add visible text fallback and facilitator/shared-device affordances.
3. **Offline continuity:** implement IndexedDB draft/outbox behavior with idempotency and explicit sync states; do not claim that service-worker caching alone meets the PRD.
4. **Officer portal:** retain AVSAR dashboard, gap, session detail, export, crosswalk, and audit patterns.
5. **Organization portal:** add the missing organization role and owned opportunities/candidate matching as a distinct backend/UI scope item.
6. **Platform spike:** run the four decision-gate checks before deciding whether native Flutter is warranted.

## Open Questions / Follow-up Research

- Which exact low-end Android models, browsers, and screen readers are in the pilot environment?
- Is the offline requirement a full local-stack venue demo, a disconnected beneficiary app with later sync, or both? The implementation cost differs substantially.
- Which Bhashini access/licensing tier is available for the intended deployment, and is Sarvam an approved fallback for the project budget and data policy?
- What organization privacy policy governs candidate visibility and contact access after beneficiary consent?
- Does the beneficiary need background recording, call interruption handling, Bluetooth headsets, or other native features that would materially change the Flutter decision?

## Source Files Inspected

- `JEEVIKASETU-GSD-PRD.md`
- `AVSAR-main/AVSAR-main/README.md`
- `AVSAR-main/AVSAR-main/ARCHITECTURE.md`
- `AVSAR-main/AVSAR-main/TECH_STACK.md`
- `AVSAR-main/AVSAR-main/PLAN.md`
- `AVSAR-main/AVSAR-main/apps/web/app/start/StartClient.tsx`
- `AVSAR-main/AVSAR-main/apps/web/app/dashboard/DashboardClient.tsx`
- `AVSAR-main/AVSAR-main/apps/web/components/ui.tsx`
- `AVSAR-main/AVSAR-main/apps/web/lib/audio.ts`
- `AVSAR-main/AVSAR-main/apps/web/public/sw.js`
- `AVSAR-main/AVSAR-main/services/core/speech/router.py`
- `AVSAR-main/AVSAR-main/services/core/speech/bhashini.py`
- `AVSAR-main/AVSAR-main/services/core/speech/sarvam.py`
- `AVSAR-main/AVSAR-main/services/core/speech/mock.py`
- `AVSAR-main/AVSAR-main/docs/runbook.md`
- `AVSAR-main/AVSAR-main/infra/docker-compose.yml`
- `KaushalVani-main/KaushalVani-main/README.md`
- `KaushalVani-main/KaushalVani-main/docs/ARCHITECTURE.md`
- `KaushalVani-main/KaushalVani-main/docs/API.md`
- `KaushalVani-main/KaushalVani-main/docs/DEPLOYMENT.md`
- `KaushalVani-main/KaushalVani-main/frontend/package.json`
- `KaushalVani-main/KaushalVani-main/frontend/src/components/VoiceRecorder.tsx`
- `KaushalVani-main/KaushalVani-main/frontend/src/components/AccessibilityToolbar.tsx`
- `KaushalVani-main/KaushalVani-main/frontend/src/pages/AdminDashboardPage.tsx`
- `KaushalVani-main/KaushalVani-main/frontend/src/pages/OpportunitiesPage.tsx`
- `KaushalVani-main/KaushalVani-main/backend/src/controllers/voice.controller.ts`
- `KaushalVani-main/KaushalVani-main/backend/src/controllers/admin.controller.ts`
- `KaushalVani-main/KaushalVani-main/ai-service/main.py`
- `KaushalVani-main/KaushalVani-main/docker-compose.yml`
