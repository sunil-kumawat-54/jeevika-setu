# docs/crosswalk-method.md — how the aspiration↔QP crosswalk was built

> One-pager for the SIH **Research & References** slide (PLAN.md §5.2).

## 1. Why this artifact has to exist

The problem statement implies a chain:

```
spoken aspiration  →  occupation concept  →  NCO-2015 code  →  NSQF-aligned QP  →  nearby centre
```

**The middle link is not published anywhere.** research.md §3.3 establishes it,
and this repository's own ingestion confirms it at full-corpus scale:

| Register | What it publishes | NCO link? |
|---|---|---|
| NCVET **Kaushalverse** | 1,170 approved Qualifications with hours, credits, eligibility, progression | `ncoCode` is **null in 0 / 1,170** records — verified by `pipelines/02_fetch_kaushalverse.py` |
| **NQR** (legacy) | Server-rendered qualification pages | "Proposed Occupation" is free text, frequently "N/A" |
| **NCS** | Nine broad sectors | No NCO taxonomy at all; no public API (research.md §7.2) |
| **PM-AJAY** GIA catalogue | ~2,360 QP-coded courses | No NSQF level field, no NCO field (research.md §3.4) |

So the join table is the contribution. We are not apologising for hand-building
it — we are **publishing the missing join table**, versioned and reviewable.

## 2. Method

```
   ┌──────────────────────┐
   │ 10 GIA domains       │  research.md §2.4 (= Annexure-I of the guidelines)
   │ (controlled vocab)   │
   └──────────┬───────────┘
              │  define concepts inside each domain
              ▼
   ┌──────────────────────┐     ┌────────────────────────────┐
   │ colloquial phrases   │     │ real NCVET qualifications  │
   │ hi · mr · te · en    │     │ seeds/kaushalverse_*.json  │
   └──────────┬───────────┘     └──────────────┬─────────────┘
              │                                │
              │   candidate generation         │
              │   (semantic + keyword)         │
              └──────────────┬─────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │  HUMAN REVIEW       │  status: auto → reviewed
                  │  second-member sign │  (peer-review protocol, PLAN.md §5.2)
                  └──────────┬──────────┘
                             ▼
                  data/crosswalk/*.yaml   →  pipeline 04  →  crosswalk table
                                                          →  qp_descriptions index
```

### Step 1 — Fix the vocabulary
Concepts live inside the **exactly ten** GIA domains of the illustrative list
(research.md §2.4). The schema enforces `CHECK (gia_domain BETWEEN 1 AND 10)`,
so a typo cannot invent an eleventh domain.

### Step 2 — Author phrases the way people actually speak
Each concept carries colloquial phrases in **hi, mr, te and en** — not
dictionary translations of the job-role title. `"कपड़ा सिलना"`, `"बुटीक खोलना है"`
and `"दर्जी का काम"` all reach `tailoring`, because that is what beneficiaries
say. This is the design response to research.md §5.1: rural-telephony ASR is
measured at **26.8% WER** even for the best Indic model, so the crosswalk has to
absorb variation rather than assume a clean transcript.

### Step 3 — Candidate QPs, then human sign-off
Candidates come from keyword and embedding search over the real register; a
person then accepts, fixes or rejects each one. Only `status: reviewed` entries
ship — `services/core/tests/test_gate3_crosswalk.py::test_entries_are_peer_reviewed`
fails the build otherwise. Every `qp_code` is checked to exist in `courses`, so
a crosswalk row can never point at an invented qualification.

### Step 4 — Embed, and make the index multilingual
`pipelines/04_build_crosswalk.py` embeds with **multilingual-e5-base on CPU**
(TECH_STACK §1) into two pgvector indexes:

* `crosswalk.embedding` — the phrase vectors;
* `qp_descriptions.embedding` — one vector per course.

**The QP description text deliberately includes the curated phrases** for that
QP in all four languages. This is load-bearing and was driven by a measurement,
not a hunch. With English-only descriptions, the query
`"मैं सिलाई का काम सीखना चाहती हूँ"` retrieved *Bijli mistry* and *Safai Mitra*
ahead of any sewing QP, with every cosine squeezed into 0.77–0.80. After folding
the aliases in, the same query returns:

```
0.8173  AP/Q01866  L2.5  Sewing Machine Operator
0.8149  AP/Q01867  L2.5  Sewing Machine Operator - Knits
0.8075  AP/Q03425  L3.0  Garment Maker
```

## 3. What ships today

| Metric | Value |
|---|---|
| Phrase rows (`crosswalk` table) | **411** |
| Concepts | **33** |
| GIA domains covered | **10 / 10** |
| Distinct real QP codes referenced | **83** |
| Languages per concept | 4 (hi, mr, te, en) |
| Review status | 100% `reviewed` |
| Declared coverage gaps | 1 (`poultry`) |

## 4. Declared gaps — and why we declare them

A crosswalk entry may carry **`qp_codes: []`** only if it also carries a
`gap_reason`; the validator rejects it otherwise.

`poultry` is currently a declared gap. There is no poultry qualification
anywhere in the ingested register (0 matches for poultry / broiler / hatchery /
layer across all 1,170 approved Qualifications) because the PM-AJAY portal was
serving its maintenance page during ingestion — see `docs/ingest-report.md`.

We could have pointed `"मुर्गी पालन"` at *Goat and Sheep Farmer*. We did not,
because a confident recommendation of the wrong trade is worse than an honest
"I don't have that". A declared gap instead:

1. falls through to semantic recall, then to **refusal / officer handoff**; and
2. surfaces in the officer dashboard's **gap panel** as demand with no local
   supply — which is precisely the signal PLAN.md §4.2 designed that panel to
   carry.

The gap closes automatically the moment pipeline 01 can reach the live
catalogue; no code change is needed.

## 5. Maintenance

The crosswalk is a living artifact:

* **Authoring** — edit `data/crosswalk/*.yaml`, run `make ingest`. Malformed
  YAML fails loudly (Gate 3 rejects 16 distinct malformation classes in test).
* **Review UI** — `/admin` exposes the crosswalk review table; every accept/fix
  writes an `audit_log` row with before/after (ARCHITECTURE §9).
* **Re-embedding** — `POST /admin/reembed` rebuilds the vector index after
  edits, so a reviewer's change takes effect without a redeploy.
* **Versioning** — each entry carries `version`, and `crosswalk(phrase, lang)`
  is UNIQUE, so a phrase cannot be defined twice with different mappings.

## 6. Honest limitations

- **Coverage is v0.** 33 concepts is a demo-grade vocabulary, not a national
  one. PLAN.md §5.2 sets the stretch target at 300 phrase rows; we are at 411
  rows but only 33 concepts.
- **No NCO-2015 codes are asserted.** We map aspiration → QP directly. Claiming
  an NCO code we cannot source would be exactly the fabrication this project
  refuses; DGE's NCO-2015 volumes are manual-download PDFs (research.md §3.3).
- **The QP universe is the fallback catalogue.** Because PM-AJAY was
  unavailable, `courses` holds 1,135 rows derived from real NCVET identities
  rather than the real ~1,893-QP GIA catalogue. Crosswalk coverage will widen
  when the portal returns.
- **Semantic recall is an aid, not the decision.** The LLM never picks courses;
  the deterministic scorer does (PLAN.md §6). Embeddings only widen the
  candidate set.
