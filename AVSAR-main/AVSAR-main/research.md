# research.md — AI-Driven Voice Assistant for Livelihood Mapping & NSQF-Aligned Skilling Recommendations for SC Communities under PM-AJAY GIA

> **SIH problem-statement research dossier.** Every load-bearing claim below went through a multi-agent research pipeline (5 search angles → 15 source fetches → 3-voter adversarial verification per claim). Claims that failed adversarial verification were **removed or corrected** — see Appendix A for exactly what was killed and why, because those traps are easy to fall into during judging Q&A.
>
> **Legend:** ✅ = survived 3/3 or 2/3 adversarial verification against the primary source. ⚠️ = single-source or partially verified. ❌ = refuted; do not cite.
>
> Compiled: 2026-08-26.

---

## Table of Contents

1. [Executive summary — what matters](#1-executive-summary)
2. [PM-AJAY and its Grant-in-Aid component](#2-pm-ajay-and-its-grant-in-aid-component)
3. [NSQF, NQR/Kaushalverse, QP-NOS and the NCO gap](#3-nsqf-nqrkaushalverse-qp-nos-and-the-nco-gap)
4. [Livelihood-mapping methodology & government practice](#4-livelihood-mapping-methodology--government-practice)
5. [Voice AI for low-literacy rural India — models, APIs, costs, accuracy](#5-voice-ai-for-low-literacy-rural-india)
6. [Prior art & UX evidence from deployed voice systems](#6-prior-art--ux-evidence)
7. [Integration surfaces & datasets you can actually hit today](#7-integration-surfaces--datasets)
8. [Legal & compliance surface (DPDP, Aadhaar, TRAI)](#8-legal--compliance-surface)
9. [Architecture patterns: latency, RAG, guardrails, offline, accessibility](#9-architecture-patterns)
10. [SIH reality: rules, rubric, prior winners](#10-sih-reality)
11. [The strategic synthesis — how to win this PS](#11-the-strategic-synthesis)

---

## 1. Executive summary

**The problem statement is secretly a compliance-automation task.** The PM-AJAY Grant-in-Aid guidelines *already legally mandate* the exact pipeline your assistant automates:

> "The Skill Gap Analysis report of National Skill Development Corporation (NSDC) shall be factored while proposing the skilling areas/job roles to be implemented in different States/Districts. The same are to be duly endorsed by relevant District Skilling Authority or authorized functionary of State Skill Development Mission, confirming that the proposals are relevant to the District/State, **in terms of aspiration of the target group and availability of job market**." ✅
> — PM-AJAY Guidelines (May 2023 Revised), Ch. 3, §7.A.a.iv — https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf

So the pitch writes itself: **today this aspiration→job-market→NSQF-QP mapping happens on paper through district officers; you are building the voice-first tool that does it in seconds, in the beneficiary's own language, for a population whose literacy makes existing portals unusable.**

Ten findings that should drive every design decision:

1. **NSQF alignment is a legal requirement of GIA skilling, not a nice-to-have** ✅ — all training partners must comply with NSQF + MSDE Common Norms (May 2023 guidelines, Ch. 3).
2. **At least 10% of SCA released each year must go to skill development** ✅ — a hard floor, so demand for course selection exists every year in all 28 States/UTs implementing GIA ✅.
3. **The PM-AJAY portal already exposes a machine-readable GIA course catalogue keyed to NSQF QP codes** ✅ — POST `https://pmajay.dosje.gov.in/front/reportajax` returns ~2,360 courses / ~1,893 unique QP codes with no login (verified live). But it has **no NSQF-level field**, so levels must be joined from NCVET's Kaushalverse API ✅.
4. **Kaushalverse (NCVET) has an open, unauthenticated JSON API** ✅ with full qualification detail payloads (hours split, credits, eligibility, progression paths) — but its `ncoCode` field is **empty in every sampled record** ✅. The aspiration→NCO-code→QP crosswalk must be built by you. This is the hardest data-engineering piece and also your moat.
5. **ASR on real rural telephony audio still fails ~1 word in 4 even with the best open Indic model** ✅ (IndicWhisper 26.8% WER on GramVaani rural-Hindi benchmark). Design for it: guided menus, confirmation loops, DTMF fallback. Field studies show **low-literacy users often prefer keypad input over speech** ✅ — voice-first ≠ speech-input-only.
6. **Bhashini's free self-served APIs are licensed for PoC only** ✅ — perfect for SIH, but production needs their paid partner tiers (Sahyogi / App Mitra / Udyat Mitra). Put this on the roadmap slide, not in the demo path.
7. **Budget under-utilisation is the ministry's own documented pain** ✅ — Actual 2024-25 spending was ₹736.28 cr vs ₹2,140 cr BE (~1/3); RE 2025-26 was cut 41.6% to ₹1,250 cr. A tool that speeds up beneficiary-level project formation speaks directly to absorption problems.
8. **PM-DAKSH was merged into PMKVY effective FY2026-27** ✅ — any recommendation engine must route trainees to MSDE/PMKVY infrastructure going forward; citing pre-merge PM-DAKSH as the destination will look stale to MoSJE judges.
9. **There is no direct precedent**: zero occurrences of "PM-AJAY", "NSQF", "Scheduled Caste" etc. across all 246 SIH 2024 problem statements ✅ — judges have no baseline solution in mind; you define the category.
10. **The SIH idea round is scored off a fixed 6-slide template** ✅ where one full slide is Feasibility (risks + mitigations) and another is Research & References — this research document feeds those slides directly.

---

## 2. PM-AJAY and its Grant-in-Aid component

### 2.1 What the scheme is

| Fact | Detail | Source |
|---|---|---|
| Full name | Pradhan Mantri Anusuchit Jaati Abhyuday Yojana | https://socialjustice.gov.in/schemes/104 |
| Type | Centrally Sponsored Scheme (Transfer to States/UTs), 100% centrally funded — States may add own funds but there is no matching share ✅ | May 2023 Guidelines |
| Formed by merger (2021-22) of | SCA-to-SCSP + PMAGY + BJRCY (exactly three schemes) ✅ | https://www.indiabudget.gov.in/doc/eb/sbe93.pdf |
| Umbrella | "Umbrella Scheme for Development of Scheduled Castes", Demand No. 93, DoSJE/MoSJE ✅ | sbe93.pdf |
| Stated objective #1 | "Reduce poverty of the SC communities by generation of additional employment opportunities through skill development" ✅ | May 2023 Guidelines / sbe93.pdf |
| SC share of population | 16.6% (Census 2011) ✅ | Guidelines |
| Official portal (MIS/plan-submission) | https://pmajay.dosje.gov.in ✅ | Guidelines ("Annual Action Plan … uploaded in online portal") |

⚠️ Note: MoSJE's master scheme index lists PM-AJAY under "Schemes for Social Empowerment"; one verification pass flagged that list position is alphabetical, not a policy classification — don't over-read taxonomy from the index page.

### 2.2 The three components and money ceilings ✅

| Component | Ceiling on allocated funds |
|---|---|
| Adarsh Gram (village gap-filling) | Up to 50%; ₹21 lakh per new village (₹20 lakh gap-filling + ₹1 lakh admin) |
| Administration, Monitoring & Evaluation | Up to 5% (1% at Centre, 4% to States proportional to central assistance released; funds centralized MIS software + TSG + PIUs at C/S/D levels) |
| Hostels (construction/repair not covered by States) | Up to 2%, released directly to implementing agencies by the Ministry |
| **Grants-in-aid for District/State projects** | **Balance funds** — allocated across States: 50% weightage to SC population + 50% weightage to State's SCSP-to-Annual-Plan weighted SC population |

GIA runs in **28 States/UTs**; excluded: Arunachal Pradesh, Nagaland, Meghalaya, Mizoram, A&N Islands, DNH, Daman & Diu, Ladakh, Lakshadweep.

Source (all): PM-AJAY Guidelines May 2023 — https://socialjustice.gov.in/writereaddata/UploadFile/36851753087331.pdf (byte-identical copy served at https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf).

### 2.3 GIA component mechanics — what the guidelines actually mandate ✅

These are the operative norms from the **May 2023 Revised guidelines** (the governing document, valid to 31 Dec 2030):

**Spending earmarks (per year, on grants released):**
- **≥ 10%** of Special Central Assistance → skill development programmes *(hard floor)*
- **≥ 15%** of total Grants → income-generating economic development schemes **exclusively for SC women** ⚠️ *(the Feb 2022 version said "up to 15%" — the 2023 revision changed a ceiling into a floor; quoting the old direction loses credibility)*
- **≤ 30%** → infrastructural development
- **≥ 30% women candidates** participation in skill development programmes

**Beneficiary eligibility & assistance norms:**
- **No fixed income limit.** Priority to SC families/persons with annual income **≤ ₹2.50 lakh**. SC-majority SHGs are eligible entities. ⚠️❌ (Popular summaries say "BPL only" — that language survives only on a frozen pre-merger legacy page of the portal describing the old SCA-to-SCSP scheme; see Appendix A.)
- Comprehensive Livelihood Projects bundle skill development + related infrastructure + financial assistance toward **beneficiary loans** for asset acquisition/creation needed for livelihood generation.
- Assistance toward such loans: **up to ₹50,000 or 50% of project cost, whichever is less, per beneficiary/household** ⚠️ *(Feb 2022 said "50% of asset cost"; May 2023 says "project cost" — quote the 2023 wording)*.
- **No standalone individual asset distribution** — assets must sit inside an appraised bundled livelihood project (ensured by the Project Appraisal Committee).
- Every training programme must include **financial literacy + preparation of a basic bank-linkable project proposal**.

**Skilling structure (four duration bands pegged to NOS/QPs):**
| Band | Duration |
|---|---|
| RPL / up-skilling | 32–80 hours, up to 1 month |
| Short-term courses (focus on women & self-employment) | 200–600 hours, up to 5 months, "or as stipulated in National Occupational Standards (NOS) and Qualification Packs (QPs)" |
| EDP (Entrepreneurship Dev. Programme) | ~80 hours (10 days) |
| Long-term | 6 months–1 year; curriculum per NSQF/NCVT/AICTE/MSME certifications |

- **All Training Partners must ensure NSQF compliance + MSDE Common Norms** (infrastructure, assessment/certification, placement, monitoring, TP eligibility, ToT).
- Job-role selection must factor **NSDC Skill Gap Analysis reports**, endorsed by District Skilling Authority / State Skill Development Mission on two explicit criteria: **aspiration of target group** + **availability of job market**.
- Non-duplication clause: States must ensure beneficiaries/components not already covered under PM-DAKSH are the ones considered (i.e., GIA skilling complements, not duplicates).
- Outcome target: **70% placement** in wage/self-employment for short-term, EDP and long-term training.
- Annual Action Plans prepared per local requirements and uploaded on pmajay.dosje.gov.in.

### 2.4 The canonical livelihood taxonomy (your ontology, handed to you)

The portal publishes the illustrative GIA project list at **https://pmajay.dosje.gov.in/illustrative-list** — exactly 10 domains:

1. Agriculture & Soil Conservation
2. Horticulture
3. Minor Irrigation
4. Animal Husbandry
5. Fisheries
6. Food Processing
7. Forestry / Ecology & Environment
8. Handicrafts & Handlooms
9. **Industry, Service & Business (ISB)** — 21 sub-items including manufacturing units, IT/ITeS services, Media & Entertainment, Healthcare, Banking & Financial Services, Beauty parlour, Plumbing, Auto repair, Bakery, and "other sustainable units as per local needs"
10. Cooperatives

This is the controlled vocabulary your recommendation engine should output into (it maps near-directly onto Sector Skill Council sectors), and it doubles as your dialogue-system slot list when parsing spoken aspirations like *"kapda silna chahti hoon"* → ISB/garmenting.

(The identical 10-domain taxonomy appears as Annexure-I of the guidelines PDF.)

### 2.5 Budget reality — the implementation-gap story ✅

From Notes on Demands for Grants, Demand No. 93 (Union Budget documents, primary source):

| Year | BE | RE | Actual |
|---|---|---|---|
| 2024-25 | ₹2,140.00 cr | ₹1,890.00 cr* | **₹736.28 cr** (~34% of BE) |
| 2025-26 | ₹2,140.00 cr | **₹1,250.00 cr** (−41.6%) | — |
| 2026-27 | **₹2,140.00 cr** | — | — |

\* RE 2024-25 figure per budget-at-a-glance tables; the verified headline numbers are: BE 2026-27 = BE 2025-26 = ₹2,140 cr; RE 2025-26 cut to ₹1,250 cr; Actual 2024-25 = ₹736.28 cr.

Context ✅: DoSJE Demand No. 93 net total 2026-27 = ₹13,687.59 cr; SC umbrella scheme = ₹9,627.96 cr; PM-AJAY ≈ 22.2% of the SC umbrella, second-largest line after Post-Matric Scholarships for SCs (₹6,360 cr).

**Why this matters for your pitch:** chronic under-absorption is precisely what a beneficiary-facing tool that accelerates aspiration capture → project formulation → AAP upload claims to attack. It converts your product from "nice chatbot" to "absorption-acceleration infrastructure".

The Union Budget does **not** disaggregate PM-AJAY into its three components ✅ (unlike SHREYAS/SMILE/YASASVI which have sub-heads) — so component-wise GIA outlays must come from MoSJE annual reports, the portal, or Parliamentary Q&A. Don't invent a "GIA budget" number on stage.

### 2.6 Sibling schemes you must de-conflict against ✅

| Scheme | Role | Status |
|---|---|---|
| **PM-DAKSH** (pmdaksh.dosje.gov.in) | Dedicated skilling for SCs/OBCs/DNTs/Safai Karamcharis | **Merged into PMKVY w.e.f. FY2026-27** ✅ — BE 2026-27 nil (BE 2025-26 was ₹130 cr; actual 2024-25 ₹79.40 cr). Route recommendations to PMKVY/MSDE infrastructure going forward. |
| Credit Enhancement Guarantee Scheme for SCs | IFCI-run credit guarantee | ifcicegssc.in — separate credit rail |
| NSFDC / SCDC assistance | Term loans via corporations | nsfdc.nic.in |
| NSQF equity hook | NSQC must prescribe guidelines ensuring training providers address special needs of disadvantaged sections **including Scheduled Castes** ✅ | NSQF notification, 27 Dec 2013 |

A sophisticated answer to "how is this different from PM-DAKSH/PMKVY portals?" is now available: *those are supply-side training-delivery systems; this PS is the demand-side aspiration-capture and mapping layer that the GIA guidelines require but nobody has built.*

---

## 3. NSQF, NQR/Kaushalverse, QP-NOS and the NCO gap

### 3.1 NSQF essentials (from the 27 Dec 2013 gazette notification) ✅

Source: https://ncvet.gov.in/wp-content/uploads/2022/08/NSQF.pdf

- **Exactly 10 levels**; Level 1 lowest complexity, Level 10 highest. Defined by learning outcomes in **five descriptor domains**: process, professional knowledge, professional skill, core skill, responsibility.
- **Levels are NOT tied to years of study** — competence demands only. (Quote this when justifying level inference from a spoken profile.)
- **Level 1 descriptor (verbatim highlights)** ✅: repetitive processes requiring no previous practice; core skill = reading/writing, addition/subtraction, personal financing; responsibility = none, works under continuous instruction. Level 2 adds receiving/transmitting written/oral messages + basic arithmetic; Levels 3–4 add basic arithmetic/algebraic principles and personal banking. **This is your concrete floor for recommending entry-level QPs to first-time, low-literacy trainees.**
- **Compliance timetable (legal basis for "must be NSQF-aligned")**: from 3rd anniversary (Dec 2016) no government funding for non-compliant programmes; from 5th anniversary (Dec 2018) NSQF compliance mandatory for **all** training/educational programmes.
- Notified 27 Dec 2013 by **Ministry of Finance (DEA)** pursuant to CCSkillD decision of 19 Dec 2013; superseded MHRD's NVEQF. Institutions named then (NSDA/NSQC authoring/approving) partly superseded by **NCVET** since 2018.
- QP-NOS taxonomy: NOS = measurable performance outcomes for one task; the set of NOSs for a job role = its **Qualification Pack**; authored by Sector Skill Councils, approved/notified by NSQC.

### 3.2 Where machine-readable qualifications actually live

Two registers exist right now; cross-check both:

| | NQR (legacy) | Kaushalverse (successor-in-progress) |
|---|---|---|
| URL | https://nqr.gov.in | https://kaushalverse.ncvet.gov.in/homepage/repository |
| Status | Live, self-labelled **"Beta Version"**, banner: "National Qualification registry is migrating on kaushalverse…" ✅ | Live; site config self-reports `"environment": "Dev"` ⚠️ |
| Access | **No public REST API** — server-rendered HTML at `/qualifications/{id}` (+ CSRF-protected POST endpoints); robots.txt allows crawling ✅ | **Open unauthenticated JSON API** ✅ |
| Records | Structured qualification pages: NOS grid (code, mandatory/optional, hours, credits, per-NOS level), NSQC approval no., approval date + 3-year validity, sector, notional hours min/max, Theory/Practical/Employability/OJT split, entry criteria, progression pathway, awarding body, downloadable Qualification File PDFs ✅ | 1,414 approved files ✅ spanning three categories — **Qualification / Standalone NOS / Standalone MC (model curriculum)** — filter them apart ✅ |
| Codes | `NQR Code` format `QG-{level}-{sector}-{serial}-{year}-V{v}-{body}` e.g. `QG-2.5-ET-01489-2023-V1-MSRVVP` ✅ (but NOT universal — some records lack it ❌→treat as partial) | Same lineage (`nqrCode` stamped per record); migration endpoints `/nqrMapping/*` present |
| NSQF levels | Half-level granularity: 1–10 incl. 2.5/3.5/4.5/5.5 ✅ | Same ✅ — a 136-record sample found levels 2…6 with ~24% at half-levels; **any integer-only logic mis-handles ~¼ of the corpus** |
| Occupation/NCO | "Proposed Occupation" is free text, frequently "N/A"; **no NCO codes** ✅ | Has an `ncoCode` field — **null in every sampled record** ✅ |

**Kaushalverse API quick reference** ✅ (verified live with plain curl, 2026-08-25):
```
Config:      GET https://kaushalverse.ncvet.gov.in/assets/config/env.json
List:        GET  /digigov/homepage/getAllQualApprovedFiles?pageNumber=N     (20/page, ~71 pages)
Detail:      GET  /digigov/homepage/getQualDetailsBasedOnVersionId?versionId=N
Award bodies:GET  /digigov/homepage/getAllRecognisedAB                       (106 bodies; only ~17 named "Sector Skill")
Search:      POST /digigov/homepage/filterQualForms?pageNumber=N   body {"search":"..."}
```

Detail payload includes everything a recommender needs without PDF parsing ✅ — worked example (versionId 71685): "Metro Rail Maintainer", nqrCode `QG-03-RL-05350-2026-V1-DA`, NSQF L3, Railways/O&M, awarding body DMRC Academy, 600–2580 hours, 20 credits, theory/practical/OJT/employability split 90/150/0/30, vertical progression "Senior Metro Rail Maintainer (L4)", valid till 2029-07-21.

### 3.3 The NCO-2015 gap — your hardest data problem, stated honestly ✅

The chain the PS implies is: **spoken aspiration → occupation concept → NCO-2015 code → NSQF-aligned QP → nearest training provider.** Neither register publishes usable NCO codes ✅✅. NCS's public pages expose no NCO taxonomy either (nine broad sectors only) ✅. So you must build the crosswalk yourself from:
- DGE's published NCO-2015 volumes (manual download),
- SSC job-role descriptions (via QP files),
- an embedding-based semantic match (multilingual text embeddings over aspiration ↔ occupation/QP descriptions).

Frame this as a contribution, not an apology: "we built the missing aspiration↔NCO↔QP crosswalk as a curated artifact."

### 3.4 Course catalogue inside the PM-AJAY portal itself ✅

Verified live (2026-08-25):
- `POST https://pmajay.dosje.gov.in/front/reportajax` with body `module_type=5&sector_id=all`, CSRF token + session cookie obtained from GET `/course-list`.
- Returns ~**2,360 rows** / ~**1,893 unique QP codes** (computed values, not official counts) across 38 SSC code prefixes and 48 selectable sectors. Columns: Sector / Sub Sector / Course / Sub Course / Sub Course Code (e.g., `AGR/Q5301 Beekeeper`, `AGR/Q1101 Tractor Operator`).
- **No NSQF level field anywhere in the response** (the literal string "NSQF" never occurs) → join levels from Kaushalverse via QP code.
- The portal's own "Find Course" menu item links out to https://nsdcindia.org/qp-nos-results — i.e., the government's own UI treats NSDC as the QP reference.

⚠️ Treat these endpoints as unofficial/unstable: the same app leaks a Laravel stack trace (`app/Http/Controllers/front/UserController.php:2623`) on malformed params — debug mode is enabled in production. Scrape politely, cache aggressively, ship seed snapshots.

---

## 4. Livelihood-mapping methodology & government practice

Load-bearing anchors carried from the core research:
- GIA's own pipeline (aspiration + job market endorsement, §2.3) is a district-level livelihood-mapping exercise done manually today ✅.
- Adarsh Gram chapter contains a **scored 10-domain village gap-analysis framework** (indicators scored 0/1/2, e.g. Aadhaar coverage >98% = 2 points) ⚠️ — evidence the ministry already thinks in structured indicator matrices you can mirror for household profiles.
- Avaaj Otalo / Farmer.Chat field results (§6) define what "capture aspirations by voice" can and cannot look like in practice.

### 4.1 The machinery that already exists: DAY-NRLM's livelihood data stack ✅

Most important supplemental discovery: **government already runs a household-level livelihood-data pipeline for SHG women** — AVSAR is its missing front door, not a new concept to defend.

- **Federation structure** (aajeevika.gov.in/work-structure/community-institutional): SHGs (10–20 women; 5–20 for special SHGs of PwDs/elderly) → Village Organisations / Primary Level Federations (usually 5–20 SHGs, one habitation/village) → Cluster Level Federations (usually 5–30 PrLFs), staffed by Community Resource Persons drawn from SHG graduates. A World Bank institution-building report confirms the tiering and state variants (Tamil Nadu: Panchayat Level Federations; Odisha: GP Level Federations).
- **Digital Aajeevika Register (DAR)** (lakhpatididi.gov.in/digital-ajeevika-register): maintained at the **VO level**, updated **every six months** after harvest/business cycles, capturing household income across **seven categories** (agriculture & allied; enterprise; salary/honorarium; wage; commissions; remittances; other). Data entry is done by community cadres — **Livelihood e-CRPs / Data-entry Sakhis** — under District MIS/Livelihoods-manager supervision; self-declared LoKOS data is verified through CRP → Block Programme Manager → District Programme Manager before DAR entry.
- **Scale + official evaluation** (Lok Sabha annexure AS123, direct download): **3.46 crore Lakhpati Didis as of 31 Mar 2026** against a 6-crore target (Maharashtra alone: 51.59 lakh potential identified, 49.62 lakh verified); DAY-NRLM Evaluation 2024 found ~10% household income uplift overall and 12–33% in mature CLFs.
- **Design implication:** the DAR's seven income categories + VO/e-CRP workflow is the closest existing schema to your beneficiary profile. Position AVSAR as *complementing* DAR (voice aspiration capture → NSQF recommendation), never duplicating LoKOS — this pre-answers the judge question "why not just extend the existing MIS?"

### 4.2 Participatory targeting methodology (PIP-PPA + PRA) ✅

- **PIP-PPA** (Participatory Identification of Poor – Participatory Poverty Assessment/Tracking) is NRLM's official targeting method, owned/facilitated by Village Organisations: Round 1 (during CRP mobilization) maps households on a village social map with poverty levels; Round 2 (within 3 months of VO formation) generates **~15 poverty/vulnerability indicators** (SECC deprivations + state/local additions), assesses each household via PIP cards, **validates in the Gram Sabha**, and produces Vulnerability Reduction and Convergence Plans (DAY-NRLM Comprehensive Document, Aug 2023 — 4 MB PDF, direct download).
- Operational PRA toolkit, fetchable primary texts: NIRDPR NRLM handbook Module IV (3-day PIP module: transect walk, social mapping, wellbeing categorization with community-agreed poor/middle/non-poor indicators, FGDs, Gram Sabha approval); NIRDPR PRA training material (transect, wealth ranking, pair-wise/preference ranking, seasonality, Venn diagrams); FAO guides listing **19 tools** incl. gender-separated resource maps and seasonal calendars by gender/wealth group.
- MSDE's **District Skill Toolkit** under SANKALP hands District Skill Committees four components: indicator sets to quantify gaps, documentation/gap-analysis templates (developed with 130 districts across 6 states, validated by Mahatma Gandhi National Fellowship fellows in 75 districts), a best-practice library, and district agrarian/industrial dashboards.

### 4.3 District demand-side evidence: what actually exists to ingest ⚠️

| Source | Granularity | Access reality |
|---|---|---|
| **NSDC District Wise Skill Gap Studies** | district × sector × skill-band (Highly/Semi/Minimally skilled) — **not job-role/QP level** | Direct PDF download verified, no login: `stag-api.nsdcindia.org/system/files/2025-08/District Wise Skill Gap Study of <State>, 2012-17, 2017-22.pdf` (Rajasthan 28 MB, Gujarat 7.4 MB, Maharashtra 12.3 MB, UP → HTTP 200; Odisha → 404). Partial coverage, **no index/API**, catalog pages JS-rendered; legacy file paths now return HTML; skillsip.nsdcindia.org returned 504 |
| **SANKALP District Skill Development Plans** | district economic profile, workforce characteristics, employer demand, migration patterns, growth sectors | **746 DSDPs + 28 SSDPs submitted FY 2024-25** (parliament annexure, direct download); the plans themselves are not bulk-downloadable |
| Labour Bureau QES/AQEES | establishment employment by sector | ~12,038 establishments (10+ workers, 9 non-farm sectors); QES datasets on data.gov.in with Catalog API ✅; occupation-wages DB (base 2016) |
| State systems (Kerala EMI, Odisha SJIS, K-DISC DWMS) | Employment Market Information (ER-I quarterly / ER-II biennial under the 1959 Act); placement dashboards | Public portals, **no open APIs** ⚠️ |
| **NCS open data** | — | **Zero**: its data.gov.in catalog entry lists no datasets; dge.gov.in states web services exist only to inter-link state exchanges with NCS ✅ |

⚠️ Every demand-side source is either years stale or aggregated above QP level — which is exactly why the guidelines make district endorsement a manual step. Honest framing for slides: AVSAR ingests what exists (skill-gap PDFs, DSDP summaries) and makes the *aspiration side* live for the first time.

### 4.4 Agro-ecological livelihood-option methods (allied-activity domains) ✅

- **ICAR-CRIDA Agriculture Contingency Plans for all 650 districts** — Part I district agro profile (soils, rainfall, land use, cropping systems, livestock/fisheries); Part II weather-contingency strategies — per-district PDFs at predictable URLs (`icar-crida.res.in/CP/<State>/<District>.pdf`). The most programmatically accessible agro dataset found.
- TIFAC–IRMA demonstrates the full identification method: FAO-IIASA Agro-Ecological Zones crop suitability + Fuzzy Cognitive Mapping for asset-sensitivity/vulnerability, with Gujarat district case studies (11 MB report downloadable from IIASA repository).
- MKSP (DAY-NRLM's agri sub-scheme): four themes — Sustainable Agriculture, NTFP, Livestock, Fisheries — with non-negotiables (local agro-ecological suitability, low-cost sustainable practices, biodiversity, climate resilience, drudgery reduction, priority to landless/small/marginal women farmers); DPR templates downloadable.
- NABARD LEDP identifies SHG-cluster livelihoods (clusters of 15–30 SHGs in contiguous villages with similar activities, batches of 25–30, two credit cycles of handholding): ~3 lakh members supported via 2,449 LEDPs, ₹128.41 cr grant, as of 31 Mar 2024. JIVA (2022) anchors natural farming in agro-ecological zoning (25 projects, 11 states, five zones).

### 4.5 Synthesis for AVSAR

Your aspiration→recommendation loop joins three existing government artifacts: **PIP-PPA vulnerability indicators** (who needs what), **DAR income categories** (what households already earn from), and **district skill-gap/DSDP evidence** (what the local market absorbs). No system has ever joined these to the NSQF catalogue — that join table is the product (§11, play #2).

---

## 5. Voice AI for low-literacy rural India

### 5.1 The ASR accuracy picture (numbers you can defend on stage)

**Benchmark 1 — Vistaar / IndicWhisper** (AI4Bharat, INTERSPEECH 2023 work; MIT-licensed incl. fine-tuned models) ✅:
- Vistaar = 59 benchmarks/datasets; >10,700 hrs labelled training audio across 12 languages; IndicWhisper best WER on 39/59.
- Hindi average WER: **IndicWhisper 13.6%** vs Google STT 23.9%, Azure 20.0%, Nvidia-large 18.6%, IndicWav2vec 21.0%.
- **GramVaani benchmark (spontaneous, telephone-quality rural Hindi — the closest proxy to your users): IndicWhisper 26.8%, Google STT 59.9%, everything else ≥41%.** Even best-in-class mistranscribes ~1 in 4 words on real rural telephony audio.
- Per-language average WER varies >3×: hi 13.6, mr 18.2, kn 18.3, ur 19.4, bn 20.1, pa 20.5, gu 22.8, ta 25.3, or 27.4, te 28.8, ml 32.3, sa 48.0. **No Bhojpuri/Maithili/Chhattisgarhi/Santhali coverage** — dialect reality for SC communities in the Hindi belt is unserved by this generation of models.
- Per-language checkpoints are direct-download ZIPs (self-hostable, zero marginal cost, offline-capable) — but deployment is per-language (12 separate models; you need language ID in front).
- ⚠️ Caveat: numbers are early/mid-2023 vintage (predate Whisper large-v3, IndicConformer, Sarvam ASR, current Bhashini models) — treat vendor comparisons as directional.

**Benchmark 2 — IndicVoices / IndicASR** (AI4Bharat, arXiv 2403.01926, Mar 2024) ✅:
- Dataset: **7,348 hours, 16,237 speakers, 145 districts, 22 Eighth-Schedule languages; 91% spontaneous** (74% extempore + 17% conversational), narrow-band telephony-grade recordings included, quota-sampled for exactly your demographic (≥15% per education bracket incl. "no schooling"; ≥10% blue-collar/unemployed; balanced urban-rural; noisy environments).
- **IndicASR (130M-param conformer, CC BY 4.0) beats every commercial/open multilingual system on all supported languages** — WER: Hindi **15.0** (vs Whisper 34.0, Google USM 20.5, Azure 27.2, Meta MMS 38.9), Marathi **18.2** (Whisper 95.2!), Telugu **26.8** (Whisper 151.9).
- Whisper-class models are effectively unusable (>90% WER) on spontaneous Marathi/Telugu. If you demo with Whisper, expect failure; use Indic ASR models or Bhashini pipelines.
- Lineage note: funded by MeitY/Bhashini mission (IIT Madras = Data Management Unit), collected on an extension of **Karya** — the whole stack is ethically-sourced Indian public goods.

**Kathbath / IndicSUPERB** (arXiv 2208.11761) ✅: 1,684 hrs labelled, 12 languages, 1,218 contributors across 203 districts; benchmarks for 6 tasks (ASR, SV, SI, LID, QbE, keyword spotting). Use keyword spotting + LID as your dialect/language router justification.

### 5.2 Bhashini / ULCA — the government-sanctioned integration path ✅

Primary docs: https://bhashini.gitbook.io/bhashini-apis

- **Self-service onboarding**: register at https://bhashini.gov.in/ulca/user/register# → email auth → login → generate keys at https://bhashini.gov.in/ulca/profile. No nationality/entity-type/government-affiliation gate. Hard cap: **5 API keys per integrator**.
- Auth = **API key + User ID together** (User ID required specifically for the Pipeline Config call).
- Call flow: Pipeline Search (optional) → **Pipeline Config (mandatory)** → **Pipeline Compute (mandatory)**.
  - Config endpoint is FIXED: `POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline` with headers `userID` + `ulcaApiKey`.
  - Inference endpoint is **NOT fixed**: read `pipelineInferenceAPIEndPoint.callbackUrl` from config response; auth header name AND value come from `inferenceApiKey.name` / `.value`. **Hardcoding either breaks** — a classic integration bug worth mentioning in your technical-approach slide.
- One call can chain tasks: `[ASR]`, `[NMT]`, `[TTS]`, `[ASR+NMT]`, `[NMT+TTS]`, `[ASR+NMT+TTS]` — order matters. Model explorer: https://bhashini.gov.in/ulca/model/explore-models. Language codes ISO-639 (hi, en, …).
- **License: PoC only.** Production or end-user charging requires Bhashini's paid plans (tiers: Sahyogi / App Mitra / Udyat Mitra). No published rate limits/pricing on the onboarding docs — anything about quotas beyond the 5-key cap is unverifiable from official sources ✅.
- Reliability signal from the field: OpenNyAI's Jugalbandi ships Bhashini as default speech layer **with automatic Azure failover** ✅ — architect yours the same way.

### 5.3 Commercial alternative pricing — Sarvam AI ✅

(https://docs.sarvam.ai/api/getting-started/pricing.md — retrieved Aug 2026)

| Service | Price |
|---|---|
| Speech-to-Text | ₹30/hour (billed per second, rounded up per request) |
| STT + diarization | ₹45/hour |
| Speech-to-Text **& Translate** | ₹30/hour — translated text costs nothing extra |
| TTS Bulbul v2 / v3 | ₹15 / ₹30 per 10K chars (v3 labelled beta pricing) |
| Translate / Transliterate | ₹20/10K chars; Language ID ₹3.5/10K chars |
| Rate limits (account-wide, all APIs) | Starter 60 req/min · Pro 200 · Business 1,000 · Enterprise custom |
| Free tier | ₹100 signup credits — enough for a hackathon demo, not a pilot |

Back-of-envelope for a finale demo: a 2-minute conversation ≈ 2 min STT (₹1) + ~600 chars TTS v2 (₹0.9) + trivial translation ≈ **under ₹2/conversation**. Cost is a non-issue for demos; rate limits (60 rpm Starter) are the real constraint — batch/precompute canned prompts.

### 5.4 TTS options

- Bhashini TTS pipelines (ULCA) — free PoC keys ✅.
- Sarvam Bulbul v2/v3 — priced above ✅.
- AI4Bharat Indic TTS models (open weights) for self-hosted/offline paths — see AI4Bharat model releases; pair with per-language ASR checkpoints for a fully offline kiosk mode.
- ⚠️ Piper/Coqui have weak Indic coverage; don't bet the demo on them.

---

## 6. Prior art & UX evidence

### 6.1 Farmer.Chat (Digital Green + Microsoft Research India) — closest living prior art ✅

arXiv 2409.08916 (Sept 2024). Deployed in Kenya, India, Ethiopia, Nigeria; **15,000+ farmers, 300,000+ queries**. Hindi, Odia, Telugu (+ Swahili, Amharic, Hausa, English); handles dialects incl. Bhojpuri; 40+ value-chain crops.

Production telemetry — your realistic performance targets:
- Avg end-to-end response **9.05 s** (reranking 3.15 s, generation 2.71 s); 68% of answers in 7.5–12.5 s.
- **~75% of user questions successfully answered**; RAGAS context precision **71%**; high faithfulness ~80%; high relevance only **67%**.
- **66% of failures were out-of-content** (knowledge-base gaps), not retrieval/reasoning failures → invest in corpus breadth before cleverness.
- Architecture: voice→text→LLM→audio back; ASR/MT layer deliberately swappable (Google Translate/Whisper/equiv.); **better results translating query to English, reasoning in English, back-translating** than native-language reasoning ✅ — steal this pattern for Indic LLM handling.
- UX finding: low-digital-literacy users **struggled to phrase questions**; **35% power users generated ~80% of queries**; **pre-generated suggestion buttons drove >45% of interactions** ✅ → design voice menus + suggested follow-ups, not open-ended free speech.

### 6.2 Jugalbandi Manager (OpenNyAI) — the reusable open-source base ✅

github.com/OpenNyAI/Jugalbandi-Manager — Apache-2.0, channel-agnostic (WhatsApp/web; **no telephony channel demonstrated**), text+voice any language, **Bhashini default with Azure failover**, service-oriented repo (`api/channel/db/flow/indexer/retriever/language/jb-manager-bot`), Docker Compose + Alembic migrations, Azure deploy path.
Maturity caveat ✅: 41 stars / 43 forks / empty Releases at fetch time — cite as "reference architecture", not "proven platform". Best use: mine its `retriever/indexer` + `language` service split for your architecture diagram.

### 6.3 Avaaj Otalo (Stanford/IBM CGNet-era, CHI 2010) — the canonical field study ✅

doi.org/10.1145/1753326.1753434 — 51 farmers, 7-month Gujarat deployment:
- **Users preferred numeric (DTMF) input over speech**; menu navigation learned readily.
- For all 51 users, first-ever participation in ANY online community → phone voice UI is a genuine digital on-ramp.
- Most popular feature = asynchronous **Q&A forum**, not broadcast.
- Users want BOTH institutional authority AND peer discussion; moderation emerged as necessary → your gov-advice bot needs an authority/verification layer and, eventually, community features.

### 6.4 Other landscape entries (context; verify details before citing specifics)

- **CGNet Swara** (Shukla et al., CHI 2012, doi.org/10.1145/2160673.2160695) — voice forum for citizen journalism on feature phones; proven Gondi/Hindi operation at tribal-India scale.
- **Gram Vaani / Mobile Vaani** — IVR social media network; the GramVaani dataset itself is the rural-telephony ASR benchmark (§5.1).
- **Karya** — ethical-data crowdsourcing platform (used for IndicVoices collection); potential partner for future data collection, not a runtime dependency.
- **MyScheme.gov.in / UMANG** — text-first scheme discovery; neither solves voice nor aspiration mapping; cite as the status quo your PS replaces for non-literate users.
- **Kisan e-Mitra** — PM-Kisan chatbot (text/WhatsApp-first). Analogous ministry bot; shows MoSJE-family appetite for conversational interfaces.
- ⚠️ Items in this subsection were scoped but not deep-fetched; do a 15-minute check before putting specific stats on slides.

---

## 7. Integration surfaces & datasets

### 7.1 Confirmed-live, machine-accessible ✅

| Surface | Access method | What you get |
|---|---|---|
| **PM-AJAY GIA course catalogue** | POST `/front/reportajax` (CSRF+cookie from `/course-list`) | ~1,893 QP-coded courses × 48 sectors (§3.4) |
| **PM-AJAY dashboard JSONs** | Unauthenticated GET: `/homeGIABeneficiary`, `/homeGIAIntervention`, `/homeGIAFy/{fy}`, `/home/{fy}`, `/homeHostelFy/{fy}` | Five-bucket intervention classification (income generation / skill dev / infrastructure / hybrid / tutoring); FY2024-25: **137,529 skill-dev beneficiaries, 221,857 income-gen, 313,643 infra**; heavy reporting lag visible (FY2025-26 skill=5,500; FY2026-27=0) |
| **Kaushalverse JSON API** | Plain curl, no auth (§3.2) | 1,414 approved quals + full detail payloads |
| **NQR HTML** | Server-rendered pages, robots.txt allows | Cross-check register while migration completes |
| **Bhashini ULCA APIs** | Self-service keys (PoC license) | ASR/NMT/TTS chains (§5.2) |

⚠️ All pmajay.dosje.gov.in endpoints are undocumented/unofficial (Laravel debug-mode leak observed) — cache seed data; never hard-depend at finale.

### 7.2 Human-accessible only (mock/adapter in demo; roadmap for real)

- **NCS** (ncs.gov.in) ✅: **no public developer API whatsoever** (no /developers section; "NCS Meta Data" is a PDF). Skilling discovery routes to SIDH via `/sidh-course`. Operated by DGE/MoL&E — a **cross-ministry** dependency for PM-AJAY (MoSJE). Existing last-mile handoff assets worth naming in your impact slide: Find Counsellor, Model Career Centres list, NCSC-DA/VRC centres (da.ncs.gov.in), Employment Exchange (eex.ncs.gov.in), helpline **1514**, mobile app. Nine broad sectors exposed publicly; no NCO codes.
- **SIDH** (skillindiadigital.gov.in) — partially resolved below: open `/sectors`+`/jobs` gateway confirmed; course-listing route still undiscovered.
- **NSDC qp-nos-results** (nsdcindia.org/qp-nos-results) — referenced by the PM-AJAY portal itself as the QP authority ⚠️.

**Supplemental verification results (tested live 26 Aug 2026):**

- **SIDH resolved halfway** ✅: an open, unauthenticated gateway exists at `https://api-fe.skillindiadigital.gov.in/api/` — `GET /sectors` returns JSON (75 sectors with Id/Name/Code/description/S3 icons) and jobs are served under `/api/jobs/`, no key needed. Terms-of-use undocumented ⚠️. The **course-listing route could not be found** by endpoint guessing (`/api/courses*`, `/api/jobrole*`, `/api/v1/courses` all 404; the Angular SPA bundle exposes nothing) — needs DevTools XHR capture or headless browsing. A third-party Apify scraper listing (~150 vocational courses with NSQF levels + QP/NOS codes) confirms structured course data is extractable ⚠️ low confidence. Official **NSDC JobX API guide v1.0** is public (UAT base demo.nsdcjobx.com with Swagger UI, "most endpoints open") — job-exchange side only. **ASEEM is dead**: smis.nsdcindia.org no longer resolves; MSDE's convergence plan folded it into SIDH (alongside SIP/NAPS/NATS/eSkill India/Bharat Skills/NCVT MIS) — build against SIDH ✅.
- **NSDC qp-nos-results confirmed unscrapeable without a browser** ✅: Next.js client-rendered shell; RSC payload carries zero QP rows; sector/job-role lists load via undiscovered post-hydration XHR. NSDC's new backend is headless Drupal (`api1.nsdcindia.org/jsonapi` + `/api/custom-content/page/{alias}`, both open) but serves only marketing content types — QP data lives in the SIDH platform.
- **data.gov.in API works end-to-end** ✅: `GET https://api.data.gov.in/resource/{resource_id}?api-key=…&format=json&offset=0&limit=N` (+ `filters[field]=value`); free self-registration key; the widely-published demo key currently grants read access (live JSON verified). Missing key → `{"error":"Authorization field missing"}`. Legacy `datastore/resource.json` pattern dead.
- **Census SC data = manual only** ✅: village-level Primary Census Abstract with scheduled-caste indicators via censusindia.gov.in portal (interactive + Excel download, no API); the data.gov.in "SC population/literacy/workers 2011" resource page is NOT API-enabled (its embedded UUIDs return "Meta not found"); legacy A-10 individual-SC tables reachable via Internet Archive mirror; Kerala/Karnataka OGD mirrors host per-caste district tables but stale (2016) and JS-modal downloads.
- **PLFS**: annual report PDFs fully open on mospi.gov.in (2023-24 report verified, 26.9 MB); unit-level microdata free but **login-walled** at microdata.gov.in (NADA catalog DDI-IND-CSO-PLFS-2023-24); no machine API.
- **UDISE+**: public dashboard (AY 2024-25 figures) + Know Your School lookup open; detailed-reports module gated (HTTP 503 anonymous); microdata login-only.
- **MyScheme**: search API auth-gated behind **API Setu organizational partner signup** (PAN, GST, Certificate of Incorporation, authority letter — not hackathon-viable). Fallback that works today: individual scheme pages + sitemap.xml fully public (~4,700+ schemes) → HTML scraping for seeds is legitimate ✅.

### 7.3 Channel surfaces for Phase-2 (verified contracts)

- **Exotel Voicebot applet — the realistic IVR path** ✅: bidirectional WebSocket; events `connected/start/media/dtmf/stop/mark/clear`; audio = base64 raw slin 16-bit mono PCM LE, sample-rate selectable 8000/16000/24000 (default 8k), chunks in multiples of 320 bytes, min ~3.2 KB (≈100 ms), max 100 KB; **barge-in = send `clear` event**; auth via IP whitelist or Basic Auth in the WSS URL. SIP-trunk handoff variant (PCMA preferred, RFC 2833 DTMF) exists but bot-initiated outbound only works by bridging Leg B after Make-a-Call. No public INR rate card (indicative ₹0.30–0.50/min inbound from secondary sources ⚠️; worked example uses hypothetical ₹0.50/pulse); toll-free rental ₹1,500–3,000/month; Voice Streaming excluded from contact-center plans and priced separately.
- **Twilio cannot do domestic India calling** ✅ — country guidelines verbatim: "Outbound calls to India can only be made from international (non-Indian) numbers"; domestic reachability N/A; termination $0.0699/min landline, $0.0496/min mobile from foreign originators only; TRAI actively blocks UCC accounts. Document-and-dismiss in the runbook.
- **Self-hosted Asterisk/FreeSWITCH** ✅: AudioSocket dialplan app or ARI externalMedia (signed-linear 16-bit 8 kHz mono LE over TCP); native `chan_websocket` channel driver shipped in Asterisk 20.16+/22.6+/23+; FreeSWITCH mod_audio_stream (⚠️ v1.0.3+ is commercial, free up to 10 concurrent channels). **OSP registration was abolished** (DoT orders Nov 2020 / Jun 2021 — no license/bank guarantee/penalties; EPABX anywhere incl. cloud and WFH agents), but PSTN connection still requires SIP trunks/PRI bought from licensed TSPs, and carriers expect ~1 year of in-India IST-stamped CDR retention.
- **WhatsApp Cloud API voice loop** ✅: inbound voice note arrives as webhook audio message (audio/ogg;opus, `voice:true`) → GET media endpoint (download URL valid ~5 minutes) → transcribe → reply inside the 24-hour customer-service window with an OGG/OPUS audio message ≤16 MB (in-client playback icon only if ≤512 KB). Per-message pricing since 1 Jul 2025 (conversation pricing deprecated): Marketing ₹0.7846 / Utility ₹0.1150 / **Service replies free; user-sent messages never charged**; BSP platform fee stacks on top (~$0.001/msg, e.g., Gupshup). Meta mandates INR billing localization by 31 Dec 2026; a flagged higher marketing rate from 1 Jan 2026 was unverified ⚠️.
- Latency floor added by telephony transport: protocol granularity (~100 ms min chunks) + jitter buffers ≈ +100–200 ms over pipeline latency (§9.1).

---

## 8. Legal & compliance surface

### 8.1 DPDP Act, 2023 (Act No. 22 of 2023, assented 11 Aug 2023) ✅

All citations from the Gazette text (egazette.gov.in/WriteReadData/2023/248045.pdf):

- **Notice (s.5)**: must accompany or precede every consent request; itemize the personal data and purposes; state how to exercise rights and complain to the Board; and per **s.5(3) must be available in English + Eighth Schedule languages** — a legal mandate for exactly the hi/mr/te notice UX you are already building. Turn compliance into a feature: spoken, language-matched consent notice.
- **Consent (s.6)**: "free, specific, informed, unconditional and unambiguous with a clear affirmative action", purpose-limited to necessary data; withdrawal anytime with comparable ease (s.6(4)-(5)); processing ceases on withdrawal unless another basis applies (s.8(7) erasure duty).
- **Legitimate uses (s.7)**: deemed consent includes voluntarily-provided data for a specified purpose AND **State provision of subsidies/benefits/services/certificates/licences** — the hook a PM-AJAY-linked deployment would ride. Design the hackathon build as if pure-consent-based anyway; it demos better and survives ministry scrutiny.
- **Security/breach/erasure (s.8(5)-(7))**, Schedule penalties [via s.33(1)]: up to **₹250 cr** (security-safeguard failure), ₹200 cr (breach-notice failure), ₹200 cr (children's data), ₹150 cr (Significant Data Fiduciary duties), ₹50 cr catch-all, ₹10k principal-duty breach.
- **Children (s.9 + Rule 10)**: verifiable parental/guardian consent before processing under-18 data — relevant because skilling candidates include minors. Simplest compliant demo posture: capture only age *band*, gate full profiling on adult confirmation, roadmap the guardian flow.
- **Cross-border (s.16)**: transfers restrictable to notified countries (none notified as of research date); s.17(2)(a) lets the Centre exempt notified State instrumentalities entirely — relevant when arguing eventual government adoption.

### 8.2 DPDP Rules, 2025 (G.S.R. 846(E), notified 13 Nov 2025) — the compliance clock ✅

Phased commencement (Rule 1):

| Phase | Date | What switches on |
|---|---|---|
| On gazette | Nov 2025 | Definitions; Consent Manager registration framework (Rules 17–21); Board functioning |
| +1 year | ~13 Nov 2026 | Rule 4 Consent Manager registration/obligations |
| +18 months | ~13 May 2027 | Rules 3, 5–16, 22–23: itemised standalone notices, security safeguards, breach intimations, children's verifiable consent |

Builder-relevant specifics: Rule 3 requires a **standalone, plain-language, itemised notice** with a withdrawal/rights/complaint link; Rule 7 requires breach intimation to each affected principal without delay plus a **detailed report to the Board within 72 hours** (extendable); Schedule I requires a Consent Manager to be an Indian company with **≥₹2 crore net worth** — you will never be one, so keep consent records in-system rather than promising Consent-Manager interop.

### 8.3 Aadhaar — why the MVP excludes it, precisely ✅

- Aadhaar Act s.4(3) (2019-amended): use is **voluntary**, informed-consent-gated. **s.4(6)**: requesting entities must offer alternate viable identification means and may not deny service for refusing authentication.
- **s.4(4)**: authentication is only for entities authorized under a Parliamentary law or a Central-Government-prescribed purpose — practically, licensed **AUA/KUA** status, whose Category-3 private-entity gate needs ≥1 year operating history + **₹5 crore paid-up capital**, ~1 lakh auth/month capacity, India-hosted backend, UIDAI Tech-Centre audit (Authentication Regulations 2016).
- **s.8A offline verification**: permitted forms include QR-code verification and Paperless Offline e-KYC XML (Dec 2025 amendment added Aadhaar Verifiable Credential + Offline Face Verification), but it bars biometric authentication and storing Aadhaar numbers/biometrics, and Paperless e-KYC now requires registering as an **Offline Verification Seeking Entity (OVSE)** with UIDAI (plain QR-code checking does not).
- **s.57 was omitted** by the 2019 Amendment (sec. 25) after Puttaswamy-II struck contract-based private use ("any contract to this effect" ≠ law). **Puttaswamy-I** (9-judge, 24 Aug 2017) established the legality / legitimate-aim / proportionality test for privacy intrusions; **Puttaswamy-II** (26 Sep 2018) upheld s.7 welfare conditionality but struck indefinite retention of authentication metadata/logs — the leading Indian proportionality + storage-limitation precedents. Cite both when defending data minimization.
- The route that remains for a private app: **Good-Governance authorisation** (Aadhaar Authentication for Good Governance Rules 2020, amended G.S.R. 88(E) 31 Jan 2025) via the concerned Ministry → MeitY's swik.meity.gov.in portal → UIDAI examination → gazette notification. Roadmap-slide material ("an MoSJE partner can authorize our use-case"), never MVP.

### 8.4 Telephony & commercial communications law (Phase-2 IVR) ✅

Operative regime: TCCCPR 2018 as amended by the Second Amendment Regulations, 12 Feb 2025 (a Third-Amendment draft consultation opened 13 Mar 2026 — re-check before finale):

- An **inbound-only service helpline** via a CPaaS Exophone avoids most of this machinery. The moment you place outbound or auto-dialer calls: advance notification to the originating access provider of Auto-Dialer/Robo-Call use and its objective (new Reg. 4); promotional robocalls only on **140-series** numbers, service/transactional robocalls on **160-series**; header suffixes -P/-S/-T/-G identify Promotional/Service/Transactional/Government; explicit consent captured for transactional messages is valid at most **seven days**.
- Penalties scale brutally: first UCC violation disconnects **all** of the sender's telecom resources across all access providers for 15 days; repeat violations → 1-year disconnection + blacklisting + device blocking. DLT registration duties sit with the sender (Principal Entity + headers + content templates).

### 8.5 AI-specific duties ✅

- **MeitY advisory, 15 Mar 2024** (ref eNo.2(4)/2023-CyberLaws-3; supersedes the withdrawn 1 Mar 2024 version): AI models/LLMs/GenAI must not permit unlawful content, bias/discrimination, or electoral-integrity threats (IT Rule 3(1)(b)); **under-tested or unreliable foundational models may be offered in India only after labelling possible fallibility/unreliability, with a consent popup** informing users. Your "beta — AI guidance; confirm with your officer" interstitial tracks this advisory almost verbatim; say so on the compliance slide.
- **IT (SGI) Amendment Rules, 2026** (notified 10 Feb 2026, effective 20 Feb 2026): synthetically-generated audio/video must carry prominent labels + embedded identifiers; per MeitY FAQ, **pure text chatbot output falls outside scope**. Your TTS speaks grounded factual guidance rather than impersonative synthetic media — low exposure — but label TTS output in the roadmap anyway.
- Cautionary tale with a name: Malaysia's **MyGOV AI chatbot was shut down in Aug 2025** after inaccurate answers (and still erred post-relaunch). Its surviving mitigations — beta labelling, mistake warnings, redirecting users to official portals instead of guessing — independently validate AVSAR's refusal-first, handoff-to-officer posture.

**Design implications (final, citation-anchored):**
- Data minimization by schema: collect only district / age-band / gender / education level / aspiration / current work. **No name field ever exists**; phone optional. Satisfies DPDP purpose-limitation and mirrors Puttaswamy-II's storage-limitation holding.
- Spoken consent captured as a designed dialogue turn (mode/ts/playback-ref stored per session) = demonstrable s.5/s.6 trail, delivered in hi/mr/te per s.5(3).
- No Aadhaar in the hackathon build (§8.3); roadmap = OVSE registration or Good-Governance authorization via MoSJE.
- Retention script (`purge_old.py`) implements s.8(7) erasure-on-withdrawal/purpose-expiry ahead of the May 2027 Rules phase-in — cheap to build now, quotable later.

---

## 9. Architecture patterns

**Carried anchors:** Farmer.Chat's measured budget ~9 s end-to-end acceptable in-field ✅; translate-to-English reasoning beat native-language generation in production ✅; guided suggestions > free-form input ✅; DTMF preference ✅; Bhashini-primary/Azure-failover reliability pattern ✅; ULCA dynamic-endpoint/config-response contract ✅.

### 9.1 Turn-taking & latency — the physics you design against ✅

- Humans expect conversational gaps of **~208 ms mean** across languages (PNAS turn-taking study); the de-facto industry voice-agent target is **~800 ms voice-to-voice** (OpenAI Realtime ≈500 ms TTFB leaves ~300 ms for everything else). The dominant cost in practice is **VAD/end-pointing at 200–400 ms**; recommended production KPIs are p50 <800 ms / p95 <1.4 s, and sessions drift past 2 s after ~20 turns as context re-inclusion grows — mitigate by rotating/reseeding context every 8–12 turns.
- Endpointing tuning evidence: LiveKit relaxes silence defaults to min 0.3 s / max 2.5 s with a forced commit within ~1 s; OpenAI's server VAD default is 500 ms and guidance warns against going lower — gain perceived speed from context-aware endpointing and speculative inference, not shorter silences; LiveKit's "dynamic" endpointing adapts via an exponential moving average of pause statistics — built for exactly the variable-pause profile of elderly/rural speakers. Interview-style use cases benefit from 800 ms–1 s waits.
- Streaming STT measurement reality: Deepgram targets ≤300 ms interim latency; finals lag behind because of endpoint detection — measure latency on interims (`is_final:false`); Pipecat frames Time-To-Final-Segment as THE configuration input driving response wait.
- Telephony end-to-end proof points: a published H100 pipeline (streaming Conformer ASR + 4-bit 2B LLM + RAG + sentence-streamed TTS) totals **0.93 s mean pipeline / 0.68 s time-to-first-audio** excluding transport → caller-perceived ~1.2–1.5 s; ~1.5 s is the practical PSTN comfort threshold. Bhashini's Media Gateway supports WebSocket streaming ASR→LLM→streaming TTS over RTP with barge-in, and MeitY launched **VoicERA** — an open-source voice-AI stack on Bhashini's National Language Infrastructure with multilingual telephony — at the India AI Impact Summit 2026: cite it as ecosystem tailwind for your IVR roadmap.
- **AVSAR implication:** our ≤9 s p50 budget (Farmer.Chat precedent) is ~10× looser than industry voice targets because we carry retrieval+LLM+TTS over rural networks — defensible on stage, but steal the cheap wins: show interim transcripts while the user speaks, start TTS on the first final sentence, allow barge-in, raise silence thresholds for elders, rotate session context every 8–12 turns.

### 9.2 Retrieval over policy documents ✅

- **Contextual Retrieval** (Anthropic): prepending 50–100 tokens of LLM-generated chunk context cuts top-20 retrieval failure −35%; adding contextual BM25 → −49%; adding reranking → −67%. Cost $1.02 per million document tokens — run offline in pipelines.
- Chunk size interacts with retriever type (PDF-regulation benchmark, 500-token chunks, k=8): bigger chunks help BM25 (Hit@8 .750→.833) but collapse dense ranking (MRR .722→.577 via semantic dilution); **hybrid BM25+dense fused by Reciprocal Rank Fusion wins overall** (Hit@8 .875–.917 vs BM25 .750, dense-only .792). **Multi-hop questions cap Chain-MRR at 0.44 even at perfect recall unless section paths are embedded in each chunk** → prefix every guidelines chunk with its chapter/section path (ARCHITECTURE.md §4 doc_chunks already has `section`).
- Faithfulness ladder (policy-QA study): vanilla LLM 0.347 → basic RAG 0.621 → advanced RAG + cross-encoder reranking 0.797 (+79% average faithfulness).
- **Indic embedding choice:** Hindi-BEIR nDCG@10 — BGE-M3 47.29 > mE5 39.93 > BM25 36.50 ≫ LaBSE 18.72. **LaBSE, often casually recommended for Indic work, is a trap**; MIRACL-Hindi agrees (BGE-M3 59.34 ≈ mE5 58.11 ≫ BM25 40.98). BGE-M3 additionally emits dense+sparse from one model (true hybrid retrieval from one index) and takes 8k-token inputs — worth an A/B against multilingual-e5 in Phase 1. (A NAACL 2025 camera-ready reports their NLLB-E5 beating both on several subsets ⚠️ numeric tables unverified.)
- Rerankers raise precision but **the retriever sets the recall ceiling** (best reranker lifted Hit@1 62.7%→83.0% yet no reranker beat ~88% Hit@10). Corrective RAG formalizes grade-then-recover loops; citation-grounded generation measurably reduces hallucination (FRONT +14.21% citation quality; VeriCite NLI claim-checking; CAGE abstention when no document supports the answer).

### 9.3 Deterministic tool-calling (why AVSAR's shell around the LLM works) ✅

- Function-calling best practice (OpenAI guidance; generalizes to Claude tool use): strict schemas (`additionalProperties:false`, all fields required), enums over boolean flags so invalid states are unrepresentable, `tool_choice:'required'` + `parallel_tool_calls:false` for exactly zero-or-one call per turn, keep available tools under ~20 per turn, constrain free-text inputs with grammars.
- Emerging Indian welfare-assistant pattern (open-source Scheme Saathi et al.): **a rules engine judges eligibility while the LLM only extracts slots and phrases verdicts** — numeric comparisons go to code, producing auditable matched/failed criterion lists. This is precisely ARCHITECTURE.md's deterministic-core/generative-shell split, independently converged: citable precedent that the design is state-of-the-art, not idiosyncratic.

### 9.4 Language strategy ✅

- Farmer.Chat explicitly rejects native-language generation: *"generating responses directly in the source language results in poorer performance compared to translating the query into English, processing it via the LLM, and then back-translating."* English-Pivoted CoT training shows up to +28.33% gains on low-resource tasks. Honest caveats: pivot benefits are resource-dependent (no gain for French; insufficient for Swahili; translation errors cause up to ~0.77 failure fraction for genuinely low-resource languages) — hi/mr/te sit mid-to-high resource where the pivot holds. No peer-reviewed gov-scheme-QA comparison of native vs pivot exists (state it as production evidence, not settled science).
- Language-ID routing earns real WER: a multilingual wav2vec front-end used for LID + per-language model switching yields **~50% relative WER improvement** across hi/mr/ta/te/gu/bn/odia; IndicConformer-600M-multilingual (MIT license) covers all 22 scheduled languages in ONE model whose language token doubles as the router signal (Hindi WER 13.2 on Vaani benchmark); MADASR 2.0 pushes to joint language+dialect prediction (8 languages × 33 dialects).

### 9.5 Low-literacy & accessibility UX — evidence base for every screen decision ✅

WCAG 2.2 (W3C Recommendation 5 Oct 2023, updated 12 Dec 2024; nine new criteria, additive to 2.1):
- **2.5.8 Target Size AA: ≥24×24 CSS px** pointer targets — the icon-grid rule for low-literacy users.
- **3.3.7 Redundant Entry A**: previously-entered info must be auto-populated or selectable — becomes mandatory once you promise offline retry.
- **3.2.6 Consistent Help A**: ever-present help — converges exactly with Medhi et al.'s low-literacy help finding.
- 1.4.4 Resize Text (200% without loss), 1.4.12 Text Spacing (line-height ≥1.5×, etc.) — Devanagari matras/shirorekha need generous line height regardless. W3C explicitly discourages requiring AAA site-wide.

ICTD field evidence:
- **Medhi CHI 2013** (60 low-income Indian participants): textual literacy AND non-verbal (Raven's) ability both predict navigation success even on entirely text-free UIs; recommendation verbatim: *keep navigational UIs linear to the extent possible and minimize hierarchical depth even at the expense of conciseness*.
- **Medhi CHI 2009** (multi-country ethnography + India usability study): spoken dialog was fastest and needed least assistance; rich multimedia gave better task completion; both beat text. Guidance: minimal hierarchy, no scrolling menus, avoid non-numeric text input, voice-annotate graphics.
- Icon studies (Kerala n=58; farming villages): detail + concreteness drive correct interpretation; concrete-contextual icons win over abstract ones. **VideoKheti CHI 2013: spreading 22 choices over two screens made selection harder than compact sets of ~4** — validates the max-4-options rule in PLAN.md.
- 'Hierarchy or List?' (24 emergent users): lists faster on GUI/audio-visual interfaces, hierarchies faster audio-only; visuals increased IVR task completion regardless of menu depth.
- Input modality: Patel CHI 2009 controlled trial (45 farmers) — dialed/DTMF input beat speech on task completion, with the largest gains among under-30s and less-than-8th-grade education; Avaaj Otalo interview preference for touchtone was 100% (§6.3).
- Ecosystem cautionary data: Kisan Call Centre — 94.5% of farmers found it difficult to explain symptoms over a call (voice loses diagnostic richness; provide photo/officer escape hatches) and only 14% knew the toll-free number (awareness, not UI, caps uptake — plan a CHW/e-CRP onboarding channel); UMANG exhibits partial screen-reader support, Android 7 cutoff, Aadhaar OTP rate-limit failures; StreetWise (Dharavi, 18 systems, 12k+ questions) and ASSETS 2022 smart-speaker deployments favor human+AI hybrids over pure-AI answers; CGNet Swara (575k calls, 287 community problems solved) and Mobile Vaani (10k+ calls/day, 100k monthly users, miss-call access, zero smartphone/data requirement) prove IVR reach among your exact population.

Devanagari typography specifics ✅:
- Material Design classifies Devanagari as a **tall script**: line height +0.1 em vs Latin at every style; Title-through-Caption sizes +1 px; use Noto Sans (not Roboto); **avoid Bold** — native readers judge it too heavy.
- Use Noto Sans **UI** families for interface text; complex-script shaping (GSUB/GPOS) is required for conjuncts (Noto Sans Devanagari = 954 glyphs); W3C deva-lreq: hanging baseline alignment, letter-spacing applied per orthographic syllable (not per character), line breaks only at inter-word spaces, **never start a line with danda (।)**.

PWA/offline mechanics ✅:
- Workbox strategy map: cache-first only for revisioned assets; stale-while-revalidate for frequently-updating non-critical resources; network-first (+timeout) for updating content; opaque cross-origin responses are refused under cache-first; non-GET requests always network-only.
- Background Sync queue (IndexedDB replay, default retention 7 days) is **Chromium-only** — absent in ALL Safari versions and Firefox → ship the service-worker-start replay fallback path unconditionally.
- **iOS Safari evicts all script-writable storage after 7 days without site interaction — EXCEPT home-screen-installed PWAs**; call `StorageManager.persist()` and prompt Add-to-Home-Screen for the kiosk story. Chrome allows ~60% disk per origin, Firefox 50%/2 GB cap — model artifacts won't fit client-side; they stay server/USB-side exactly as TECH_STACK.md §6 already decides.

---

## 10. SIH reality

### 10.1 Rules that bind your submission (SIH 2026 official docs) ✅

Sources: sih.gov.in — Guidelines PDF (`SIH 2026 Guidelines.pdf`), Idea Presentation Format PPTX (`SIH2026-IDEA-Presentation-Format.pptx`), College SPOC guidelines.

- Team: **exactly 6 students, one college, ≥1 female member mandatory**; ≤2 optional mentors (~5 yrs experience); travel reimbursement cap ₹3,000/person.
- Idea submission opens Aug 2026; **500-idea cap per PS** (PS freezes at cap; live counter shown); max **2 PS per team**; Grand Finale proposed **offline, December 2026** at nodal centres. ⚠️ The guidelines nowhere specify finale duration — the folklore "36-hour build" is **not sourced**; plan a build plan that flexes from 24h to 48h.
- Evaluation criteria (official nine-factor list, post-submission expert evaluation): **novelty · complexity · clarity/detail in prescribed format · feasibility · practicability · sustainability · scale of impact · user experience · potential for future work progression.** No published numeric weights.
- Only **4–5 teams per PS** reach the finale; the PS organisation has final say and may declare **no winner**.
- Prize: **₹1,50,000 per PS** to winner(s) — paid **only if** the organisation likes the idea; IP shared equally between organisation and winning team (or by mutual agreement).

### 10.2 The 6-slide template is the de-facto rubric ✅

Fixed, non-editable sequence (max **6 slides incl. title**, upload **PDF only**, points/diagrams/infographics — no paragraphs, novelty stated explicitly):
1. **Title** — PS ID, title, theme, Software/Hardware, Team ID, team name
2. **Proposed Solution** — innovation/uniqueness + how it addresses the problem
3. **Technical Approach** — name concrete languages/frameworks/hardware; flow charts/images/working prototype (a named-stack diagram is expected AT IDEA STAGE)
4. **Feasibility & Viability** — feasibility analysis + potential challenges/risks + mitigation strategies (= your risk register: dialect ASR limits, Bhashini PoC-license, connectivity, data access)
5. **Impact & Benefits**
6. **Research & References** — links/details of reference and research work (this document is your raw material)

### 10.3 Prior-year ground truth ✅

**SIH 2024** (results table, sih.gov.in):
- Master PS list: **246 statements; ZERO occurrences** of PM-AJAY/Anusuchit/Abhyuday/NSQF/Scheduled Caste/Grant-in-Aid/Adarsh Gram/SSC/PMKVY/NCS/Bhashini/AI4Bharat/NCO-2015/IVR → **no prior-year baseline; first-of-kind PS**.
- MoSJE sponsored 11 PSs; 10 from the DePWD wing (ISLRTC/NIEPID/NIEPMD/AYJNISHD); only ONE from DoSJE proper — **SIH1719 (Statistics Division): "Monitoring System for classroom session in skill training programme"** with prose-promised dataset of job roles + curricula + infra requirements (Datasetfile column NULL). → MoSJE's skilling wing thinks in job-role taxonomies and wants monitoring; your PS extends that trajectory.
- Closest functional cousin: **SIH1781 (NCVET): "AI-Enhanced Career Guidance System for Personalized Career Pathways"** — aptitude/aspiration/ability mapping + skill gaps, but never names NSQF/QP/NOS in PS text. NCVET sponsored 5 PSs (SIH1777–81) incl. voice-controlled learning games (SIH1779).
- MoSJE outcomes: **11 winners, all sole winners** (no Joint Winners for MoSJE despite 67/246 PSs having multiple winners overall); venues clustered at Amal Jyothi CE, Shobhit Inst., NIT Srinagar; 6/11 winning teams from Tamil Nadu colleges. Five PSs nationwide got NO winner (SIH1529/1564/1692/1697/1776) — the bar is real.
- Baseline expectation signal: SIH1717 ("Indian Version of Nagish App") demanded real-time bidirectional voice⇄text across multiple Indian languages **and dialects** with simple UI → multilingual speech tech + low-literacy UI is table stakes for MoSJE, not stretch goals.

**SIH 2025** (results table):
- DoSJE winners: **SIH25059 Data_CodeBlitz** (Guru Ghasidas Vishwavidyalaya, Bilaspur) and **SIH25060 Si Extractors** (Sethu Institute of Technology, TN) — both evaluated at KIET Group of Institutions nodal; standard prize ₹1.5L (joint = ₹75k each; ISRO PSs alone used tiered 100k/75k/50k).
- Three PSs got no winner (SIH25056/25199/25214).
- Results page publishes **no rubric/jury info** — rubric lives in the guidelines/template docs above.

**Strategic reads:** sole-winner culture for MoSJE PSs → aim to be unambiguous #1; TN-heavy wins are demographics of participation, not bias; the Statistics Division (your PS's likely owner) has historically wanted structured skilling data systems → emphasize the structured artifacts your system produces (household livelihood profiles, district heatmaps, AAP-ready exports), not just the chat experience.

---

## 11. The strategic synthesis

1. **Name the compliance loop.** Your system operationalizes Ch.3 §7.A.a.iv of the operative guidelines: aspiration capture (voice, Indic) + job-market factoring (district data) + NSQF QP output + AAP-ready export. Quote the paragraph on slide 2. Nobody else will have read the guidelines this closely.
2. **Own the missing crosswalk.** aspiration→NCO-2015→QP is unpublished everywhere (Kaushalverse ncoCode null; NQR free-text; NCS no taxonomy) ✅ — building it as a curated, versioned dataset + embedding index IS the intellectual contribution. Say "we are publishing the missing join table."
3. **Design for 26.8% WER, not around it.** Rural-telephony ASR error is measured ✅. Mitigations that impress judges because they're evidence-backed: guided slot menus + suggestion buttons (Farmer.Chat >45% interaction share ✅), DTMF fallback (Avaaj Otalo preference ✅), read-back confirmation loops, keyword-spotting router, Bhashini-with-Azure-failover ✅.
4. **Respect the license lines.** Bhashini PoC-only ✅ → demo on free keys, roadmap-slide the Sahyogi/App Mitra tier. NCS has no API ✅ → adapter/mock now, MoU later. pmajay endpoints unofficial ✅ → cached seeds.
5. **Route to PMKVY, not PM-DAKSH** ✅ (merged w.e.f. FY2026-27) — a current-affairs detail most competing teams will miss.
6. **Target the absorption story** ✅: ₹736.28 cr actual vs ₹2,140 cr BE. Frame KPIs as beneficiaries-mapped-per-officer-day, AAP-cycle-time reduction, % women captured (≥30% mandate ✅), ≥15% women-income earmark tracking ✅.
7. **Slide 4 risks, pre-written** (from verified facts): dialect ASR degradation outside 12 scheduled languages ✅; Bhashini PoC license ✅; unofficial portal endpoints ✅; NQR→Kaushalverse migration churn ✅; half-level NSQF granularity breaking naive integer logic ✅; reporting lag in dashboard JSONs ✅; cross-ministry NCS dependency ✅; connectivity/offline (see §9.5).
8. **Demo script that survives bad networks:** recorded-audio fallback path, pre-seeded catalogue snapshot, canned TTS responses, DTMF-only mode. Judges forgive latency (9s precedent ✅), not dead screens.

---

## Appendix A — Verification ledger: claims killed by adversarial checking ❌

Three independent verifiers attempted refutation per claim; ≥2/3 kills it. These died — **never cite them**:

1. ❌ **"Guidelines_PM-Ajay_may2023.pdf is 20pp"** — false; pdfinfo says 43 pp (some voters saw a 46-pp Feb 2022 file at a different URL). The substantive quotes inside the killed claim (NSDC skill-gap factoring; NSQF/Common Norms mandate) ARE genuine and appear verbatim in the May 2023 PDF — they survive as separate claims S1/S2/S13/S14. Kill reason was the page-count + sourcing-hygiene defects, not the substance.
2. ❌ **"Income-generation subsidy norm is Rs 10,000/beneficiary or 50% of loan; enhancement stuck since 2018-19; 'meager' subsidy"** — sourced from a **frozen pre-merger legacy page** on pmajay.dosje.gov.in describing the old SCA-to-SCSP scheme (performance table ends 2021-22; page says merger "under consideration"). Current norm per May 2023 guidelines: **₹50,000 or 50% of project cost**. The Rs 10,000 story is wrong TODAY even though the quote is real.
3. ❌ **"₹50,000 or 50% of ASSET cost, whichever is less"** — Feb 2022 wording; May 2023 changed denominator to **project cost**. Also "structured as loan assistance, not a grant" framing overreached. Salvageable parts that DID verify elsewhere: no standalone asset distribution; mandatory financial-literacy + bank-linkage component.
4. ❌ **"Up to 15% of grants reserved exclusively for SC women's schemes"** — direction inverted. Feb 2022: "Up to 15%"; May 2023: "**At least** 15%" (ceiling→floor). Cite the floor.
5. ❌ **"MoSJE classifies PM-AJAY as entry #4 under 'Schemes for Social Empowerment' making pmajay.dosje.gov.in the authoritative transaction portal"** — compound kill: "#4" is an alphabetical-sort artifact; "transaction portal" unsupported (guidelines call it the MIS/plan-upload portal); the directory row says nothing about data/APIs. Portal's existence and MIS role verified separately.

Also corrected during verification (kept with caveats): NQR-code universality ("every qualification carries a parsable NQR Code" → most do; treat as partial); NQR Beta/migration status (verified but one voter demanded more corroboration → carry ⚠️).

## Appendix B — Primary source master list

**Scheme & budget**
- PM-AJAY Guidelines (May 2023 Revised) — https://socialjustice.gov.in/writereaddata/UploadFile/36851753087331.pdf (mirror: https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf)
- PM-AJAY Guidelines (Feb 2022, superseded — for diffing only) — https://socialjustice.gov.in/writereaddata/UploadFile/31121740857806.pdf
- Scheme page — https://socialjustice.gov.in/schemes/104 · Master index — https://socialjustice.gov.in/schemes
- Portal — https://pmajay.dosje.gov.in (+ `/illustrative-list`, `/course-list`, `/front/reportajax`)
- Notes on Demands for Grants 2026-27, Demand 93 — https://www.indiabudget.gov.in/doc/eb/sbe93.pdf (prior years: indiabudget.gov.in archive)

**Skills framework**
- NSQF gazette (27 Dec 2013) — https://ncvet.gov.in/wp-content/uploads/2022/08/NSQF.pdf
- NQR — https://nqr.gov.in · Kaushalverse — https://kaushalverse.ncvet.gov.in/homepage/repository (+ `/assets/config/env.json`)
- NSDC QP-NOS — https://nsdcindia.org/qp-nos-results
- NCS — https://www.ncs.gov.in · SIDH — https://www.skillindiadigital.gov.in

**Speech stack**
- Bhashini docs — https://bhashini.gitbook.io/bhashini-apis · Onboarding — https://bhashini.gov.in/ulca/user/register#
- Vistaar/IndicWhisper — https://github.com/AI4Bharat/vistaar
- IndicVoices/IndicASR — https://arxiv.org/abs/2403.01926
- IndicSUPERB/Kathbath — https://arxiv.org/abs/2208.11761
- Sarvam pricing — https://docs.sarvam.ai/api/getting-started/pricing.md

**Prior art**
- Farmer.Chat — https://arxiv.org/abs/2409.08916
- Jugalbandi Manager — https://github.com/OpenNyAI/Jugalbandi-Manager
- Avaaj Otalo — https://doi.org/10.1145/1753326.1753434
- CGNet Swara — https://doi.org/10.1145/2160673.2160695

**SIH**
- SIH 2026 Guidelines — https://www.sih.gov.in/letters/2026/SIH%202026%20Guidelines.pdf
- Idea Presentation Format — https://www.sih.gov.in/letters/2026/SIH2026-IDEA-Presentation-Format.pptx
- SIH 2024 results — https://www.sih.gov.in/sih2024/sih2024-grand-finale-result · PS sheet — https://www.sih.gov.in/letters/SIH_PS_2024.xlsx
- SIH 2025 results — https://www.sih.gov.in/sih2025/sih2025-grand-finale-result

**Livelihood & planning data** (§4)
- DAY-NRLM community institutions — https://aajeevika.gov.in/work-structure/community-institutional
- Lakhpati Didi Digital Aajeevika Register — https://lakhpatididi.gov.in/digital-ajeevika-register/
- DAY-NRLM Comprehensive Document (incl. PIP-PPA) — https://cdnbbsr.s3waas.gov.in/s3e6c2dc3dee4a51dcec3a876aa2339a78/uploads/2023/08/2023080499.pdf
- Lakhpati Didi count annexure — https://sansad.in/getFile/lsapps/loksabhaquestions/annex/188/AS123_3PK8V5.pdf · DSDP annexure — https://sansad.in/getFile/lsapps/loksabhaquestions/annex/188/AS320_APDsHG.pdf
- NSDC District Wise Skill Gap Studies — https://stag-api.nsdcindia.org/system/files/2025-08/District%20Wise%20Skill%20Gap%20Study%20of%20Rajasthan%2C%202012-17%2C%202017-22.pdf (URL-pattern family)
- ICAR-CRIDA district contingency plans — https://www.icar-crida.res.in/Crop_Contingency_Plan.html
- NIRDPR NRLM handbook — https://nirdpr.org.in/nird_docs/nrlm/nrlmhandbook240614.pdf · PRA material — https://nirdpr.org.in/nird_docs/sb/sb080720.pdf

**Legal & compliance** (§8)
- DPDP Act 2023 gazette — https://egazette.gov.in/WriteReadData/2023/248045.pdf · DPDP Rules 2025 — https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa
- Aadhaar Act — https://www.uidai.gov.in/images/Aadhaar_Act_2016_English.pdf · Good-Governance portal — https://swik.meity.gov.in · OVSE registration — https://uidai.gov.in/en/ovse-registration.html
- Puttaswamy I — https://main.sci.gov.in/supremecourt/2012/35071/35071_2012_Judgement_24-Aug-2017.pdf · II — …/35071_2012_Judgement_26-Sep-2018.pdf
- TCCCPR 2018 — https://trai.gov.in/sites/default/files/2025-01/RegulationUcc19072018.pdf · Second Amendment 2025 — https://trai.gov.in/sites/default/files/2025-02/Regulation_12022025.pdf
- MeitY AI advisory 15 Mar 2024 — https://iprmentlaw.com/wp-content/uploads/2024/03/March_15_AI_advisory__1710574832.pdf

**Architecture evidence** (§7.3, §9)
- Contextual Retrieval — https://www.anthropic.com/engineering/contextual-retrieval
- Chunk-level RAG eval on regulations — https://hps.vi4io.org/_media/research/labs/2026/2026-01-corinna_liley-chunk_level_retrieval_evaluation_in_rag_systems_a_case_study_onuniversity_regulations-report.pdf
- Hindi-BEIR — https://arxiv.org/html/2408.09437 · BGE-M3 — https://arxiv.org/abs/2402.03216 · Corrective RAG — https://arxiv.org/abs/2401.15884
- Telephony voice-agent pipeline latency — https://arxiv.org/html/2508.04721 · Exotel Voicebot applet — https://developer.exotel.com/docs/agentstream/stream-voicebot-applet · Twilio India guidelines — https://www.twilio.com/en-us/guidelines/in/voice
- Human turn-taking ~208 ms — https://www.pnas.org/doi/10.1073/pnas.0903616106
- WCAG 2.2 — https://www.w3.org/TR/WCAG22/ · new-in-2.2 — https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- Medhi CHI 2013 — http://cutrell.org/papers/Medhi-CHI2013-Hierarchy.pdf · VideoKheti CHI 2013 — https://cutrell.org/papers/Cuendet-CHI2013-VideoKheti-Final.pdf · Patel CHI 2009 speech-vs-dial — https://doi.org/10.1145/1518701.1518709
- Workbox strategies — https://developer.chrome.com/docs/workbox/modules/workbox-strategies · web storage quotas/eviction — https://web.dev/articles/storage-for-the-web
- Material Design Indic typography — https://m1.material.io/style/typography.html · W3C Devanagari layout reqs — https://www.w3.org/TR/2024/DNOTE-deva-lreq-20240920/
- SIDH open gateway — https://api-fe.skillindiadigital.gov.in/api/sectors · data.gov.in API how-to — https://data.gov.in/help/how-use-datasets-apis
