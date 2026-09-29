# PLAN.md — Project AVSAR: Master Execution Plan

> **AVSAR** — *Aspiration-to-Vocational Skilling Assistant & Recommender* (अवसर = opportunity).
> A voice-first assistant that lets an SC beneficiary speak their livelihood aspiration in their own language and walk away with an NSQF-aligned skilling recommendation grounded in the PM-AJAY GIA guidelines — plus an officer dashboard that turns those captured aspirations into district-level livelihood maps and AAP-ready exports.
>
> This file = WHAT to build and WHEN, in every detail. Companion files: `research.md` (evidence), `ARCHITECTURE.md` (system design), `TECH_STACK.md` (exact stack/endpoints), `FABLE_PROMPT.md` (handoff prompt that builds it all).

---

## Table of Contents

1. [Problem framing (one paragraph you can memorize)](#1-problem-framing)
2. [Users & personas](#2-users--personas)
3. [Product scope: MVP vs demo-only vs roadmap](#3-product-scope)
4. [Feature specification](#4-feature-specification)
5. [Data plan: what to ingest, what to hand-build](#5-data-plan)
6. [The recommendation algorithm (precise)](#6-the-recommendation-algorithm)
7. [Dialogue design (voice UX)](#7-dialogue-design)
8. [Build phases](#8-build-phases)
   - Phase 0: Idea-round package (now)
   - Phase 1: Pre-finale preparation sprint
   - Phase 2: Grand finale hour-by-hour (36h)
   - Phase 3: Judge-proofing & rehearsal
9. [Team split (6 members)](#9-team-split)
10. [Demo script](#10-demo-script)
11. [Risk register](#11-risk-register)
12. [Judging-strategy map (9 official criteria)](#12-judging-strategy-map)
13. [Post-SIH roadmap](#13-post-sih-roadmap)
14. [Definition of done (acceptance criteria)](#14-definition-of-done)

---

## 1. Problem framing

Memorize this; it opens your pitch:

> Under PM-AJAY's Grant-in-Aid component, the government is legally required to spend ≥10% of released funds on skilling, and its own guidelines mandate that every job-role choice be validated against **beneficiary aspiration** AND **local job market**, then aligned to **NSQF Qualification Packs** (Guidelines May 2023, Ch. 3 §7.A.a.iv). Today that mapping is done on paper, in English, by district officers — while actual beneficiaries are largely non-literate, dialect-speaking SC youth and women whose aspirations never enter the system. Result: ₹736 cr spent against ₹2,140 cr budgeted in FY2024-25. **AVSAR closes that loop by voice**: speak your aspiration in Hindi/Marathi/Telugu, get back an NSQF-aligned, locally available course recommendation with women's-quota and loan-assistance facts, and give the officer a live livelihood map — all backed by the ministry's own portals and NCVET registers.

---

## 2. Users & personas

| Persona | Context | Needs from AVSAR |
|---|---|---|
| **Priya, 22, first-generation learner** (primary beneficiary) | Rural/block town; smartphone shared with family; reads slowly; speaks Marathi/Hindi mix | Speak freely, be understood despite dialect; get ONE clear next step (course name, how long, where, what support money exists); hear it again; get an SMS summary |
| **Ramesh, 45, informal artisan** | Feature phone OR no phone; low trust in forms | Phone-call path (IVR), DTMF menus, human callback option |
| **Lakshmi, SHG office bearer** | Semi-literate group leader; organizes 10–20 women | Group capture mode: run several members through on one device; printed/voice summary per member |
| **Block/Mission officer** (secondary user) | Uses pmajay.dosje.gov.in MIS today | Dashboard: aspirations heat-mapped by district/block; aspiration↔course-supply gaps; CSV/AAP-ready export; consent-flagged beneficiary lists |
| **State Skill Development Mission reviewer** | Endorses job-role selection per guidelines | Evidence pack: which aspirations drove which proposed job roles (audit trail = compliance artifact) |

Design rule from field evidence: Priya's flow is **guided menus + suggested phrases first, free speech second, DTMF fallback always** (Farmer.Chat: suggestion buttons drove >45% of interactions; Avaaj Otalo: keypad preferred over speech).

---

## 3. Product scope

### MVP — the thing that must WORK live at judging (non-negotiable)
1. **Voice conversation loop** (browser mic on PWA): language pick (hi/mr/te) → spoken consent → guided profile capture (5 questions) → free-speech aspiration → spoken recommendation → repeat/confirm → SMS-style text summary shown + linkable.
2. **Real data underneath**: PM-AJAY course catalogue (~1,893 QPs) ingested; Kaushalverse qualification details (hours, credits, NSQF level) joined; hand-built aspiration→QP crosswalk (v0 ≈ 150 colloquial phrases across the 10 GIA domains).
3. **Grounded recommendations**: every spoken claim traceable to a tool query result; LLM never invents course names/numbers (function-calling + citation-of-tool-output pattern).
4. **Officer dashboard**: list + map view of captured profiles; top-aspirations bar; simple gap view (aspirations vs available courses in district); CSV export.
5. **Auth**: beneficiaries = phone-number OTP-lite (mock OTP in demo mode, no SMS provider needed); officers = email/password with roles (`viewer`, `officer`, `admin`); JWT throughout.
6. **Mock-mode switch** (`VOICE_PROVIDER=mock`): recorded/fixed responses for the entire voice path so the demo survives dead internet, exhausted API keys, and rate limits.

### Demo-polish — do if hours allow (in priority order)
7. Telephony IVR number (Exotel trial) ringing into the same pipeline — even if judges just hear a recording of it working.
8. WhatsApp voice-note channel (send voice note → get voice reply) via webhook.
9. Hindi/mixed-language ASR self-hosted fallback (IndicWhisper checkpoint) running on the demo laptop.
10. Print-friendly one-page "beneficiary plan" PDF (course, centre, documents, scheme entitlements).

### Explicitly roadmap (slides only, never promised live)
- Production Bhashini partnership tier (Sahyogi/App Mitra) — PoC license constraint.
- NCS/SIDH live integration via MoU (no public APIs exist — say so; it shows research depth).
- Aadhaar e-KYC (voluntary, gated on UIDAI licensing) — NOT in build.
- More languages (Bhojpuri etc.) pending model coverage — cite WER evidence honestly.
- Offline kiosk mode (service-worker cached prompts + self-hosted ASR/TTS on a mini-PC).

---

## 4. Feature specification

### 4.1 Beneficiary conversation (state machine)

```
[START]
  ├─ LanguageSelect: "हिंदी / मराठी / తెలుగు / English" — big buttons + spoken menu (DTMF 1-4 on IVR)
  ├─ ConsentCapture: short spoken consent line + big ✓ button; stores {consent:true, ts, lang}; refusal ends call politely
  ├─ ProfileCapture (5 slots, each = suggested options + free speech):
  │    1. District (dropdown by state; type-ahead)          [slot: district]
  │    2. Age band (<18 /18-30/30-45/45+)                    [slot: age_band]
  │    3. Gender (female/male/other — drives ≥30% women quota logic)
  │    4. Education (none/up-to-5th/5th-8th/8th-10th/10th-12th/grad+)  → maps to NSQF entry-level cap
  │    5. Current work (unemployed/farm labour/artisan/SHG member/small trade/other)
  ├─ AspirationCapture: "आप क्या काम करना चाहते हैं? बोलकर बताइए"
  │    ├─ ASR → transcript (show live partials as decorative confidence)
  │    ├─ Parse → {gia_domain(10), activity_concept, nco_guess}
  │    ├─ If parse confidence < τ: clarify ONCE ("क्या आप सिलाई की बात कर रही हैं या पशुपालन की?")
  │    └─ Confirm parsed intent back to user ("समझ गया — सिलाई/टेलरिंग")
  ├─ RecommendationBuild (§6 algorithm; target <8s end-to-end):
  │    → 1 primary + 2 alternates, each = {QP code, course name, NSQF level, duration band,
  │      sector, why-this-fits (1 line), assistance facts (₹50k/50% project-cost loan support,
  │      women earmark if female), next step}
  ├─ RecommendationSpeak: TTS, chunked; then menu: [फिर सुनें] [विकल्प सुनें] [SMS भेजें] [खत्म]
  └─ SummaryPersist: session record → DB; SMS/WhatsApp text rendered (roadmap: real send)
[END]
```

Rules:
- Every turn ≤ 2 spoken sentences before yielding.
- Numbers are ALWAYS repeated digit-by-digit on request ("पचास हज़ार" → "पाँच-शून्य-शून्य-शून्य").
- Any ASR empty-result twice → offer keypad/menu mode automatically.
- Session resumable by phone number for 72h.

### 4.2 Officer dashboard (same app, `/dashboard`, role-gated)

- **Map/list toggle**: pins = captured sessions (block/district aggregate view; individual rows only for `officer`+ roles).
- **Top aspirations chart** (bar): count by GIA domain + top 20 activity concepts, filterable by district/gender/timebox.
- **Gap panel**: for selected district — top aspirations vs courses available in catalogue for that district's centres (seed table), flagged ⚠ when demand concept has no nearby QP supply.
- **Compliance chips** (auto-computed): % women captured (target ≥30% ✅mandate), % priority-income (≤₹2.5L self-reported), % consent-complete.
- **Export**: CSV of filtered sessions; "AAP annexure" XLSX grouping by GIA domain with counts — mimics what an Annual Action Plan needs.
- **Session drill-down**: transcript, parsed slots, recommended QPs + scores, consent record.

### 4.3 Crosswalk console (`admin` role)

- Table of `aspiration_phrase (hi/mr/te/en) → gia_domain → qp_codes[] → status(auto/reviewed)`.
- Reviewer can accept/fix/auto-batch suggestions; every change versioned (who/when).
- This is the "we built the missing join table" exhibit — keep it visible during judging.

### 4.4 Non-functional targets

| Metric | Target | Source of precedent |
|---|---|---|
| End-to-end voice turn (ASR→LLM→TTS audible) | ≤ 9 s p50, ≤ 15 s p95 | Farmer.Chat measured 9.05 s avg ✅ |
| Recommendation generation after intent confirm | ≤ 4 s (DB queries pre-indexed) | internal |
| ASR accuracy expectation | hi ~13-27% WER honest disclosure; mitigations active | Vistaar GramVaani 26.8% ✅ |
| Uptime during demo | 100% via mock-mode fallback | design |
| Accessibility | WCAG 2.2 AA checklist pass on dashboard; voice UI = audio-first by construction | see research §9 |
| Data minimization | No name required; phone optional; consent flag mandatory | DPDP posture |

---

## 5. Data plan

All ingestion happens ONCE during Phase 1; outputs are committed as seed snapshots so the finale build never touches a gov portal live.

### 5.1 Ingest (scripts in `pipelines/`, run in order)

| # | Script | Source | Output tables | Notes |
|---|---|---|---|---|
| 01 | `fetch_pmajay_courses.py` | POST pmajay.dosje.gov.in/front/reportajax (module_type=5&sector_id=all; CSRF from /course-list) | `courses(sector, sub_sector, course, sub_course, qp_code)` ~2,360 rows | Cache raw JSON to `seeds/pmajay_courses.json`; polite 1 req/s |
| 02 | `fetch_kaushalverse.py` | GET getAllQualApprovedFiles (71 pages) + getQualDetailsBasedOnVersionId per qual (throttled) | `qualifications(qp/nqr_code, name, nsqf_level, sector, min/max_hours, theory/prac/ojt/es_hours, credits, eligibility, progression, valid_till)` | Filter categoryOfQual == 'Qualification' (drop Standalone NOS/MC); expect ~half-level granularity — store nsqf_level NUMERIC(3,1) |
| 03 | `join_qp_level.py` | inner join courses.qp_code ↔ qualifications (match on code prefix + name fuzzy) | enriches `courses.nsqf_level, hours, credits` | Expect imperfect coverage; log unmatched %; fallback: infer level band from hours (200-600h STT ≈ L3-L4 heuristic, flagged) |
| 04 | `build_crosswalk.py` | curated YAML (`data/crosswalk/*.yaml`) + embedding index | `crosswalk(id, phrase, lang, gia_domain, qp_codes[], status)` v0≈150 entries | Hand-authored by team using illustrative-list 10 domains; each entry reviewed by a second member |
| 05 | `seed_district_supply.py` | synthetic-but-plausible district centre/course-availability table (clearly labelled SYNTHETIC in UI footer until real data via MoU) | `centre_supply(district, qp_code, seats, centre_name)` | Honesty label matters for judges; roadmap slide = replace via SIDH/NCS MoU |
| 06 | `load_guidelines_rag.py` | PM-AJAY May-2023 PDF + NSQF gazette + GIA chapter → chunk (≈500 tok, section-aware) → embed (multilingual-e5-base) | pgvector table `doc_chunks(chunk, embedding, source, page)` | Powers "scheme facts" answers; citations = doc+page |
| 07 | `seed_users_demo.py` | demo accounts: officer@demo / viewer@demo (password from env at bootstrap), 25 synthetic beneficiary sessions spread over 5 districts | users, sessions | Dashboard looks alive immediately |

### 5.2 Hand-built artifacts (the moat)

- `data/crosswalk/*.yaml` — aspiration↔QP mappings (v0 150; stretch 300). Seed generously around these GIA-domain clusters: tailoring/garment (ISB), beauty & wellness, electrician/plumbing (ISB), tractor operator/beekeeping/poultry/dairy/goatery (Agri/AH), food processing/papad-pickle units, handicrafts/handloom, mobile repair, healthcare attendant, IT/ITeS data-entry, retail.
- `data/prompts/dialogue.{hi,mr,te}.json` — every spoken prompt as data (not hardcoded strings) so language QA is parallelizable.
- `docs/crosswalk-method.md` — one-pager explaining method (embed → candidate → human-review) for the Research slide.

---

## 6. The recommendation algorithm

Deterministic core, generative shell — the LLM NEVER picks courses, only verbalizes tool output.

```
INPUT: profile{district, age_band, gender, edu_level, current_work}, intent{gia_domain, concept_text}

STEP 1 — Capability ceiling (NSQF-grounded):
  edu none/up-to-5th      → max_level = 2   (NSQF L1-L2 descriptors: basic literacy/numeracy ✅)
  5th-8th                 → max_level = 3
  8th-10th                → max_level = 4
  10th-12th               → max_level = 4.5
  grad+                   → max_level = 7
  (ceiling softens +1 if current_work indicates experience)

STEP 2 — Candidate QPs:
  C1 = crosswalk[concept_text].qp_codes                      (curated, exact)
  C2 = embed(concept_text) · top-k(40) over qp_description_embeddings  (semantic recall)
  candidates = dedupe(C1 ∪ C2) ∩ courses WHERE nsqf_level <= max_level
  IF len(candidates) < 3: relax max_level += 1, re-run, flag 'stretch'

STEP 3 — Eligibility filters:
  drop quals failing explicit entry criteria (min education) from qualifications table;
  gender-targeted courses (e.g., women-focus STT bands) BOOST not FILTER (≥30% women mandate)

STEP 4 — Score (weights in config, sum=1):
  score = 0.40·semantic_fit            (cosine, normalized)
        + 0.25·local_supply            (seats in district; 0 if none → penalty flag)
        + 0.15·level_fit               (distance from inferred starting level)
        + 0.10·placement_prior         (sector placement prior; seed constant 0.7 = guideline target)
        + 0.10·equity_boost            (women-focus course if female; RPL availability if experienced)

STEP 5 — Compose output object (STRICT schema):
  [{qp_code, name, nsqf_level, duration_band, hours, sector,
    why: template(highest-scoring factors),
    assistance: {loan_support:"up to ₹50,000 or 50% of project cost", women_note?},
    next_step}] × 3

STEP 6 — Verbalize: LLM receives ONLY the structured objects + dialogue history;
  system prompt forbids new facts; any number in output must appear in tool JSON (post-hoc check;
  violation → regenerate once → else fall back to canned template reading).
```

Fallback ladder (each fully functional alone): LLM+tools → template reader (no LLM) → static "top courses in your district" menu.

---

## 7. Dialogue design

- **Prompt style**: short, one clause per sentence; option-count ≤ 4 spoken at once; confirmations echo parsed slots ("आपका ज़िला लातूर, उम्र 18-30 — सही है?" single tap/speech "हाँ").
- **Barge-in**: mic stays open; any speech interrupts TTS (streaming TTS sentence-chunks make this cheap).
- **Confidence UX**: live caption pill shows transcript with a small dot-meter; below-threshold ASR auto-triggers the clarify-once flow.
- **Language mixing**: Hinglish/code-mixed input handled by prompting ASR language = primary but validating transcripts against all three language variants of crosswalk phrases.
- **Consent line** (recorded as data, played back on request): "आपकी जानकारी सिर्फ़ स्किल सलाह और योजना लिंकिंग के लिए रिकॉर्ड होगी। आप कभी भी 1514-शैली हेल्पलाइन से हटने के लिए 'बंद करो' कह सकते हैं।" — turns DPDP posture into product.
- **Tone**: respectful "आप", never "ग्राहक"; no jargon ("NSQF लेवल 3" spoken as "3 स्तर का कौशल कोर्स").

---

## 8. Build phases

### Phase 0 — Idea-round package (do immediately; ~2 evenings)

Deliverables (feeds directly off `research.md`):
1. **6-slide deck** per official template (PDF export only):
   - S1 Title: PS ID/title/theme/Software/TeamID/name
   - S2 Proposed Solution: compliance-loop framing + 3-step user journey graphic
   - S3 Technical Approach: ARCHITECTURE.md diagram verbatim + named stack bullets
   - S4 Feasibility & Viability: risk register §11 condensed (this slide wins credibility)
   - S5 Impact: absorption narrative + KPIs + women-quota alignment
   - S6 Research & References: top 12 links straight from Appendix B
2. **30-second demo video** of mock-mode voice loop (record early, protects against live-demo disaster later).
3. Portal submission before the 500-idea freeze (submit day-1 of window; max 2 PS allowed).

### Phase 1 — Pre-finale preparation sprint (2 weekends + evenings)

Goal: arrive at finale with **everything risky already proven**. Checklist:

- [ ] Repo scaffold per ARCHITECTURE.md §monorepo layout; CI green (lint+tests) on push
- [ ] Pipelines 01–03 executed; `seeds/` committed; join report written (`docs/ingest-report.md`)
- [ ] Crosswalk v0 (≥150 entries) authored & peer-reviewed
- [ ] Embeddings built (guidelines chunks + QP descriptions); retrieval smoke test notebook
- [ ] Voice spike: browser mic → Bhashini ASR (real keys) → text; text → Sarvam/Bhashini TTS → speaker. Measure latencies, write numbers into docs
- [ ] Mock-mode implemented FIRST-CLASS (`VOICE_PROVIDER=mock` env) with recorded fixtures
- [ ] Recommendation engine v1 + unit tests (capability ceiling, filters, scoring determinism)
- [ ] Auth flows working end-to-end (OTP-lite mock, officer login, RBAC)
- [ ] Dashboard skeleton with seeded synthetic sessions
- [ ] Docker-compose boots whole system on a clean laptop in ≤5 min (`make up`)
- [ ] Demo laptop imaged + backup USB + offline copies of all seeds/models

Exit criteria: a teammate can run `make up && make seed && open http://localhost:3000` and complete a full mock voice conversation.

### Phase 2 — Grand finale (hour-by-hour, assumes ~36h; compress proportionally if less)

| Window | Track A (backend×2) | Track B (voice/ML×1) | Track C (frontend×1) | Track D (dashboard/design×1) | Track E (PM/demo×1) |
|---|---|---|---|---|---|
| H0–2 | Kickoff; verify `make up` on all laptops; assign GitHub issues | Real-key sanity: Bhashini ASR/TTS live test | Wire dialogue state machine screens to API contract | Map component + theme tokens | Icebreaker; print runbook; set up timeboard |
| H2–8 | Sessions API + consent + RBAC hardening | Streaming loop: partials, barge-in, silence detect | Complete 5-slot profile flow w/ suggested chips | Top-aspirations bar + filters | Draft judge Q&A bank from research.md |
| H8–16 | Recommendation engine integration + guardrail post-check | Language router (LID) + DTMF tone handling stub | Free-speech capture screen + confidence pill | Gap panel + compliance chips | Rehearsal #1 (mock mode); log bugs |
| H16–24 | CSV/AAP export; audit-log view | IVR attempt (Exotel trial) OR WhatsApp webhook — pick ONE, timebox 4h | Summary screen, replay menu, retry loops | Polish icons/literacy UX pass (≤4 options/screen) | Rehearsal #2 WITH VOICE; measure timings |
| H24–30 | Bug triage; perf (indexes, connection pool) | Fallback ladder tests (kill network mid-demo drill) | Empty/error/loading states everywhere | Export UX + print sheet | Video backup recording of full demo |
| H30–34 | Freeze features; only critical fixes | Final latency tuning; fixture refresh | Final visual QA both themes | Dashboard storytelling data curated | Slide dry-run vs 6-slide rubric; timing ≤8 min |
| H34–36 | Tag release `finale-v1`; deploy to VPS + ngrok; smoke test from venue wifi | Same | Same | Same | Full dress rehearsal ×2; sleep rota for presenter |

Standing rules during finale: main branch protected; every merged PR runs tests; feature-freeze at H30 absolute; every demo path has a recorded-video twin.

### Phase 3 — Judge-proofing (continuous from H16)

- **Kill-a-service drills**: unplug internet / revoke keys / kill DB container mid-flow → system degrades to mock/template mode with a friendly line. Practice until boring.
- **Hostile Q&A bank** (PM maintains; answers sourced from research.md): "What about Bhojpuri?" (WER evidence + LID router + roadmap), "Why not just use the PMKVY portal?" (supply-side vs demand-side framing), "Data privacy?" (minimization + consent-as-feature + DPDP roadmap), "How is this different from Jugalbandi?" (domain grounding + compliance artifacts + officer loop), "Cost per beneficiary?" (₹<2/conversation math ✅), "What if ASR fails?" (demonstrate live fallback).
- Metrics placard printed: latency p50/p95 measured, WER expectations, coverage numbers (courses, QPs, crosswalk size).

---

## 9. Team split (6)

| Role | Owns | Backup |
|---|---|---|
| BE-1 (lead) | Repo/CI, sessions+auth+RBAC, deployment | BE-2 |
| BE-2 | Ingestion pipelines, seeds, recommendation engine | BE-1 |
| VOICE | Bhashini/Sarvam integration, streaming, LID, DTMF, fallback ladder | FE |
| FE | Beneficiary PWA (all screens), i18n strings, offline SW | DASH |
| DASH | Officer dashboard, exports, design system, accessibility pass | FE |
| PM | Slides, Q&A bank, rehearsals, timeboard, judge liaison, video | everyone |

---

## 10. Demo script (8 minutes, rehearsed)

1. **(60s)** Problem: quote Ch.3 §7.A.a.iv on screen + absorption number. "The law already demands this loop. Nobody built the front door."
2. **(90s)** LIVE: Priya persona on phone PWA — Hindi, free-speech aspiration (*"main silai ka kaam seekhna chahti hoon"*), watch parse-confirm-recommendation. Show the ₹50,000/50%-project-cost assistance fact spoken aloud.
3. **(60s)** Show crosswalk console: her phrase already mapped to QP codes with NSQF levels joined from Kaushalverse — "the missing join table, built and cited."
4. **(90s)** Officer dashboard: her session appears live; district gap panel; women-participation chip crossing 30%; CSV/AAP export click.
5. **(60s)** Resilience theater: turn wifi off mid-conversation → graceful template fallback → wifi on → continues. "Designed for villages, not conference wifi."
6. **(60s)** IVR clip (recorded): same brain reachable from a ₹1,000 feature phone; DTMF menu audible.
7. **(60s)** Compliance & scale: PoC-license honesty (Bhashini tiers), PMKVY routing post-DAKSH-merger, roadmap to SIDH/NCS MoUs.
8. **(60s)** Impact ask: pilot metric proposal with one district's Mission office; team intro.

Backup: 3-min video mirror of steps 2–6.

---

## 11. Risk register

| # | Risk (verified basis) | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Rural-telephony ASR ~27% WER best-case (GramVaani ✅) | Certain | Medium | Guided menus+suggestions, clarify-once, confirm-back, DTMF fallback, honest metrics placard |
| R2 | Bhashini keys throttled/rate-limited at venue (no published SLA ✅) | Medium | High | Mock mode + Sarvam secondary + Azure failover pattern (Jugalbandi precedent ✅) + pre-recorded fixtures |
| R3 | Bhashini PoC-only license | Certain | Low (SIH) | Demo under PoC terms; partnership-tier roadmap slide |
| R4 | pmajay endpoints change/unofficial (debug-leak observed ✅) | Medium | High | Seed snapshots committed; live fetch optional garnish |
| R5 | NQR→Kaushalverse migration churn (both live ✅) | Medium | Medium | Dual-source ingestion; store both IDs; nightly diff script |
| R6 | Half-level NSQF values break integer logic (✅ ~24% sample) | Certain | Medium | NUMERIC(3,1) column + floor() display + tests |
| R7 | Crosswalk quality (hand-built) | Medium | High | Peer-review protocol, review-status UI, versioning; show process to judges |
| R8 | Venue network dead | Medium | High | Full-offline mock rehearsal; laptop-hosted everything; USB backups |
| R9 | Team illness/burnout | Low | Medium | Pairing on every subsystem; runbook; role backups |
| R10 | Judges expect real govt data integration | Medium | Medium | Show verified-live endpoints working (catalogue JSON, dashboard feeds) + honest MoU roadmap |
| R11 | Scope creep in finale | High | High | Feature freeze H30; MVP list is contract; PM holds veto |
| R12 | LLM hallucinates scheme facts | Medium | High | Tool-output-only policy + post-hoc numeric check + template fallback |

---

## 12. Judging-strategy map (official nine criteria ✅ → our proof)

| Criterion (SIH 2026 wording) | Our evidence at judging |
|---|---|
| Novelty | First PS appearance ever (zero 2024 mentions ✅); missing-crosswalk contribution; compliance-loop framing |
| Complexity | Multi-source ingestion, half-level joins, multilingual voice, deterministic-core/generative-shell safety |
| Clarity/detail in format | 6-slide template followed exactly; diagrams over prose; this dossier as backing |
| Feasibility | Working MVP with real endpoints verified live; latency/WER numbers measured not claimed |
| Practicability | Runs on ₹35k laptop + free tiers; ₹<2/conversation cost math; mock-mode ops realism |
| Sustainability | Open data sources (NCVET/Kaushalverse), partner-tier path, MoU roadmap, crosswalk maintainable via console |
| Scale of impact | 28 States/UTs ✅; ≥10% skilling floor ✅; ≥30% women ✅; absorption-gap narrative ✅ |
| User experience | Field-evidence-driven UX (suggestions>free-form ✅, DTMF ✅); WCAG 2.2 AA pass; audio-first |
| Future work progression | Phased roadmap (§13) with named gates (licenses, MoUs, pilots) |

---

## 13. Post-SIH roadmap (slide + answer)

- **Q1 post-win**: Pilot MoU with one State Skill Development Mission / district Mission office; replace synthetic `centre_supply` with SIDH extract; Bhashini production tier application (Sahyogi).
- **Q2**: Telephony rollout (toll-free inbound, Exotel/BSNL SIP trunk + DLT registration); WhatsApp channel GA; Marathi+Telugu expansion beyond demo districts; officer training kit.
- **Q3**: SHG group-capture mode GA; outcome tracking loop (placement follow-up calls at 90 days — closes the 70%-placement monitoring need ✅); anonymized aspiration analytics published quarterly.
- **Year 2**: Additional languages pending model coverage (cite WER table honestly); kiosk hardware pilot at Common Service Centres (CSC); integration bid with pmajay.dosje.gov.in MIS via DoSJE.

---

## 14. Definition of done

A build is DONE when ALL hold:
- [ ] Fresh-machine `make up && make seed` → full mock voice conversation completable in ≤3 min without touching config
- [ ] With real Bhashini keys, same flow completes with measured p50 ≤ 9 s
- [ ] Every recommendation's fields provably originate from DB rows (spot-check script `scripts/verify_grounding.py` passes on 50 random sessions)
- [ ] Officer dashboard renders ≥25 seeded sessions, exports valid CSV/XLSX
- [ ] Auth: beneficiary OTP-lite + officer RBAC enforced (401/403 tests)
- [ ] `pytest` suite green; grounding, scoring-determinism, and RBAC covered
- [ ] Kill-a-service drill passes (network off → template mode; DB down → readable error + recovery)
- [ ] README quickstart accurate; `.env.example` documents every variable; no secrets in git
- [ ] 6-slide deck + 3-min video exported and linked from README
