# docs/slides-outline.md — SIH 6-slide deck outline

Mapped to the fixed SIH template recorded in **research.md §10.2**: max **6
slides including the title**, **PDF only**, points/diagrams/infographics — *no
paragraphs* — and novelty stated explicitly. The sequence is non-editable, so
the headings below are the ones the template gives, in order.

Every figure here is copied from a verified source. The ✅ marks in research.md
mean the claim survived adversarial verification; figures marked ❌ in
Appendix A of research.md are **not** used anywhere in this deck. Nothing on
these slides is estimated unless the slide says "estimate".

---

## Slide 1 — Title

- **PS ID:** _(fill from the SIH portal entry)_
- **Problem Statement Title:** _(verbatim from the portal — do not paraphrase)_
- **Theme:** Smart Automation / Miscellaneous _(as listed against the PS)_
- **PS Category:** Software
- **Team ID / Team Name:** _(fill)_
- **Project name:** **AVSAR** — *Aspiration-to-Vocational Skilling Assistant &
  Recommender*

> Leave this slide factual. Every field is a portal field; a wrong PS ID is an
> unforced error.

---

## Slide 2 — Proposed Solution

**Lead with the compliance loop. This is the slide nobody else can write.**

- The guidelines **already legally require** what we automate — quote it:
  > "…confirming that the proposals are relevant to the District/State, **in
  > terms of aspiration of the target group and availability of job market**."
  > — PM-AJAY Guidelines (May 2023 Revised), **Ch. 3 §7.A.a.iv**
- Today that loop runs **on paper**, through district officers.
- AVSAR is the voice front door: **speak your aspiration in Hindi / Marathi /
  Telugu / English → get an NSQF-QP-coded course with local seat availability
  and the assistance figure, in seconds.**
- **The absorption number that makes it urgent:** FY 2024-25 actual spend
  **₹736.28 cr against ₹2,140 cr BE (~34%)**; RE 2025-26 cut **41.6% to
  ₹1,250 cr**. Slow beneficiary-level project formation is the ministry's own
  documented pain.
- **Novelty, stated explicitly (the template demands it):**
  1. **We publish the missing join table.** aspiration → NCO-2015 → NSQF QP is
     unpublished everywhere — of the **1,170** NCVET qualifications we
     ingested, `nco_code` is populated on **zero**; NQR is free text; NCS has
     no taxonomy.
     Ours is curated, versioned, cited: **411 rows, 33 concepts, all 10 GIA
     domains, 83 real QP codes**, with declared gaps rather than guesses.
  2. **Deterministic core, generative shell.** The language model never picks a
     course and never states a number. Recommendations come from database
     queries; a numeral guardrail rejects any digit not present in the tool
     JSON, retries once, then falls back to a deterministic template.
  3. **It works with the wifi off.** Mock speech + template verbalizer complete
     the whole journey with zero API keys.
- **Data minimisation by schema:** there is **no name column anywhere in the
  database**. Phone is optional. Consent is recorded before any profile field
  is stored.

---

## Slide 3 — Technical Approach

*The template expects a named stack and a flow diagram even at idea stage.*

**Flow (one diagram, left to right):**

```
speak  →  ASR (Bhashini / Sarvam / Azure / mock)
       →  FSM: consent → 5 profile slots → aspiration → confirm
       →  crosswalk lookup (exact → containment → trigram)
          ∪ hybrid retrieval: BM25 ∪ pgvector, fused by RRF (k=60)
       →  deterministic scorer: semantic 0.40 · local supply 0.25
          · level fit 0.15 · placement prior 0.10 · equity 0.10
       →  LLM verbalizes ONLY the tool output  →  numeral guardrail
       →  TTS  →  officer dashboard · AAP-ready CSV/XLSX export
```

**Named stack:**

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI, SSE streaming |
| Data | PostgreSQL 16 + **pgvector** (HNSW) + `pg_trgm`; Alembic; Redis |
| Embeddings | `multilingual-e5-base`, 768-dim, CPU, `query:`/`passage:` prefixes |
| Retrieval | BM25 (tsvector) ∪ vector, **Reciprocal Rank Fusion, k=60** |
| Speech | Provider ladder with demotion after 2 failures → mock rung |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind, PWA + service worker |
| Auth | argon2id, JWT (30 min / 12 h), RBAC viewer < officer < admin, audit log |
| Ops | Docker Compose, `/metrics` Prometheus, structured JSON logs |

**Two design decisions worth a line each:**

- **NSQF levels are `NUMERIC(3,1)`, never integers.** 22.9% of the 1,170
  qualifications we ingested carry half-levels (2.5, 4.5). Rounding them would
  silently mis-gate eligibility for roughly one course in four.
- **Seeds, not scraping.** Government sources are ingested once at 1 req/s into
  committed seed files; runtime never calls a portal except through one
  explicitly labelled live-check endpoint.

---

## Slide 4 — Feasibility & Viability

*Feasibility, then risks, then the mitigation actually implemented — not
promised.*

**Feasible today, measured on the build machine:**

- Full mock voice journey, cold start to summary: **9 turns, ~1.1 s** of server
  time; the budget is ≤3 minutes.
- Per-stage latency against the design budget (**mock providers — see the
  honesty note below**), from `make latency` on a freshly started core: ASR p50
  5.1 ms, retrieval p50 92.2 ms, scoring p50 1.4 ms, TTS first byte p50 34.5 ms,
  end-to-end turn **p50 58.3 ms / p95 535.2 ms** over 63 turns. Every stage is
  inside its ARCHITECTURE §3 budget.
- **492 automated tests pass.** Grounding verified across **50 random sessions,
  256 numerals, 0 ungrounded, 0 invented course names or QP codes**.
- Cost, from the published Bhashini/Sarvam rate card: a 2-minute conversation ≈
  2 min STT (₹1) + ~600 chars TTS (₹0.9) + trivial translation ≈
  **under ₹2 per conversation**. Rate limits, not cost, are the constraint.

**Risks and what is already built against them:**

| Risk (evidence) | Mitigation, implemented |
|---|---|
| **Rural ASR error is ~1 word in 4** — IndicWhisper **26.8% WER** on the GramVaani rural-Hindi benchmark; per-language spread is >3× (hi 13.6, mr 18.2, te 28.8) | Designed *for* the error, not around it: 4-option guided menus, read-back confirmation before any recommendation, tap fallback after 2 empty ASR turns, clarify step below a 0.55 confidence threshold |
| **Venue wifi / provider keys fail** | Mock-first is the committed default. Kill-a-service drill: network off (incl. `--network none`), database stopped, key revoked — **7/7 checks pass, exits 0** |
| **Bhashini is PoC-licensed** | Demo on free keys; provider adapters are swappable; the Sahyogi/App-Mitra tier is a roadmap line, not a claim |
| **Government portal unavailable** | It was, for this entire build — the PM-AJAY portal served a maintenance page. Course rows are **synthetic and labelled `synthetic=true`** from ingestion through the dashboard badge to the export's compliance sheet. Documented in `docs/ingest-report.md` |
| **Model invents a figure** | Numerals are extracted (including Devanagari/Telugu digits), checked against the tool JSON, regenerated once, then replaced by a template. `make grounding` proves it |

> **Honesty note to say out loud:** the latency figures above are measured with
> the **mock** speech and LLM providers. They are real measurements of a real
> code path, but they are not a measurement of Bhashini. The keyed-run number is
> not claimed because it was not run.

---

## Slide 5 — Impact & Benefits

**Who benefits, and in what unit.**

- **Beneficiary:** speaks in their own language, gives no name, needs no
  literacy, no smartphone skill and no form. Gets a real course code, the local
  seat count, and the assistance they can claim —
  **"up to ₹50,000 or 50% of project cost, whichever is less."**
- **District officer:** a live map of what people in their district actually
  want, a gap panel showing aspirations with **no local training supply** (the
  procurement signal), and a one-click **AAP annexure** — the exact artefact the
  Annual Action Plan needs, grouped by GIA domain.
- **Ministry:** faster beneficiary-level project formation against the
  **₹736.28 cr / ₹2,140 cr** absorption gap; mandate tracking built into the
  export — **≥30% women participation**, **≥15% women-income earmark**,
  **≥10% skilling floor**, priority to families at **≤₹2.5 lakh** annual income.
- **Compliance, not vibes:** every export carries a compliance sheet with the
  mandate, the measured value, whether it is met, and the citation.
- **Equity by design:** gender **boosts** eligibility scoring, it never filters;
  a capability ceiling derived from education keeps recommendations reachable,
  with a documented stretch relaxation instead of an empty result.

**KPIs worth naming:** beneficiaries mapped per officer-day · AAP cycle-time
reduction · % women captured against the 30% mandate · aspirations with zero
local supply (the gap the officer can act on).

---

## Slide 6 — Research & References

Primary sources only. Everything cited here is in `research.md` with its
verification mark.

1. **PM-AJAY Guidelines (May 2023 Revised)** — Ch. 3 §7.A.a.iv (the mandate we
   automate); the 43-page PDF is ingested and chunked in the system.
   `pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf`
2. **Union Budget / DoSJE expenditure** — Actual FY2024-25 **₹736.28 cr** vs BE
   **₹2,140 cr**; RE 2025-26 **₹1,250 cr** (−41.6%).
3. **NCVET Kaushalverse** — qualification API; **1,170** qualifications
   ingested, `nco_code` populated on **0 of 1,170**, **268 of 1,170 (22.9%)**
   carrying NSQF half-levels.
4. **LGD district master** — **785** districts, the district spine.
5. **Vistaar / IndicWhisper benchmark** — Hindi average WER **13.6%**;
   **26.8% WER** on the GramVaani rural-Hindi set; per-language spread hi 13.6 /
   mr 18.2 / te 28.8. IndicASR: Hindi 15.0, Marathi 18.2, Telugu 26.8.
6. **Farmer.Chat** (agri voice assistant, India) — the latency precedent we
   budget against (**9.05 s average**) and the evidence that suggestion buttons
   carry >45% of interactions.
7. **DPDP Act 2023** — consent and data-minimisation posture; Rule 3 itemised
   notice. Our consent record is in-system by design.
8. **Bhashini / Sarvam rate cards** — the <₹2-per-conversation arithmetic.

Project repository: README → `docs/decisions.md` (46 recorded decisions),
`docs/ingest-report.md` (what is real, what is synthetic),
`docs/crosswalk-method.md` (how the join table was built and validated),
`docs/runbook.md` (venue procedure).

---

## Delivery checklist for the deck

- [ ] Export to **PDF** (the portal accepts nothing else).
- [ ] **6 slides, not 7.** The title slide counts.
- [ ] Bullets and diagrams only — **no paragraphs**.
- [ ] Slide 2 states the novelty in so many words.
- [ ] Slide 3 names concrete languages and frameworks and carries the flow
      diagram.
- [ ] Every number on the deck traced to research.md or to a command in this
      repository. **If a figure cannot be traced, cut it.**
- [ ] The synthetic-data caveat appears on the deck, not only in the demo.
