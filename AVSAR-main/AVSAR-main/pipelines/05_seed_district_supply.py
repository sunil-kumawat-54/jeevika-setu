"""Pipeline 05 — district training-centre supply.

PLAN.md section 5.1:
    05 | seed_district_supply.py | synthetic-but-plausible district
       centre/course-availability table (clearly labelled SYNTHETIC in UI footer
       until real data via MoU) | centre_supply(district, qp_code, seats,
       centre_name) | Honesty label matters for judges; roadmap slide = replace
       via SIDH/NCS MoU

This table is synthetic **by design, not by failure**. research.md section 4.3
establishes why no real substitute exists today:

* NSDC District Wise Skill Gap Studies are district x sector x skill-band —
  *"not job-role/QP level"* — with no index and no API.
* SANKALP District Skill Development Plans are not bulk-downloadable.
* NCS publishes **zero** open datasets; DGE states its web services only
  inter-link state exchanges.
* SIDH exposes ``/sectors`` and ``/jobs`` openly, but research.md section 7.2
  records that *"the course-listing route could not be found"*.

So ``centre_supply.synthetic`` defaults to TRUE in the schema, every row written
here sets it true, and the dashboard renders a visible synthetic badge. Nothing
in this file may ever be described as real government supply data.

The generator is seeded deterministically, so re-running ``make ingest`` gives a
byte-identical snapshot (idempotency).
"""

from __future__ import annotations

import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pipelines.common import (  # noqa: E402
    SEEDS,
    PipelineResult,
    Provenance,
    read_seed,
    record_run,
    stable_rng,
    write_seed,
)

log = logging.getLogger("05_supply")

NAME = "05_seed_district_supply"
SEED_PATH = SEEDS / "centre_supply.json"
DISTRICTS_SEED = SEEDS / "districts.json"
COURSES_SEED = SEEDS / "pmajay_courses.json"

#: The five districts the demo is built around (PLAN.md section 5.1 pipeline 07:
#: "25 synthetic beneficiary sessions spread over 5 districts").
DEMO_DISTRICT_NAMES = ("Latur", "Nanded", "Varanasi", "Nalgonda", "Gaya")

#: Centre-name templates mirroring the real institutional mix a district has.
CENTRE_KINDS = (
    "{d} District Skill Centre",
    "{d} ITI",
    "PMKVY Training Centre, {d}",
    "{d} Rural Self Employment Training Institute",
    "{d} Women's Skill Hub",
    "Common Service Centre, {d}",
)

#: Courses offered per demo district, and per other district. Demo districts get
#: deeper supply so the dashboard's gap panel has something to show on both sides.
DEMO_QP_PER_DISTRICT = 90
OTHER_QP_PER_DISTRICT = 12
#: How many districts outside the demo five get any supply at all. Keeping this
#: bounded stops a 785-district cross-product from dwarfing the real catalogue.
OTHER_DISTRICT_COUNT = 45


def _crosswalk_qp_codes() -> set[str]:
    """QP codes the curated crosswalk actually maps aspirations to."""
    import sys as _sys

    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services"))
    try:
        from core.domain.crosswalk_schema import load_dir
    except ImportError:
        return set()
    try:
        rows = load_dir(pathlib.Path(__file__).resolve().parents[1] / "data" / "crosswalk")
    except Exception as exc:  # a malformed crosswalk is pipeline 04's failure to report
        log.warning("could not read crosswalk for supply seeding: %s", exc)
        return set()
    return {code for row in rows for code in row.qp_codes}


def run() -> PipelineResult:
    _, districts = read_seed(DISTRICTS_SEED)
    _, courses = read_seed(COURSES_SEED)

    prov = Provenance(
        pipeline=NAME,
        source_url="synthetic (no real district x QP supply dataset is published)",
        mode="synthetic",
        synthetic=True,
        fallback_note=(
            "centre_supply is synthetic BY DESIGN, not because a fetch failed. "
            "research.md 4.3: NSDC skill-gap studies stop at sector x skill-band, "
            "SANKALP DSDPs are not bulk-downloadable, NCS publishes no open data, "
            "and SIDH's course-listing route is undiscovered. Every row sets "
            "synthetic=true and the dashboard renders a visible badge. Replacing "
            "this table with a real SIDH/State-Mission extract is the Q1 roadmap "
            "item in PLAN.md 13."
        ),
    )

    if not districts or not courses:
        prov.failure_reason = "districts or courses seed missing — run pipelines 00-03 first"
        write_seed(SEED_PATH, [], prov)
        return PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)

    by_name = {d["name_en"]: d for d in districts}
    demo = [by_name[n] for n in DEMO_DISTRICT_NAMES if n in by_name]
    demo_codes = {d["code"] for d in demo}

    # Deterministic choice of the "other" districts: the first N by code that
    # are not demo districts.
    others = [d for d in sorted(districts, key=lambda x: x["code"]) if d["code"] not in demo_codes]
    others = others[:OTHER_DISTRICT_COUNT]

    qp_codes = sorted({c["qp_code"] for c in courses if c.get("qp_code")})
    if not qp_codes:
        prov.failure_reason = "course seed has no qp_codes"
        write_seed(SEED_PATH, [], prov)
        return PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)

    # A district's training centres teach the trades people actually ask for, so
    # a synthetic supply table that samples the catalogue uniformly is a poor
    # model of reality: it left Latur — the scripted demo district — with no
    # tailoring seats at all, which then let an unrelated course with seats
    # outrank the right one. Demo districts therefore stock a deterministic
    # majority of the CURATED trades (the ones the crosswalk knows about), plus
    # a random tail from the wider catalogue. Coverage is intentionally partial
    # so the dashboard's gap panel still has real district-level gaps to show.
    curated_codes = sorted(_crosswalk_qp_codes())
    coverage = {}

    rows: list[dict] = []
    for district, depth in [(d, DEMO_QP_PER_DISTRICT) for d in demo] + [
        (d, OTHER_QP_PER_DISTRICT) for d in others
    ]:
        rng = stable_rng(f"avsar-supply-{district['code']}")
        picks: list[str] = []
        if district["code"] in demo_codes and curated_codes:
            # ~75% of curated trades per demo district, deterministic per district.
            take = max(1, int(len(curated_codes) * 0.75))
            picks.extend(rng.sample(curated_codes, k=min(take, len(curated_codes))))
        remaining = [c for c in qp_codes if c not in set(picks)]
        extra = max(0, depth - len(picks))
        if extra and remaining:
            picks.extend(rng.sample(remaining, k=min(extra, len(remaining))))
        coverage[district["name_en"]] = len(picks)

        for qp_code in sorted(set(picks)):
            centre = rng.choice(CENTRE_KINDS).format(d=district["name_en"])
            rows.append(
                {
                    "district_code": district["code"],
                    "qp_code": qp_code,
                    "centre_name": centre,
                    "seats": rng.choice([15, 20, 25, 30, 35, 40, 50, 60]),
                    "synthetic": True,
                }
            )

    # centre_supply(district_code, qp_code, centre_name) is UNIQUE.
    seen: set[tuple] = set()
    unique = []
    for row in sorted(rows, key=lambda r: (r["district_code"], r["qp_code"], r["centre_name"])):
        key = (row["district_code"], row["qp_code"], row["centre_name"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    prov.notes = [
        f"{len(curated_codes)} curated QP codes; demo districts stock ~75% of them "
        f"so the trades beneficiaries actually ask for have local seats",
        f"per-district QP counts: {coverage}",
        f"{len(demo)} demo districts at up to {DEMO_QP_PER_DISTRICT} QPs each",
        f"{len(others)} further districts at up to {OTHER_QP_PER_DISTRICT} QPs each",
        f"{len(unique)} unique (district, qp_code, centre) rows, all synthetic=true",
        "Deterministically generated — re-running produces a byte-identical snapshot.",
    ]
    for note in prov.notes:
        log.info(note)

    write_seed(SEED_PATH, unique, prov)
    canonical_version = prov.source_version or "synthetic-2026-09"
    centre_rows: list[dict] = []
    programme_rows: list[dict] = []
    seen_centres: set[tuple[str, str]] = set()
    for row in unique:
        centre_key = (row["district_code"], row["centre_name"])
        centre_id = f"{row['district_code']}:{row['centre_name']}"
        if centre_key not in seen_centres:
            seen_centres.add(centre_key)
            centre_rows.append(
                {
                    "district_code": row["district_code"],
                    "centre_name": row["centre_name"],
                    "coordinate_status": "synthetic",
                    "source_name": NAME,
                    "source_version": canonical_version,
                    "source_record_id": centre_id,
                    "synthetic": True,
                }
            )
        programme_rows.append(
            {
                "centre_source_record_id": centre_id,
                "qp_code": row["qp_code"],
                "programme_type": "training",
                "title": f"{row['qp_code']} training at {row['centre_name']}",
                "seats": row["seats"],
                "source_name": NAME,
                "source_version": canonical_version,
                "source_record_id": f"{row['district_code']}:{row['centre_name']}:{row['qp_code']}",
                "synthetic": True,
            }
        )
    canonical_prov = Provenance(
        pipeline=NAME,
        source_url=prov.source_url,
        mode="synthetic",
        source_name=NAME,
        source_version=canonical_version,
        synthetic=True,
        fallback_note=prov.fallback_note,
        notes=[
            "Canonical training-centre/programme rows are derived from centre_supply.",
            "No coordinates are generated from district aggregates; coordinate_status=synthetic.",
        ],
    )
    write_seed(SEEDS / "training_centres.json", centre_rows, canonical_prov)
    write_seed(SEEDS / "programmes.json", programme_rows, canonical_prov)
    result = PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)
    record_run(result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
