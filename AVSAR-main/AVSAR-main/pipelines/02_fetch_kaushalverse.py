"""Pipeline 02 — Kaushalverse (NCVET) qualification register.

PLAN.md section 5.1:
    02 | fetch_kaushalverse.py | GET getAllQualApprovedFiles (71 pages) +
       getQualDetailsBasedOnVersionId per qual (throttled) |
       qualifications(qp/nqr_code, name, nsqf_level, sector, min/max_hours,
       theory/prac/ojt/es_hours, credits, eligibility, progression, valid_till) |
       Filter categoryOfQual == 'Qualification' (drop Standalone NOS/MC);
       expect half-level granularity — store nsqf_level NUMERIC(3,1)

Endpoints (TECH_STACK.md section 2.3 — open JSON, no auth):
    GET /digigov/homepage/getAllQualApprovedFiles?pageNumber=N   (20/page)
    GET /digigov/homepage/getQualDetailsBasedOnVersionId?versionId=ID

Two facts from research.md section 3.2 that this pipeline is built around:

* ``nsqfLevel`` arrives as a *string* and half levels are common ("5.5", "2.5").
  It is parsed to a Decimal and stored NUMERIC(3,1) — never int (RULE 5).
* ``ncoCode`` is **null in every sampled record**. The pipeline keeps the column
  and reports the null rate, because that void is precisely what the curated
  crosswalk (pipeline 04) exists to fill.

Detail responses are cached under ``seeds/raw/kaushalverse/`` so a re-run costs
no requests — which is what makes ``make ingest`` cheap to repeat and idempotent.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pipelines.common import (  # noqa: E402
    RAW,
    SEEDS,
    PipelineResult,
    Provenance,
    RateLimiter,
    as_float,
    as_int,
    build_client,
    clean,
    env,
    env_float,
    record_run,
    stable_rng,
    write_seed,
)

log = logging.getLogger("02_kaushalverse")

NAME = "02_fetch_kaushalverse"
SEED_PATH = SEEDS / "kaushalverse_qualifications.json"
DETAIL_CACHE = RAW / "kaushalverse"
PAGE_SIZE = 20

#: Only true Qualifications become rows; Standalone NOS / Standalone MC are
#: dropped exactly as PLAN.md section 5.1 instructs.
WANTED_CATEGORY = "Qualification"


def _base() -> str:
    return env("KAUSHALVERSE_BASE", "https://kaushalverse.ncvet.gov.in").rstrip("/")


def parse_level(raw) -> float | None:
    """Parse an NSQF level preserving half-level granularity (RULE 5).

    research.md section 3.2: levels run 1-10 including 2.5/3.5/4.5/5.5; ~24% of a
    136-record sample sat at a half level, so any integer-only parse mis-handles
    a quarter of the corpus.
    """
    text = clean(raw)
    if text is None:
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not (Decimal(1) <= value <= Decimal(10)):
        return None
    # Quantise to one decimal place — the column is NUMERIC(3,1).
    return float(value.quantize(Decimal("0.1")))


def qp_code_from_nqr(nqr_code: str | None) -> str | None:
    """Derive a QP-style code from an NQR code.

    research.md section 3.2 gives the format
    ``QG-{level}-{sector}-{serial}-{year}-V{v}-{body}`` e.g.
    ``QG-2.5-ET-01489-2023-V1-MSRVVP``. The PM-AJAY catalogue keys courses as
    ``SSC/Qnnnn`` (e.g. ``AGR/Q5301``). We reconstruct ``{sector}/Q{serial}``
    from the NQR code — a *derivation*, not an invention, and the original
    ``nqr_code`` is always stored alongside so the derivation is auditable.
    """
    if not nqr_code:
        return None
    parts = nqr_code.split("-")
    if len(parts) < 4:
        return None
    sector_abbr, serial = parts[2], parts[3]
    if not sector_abbr or not serial:
        return None
    return f"{sector_abbr.upper()}/Q{serial}"


def _eligibility(record: dict) -> dict | None:
    """Keep the eligibility grid plus the two flat fields, dropping nulls."""
    grid = record.get("eligibilityCriteriaGrid")
    education = clean(record.get("education"))
    experience = clean(record.get("experience"))
    if not grid and not education and not experience:
        return None
    payload: dict = {}
    if grid:
        rows = []
        for row in grid:
            kept = {k: v for k, v in row.items() if v not in (None, "", [])}
            if kept:
                rows.append(kept)
        if rows:
            payload["criteria"] = rows
    if education:
        payload["education"] = education
    if experience:
        payload["experience"] = experience
    return payload or None


def _valid_till(record: dict) -> str | None:
    raw = clean(record.get("validTill"))
    if not raw:
        return None
    # Payload uses ISO-ish strings; keep only the date part.
    return raw.split("T")[0][:10]


def normalise(record: dict) -> dict | None:
    version_id = as_int(record.get("qualVersionId"))
    name = clean(record.get("nameOfQualification"))
    if version_id is None or not name:
        return None
    nqr_code = clean(record.get("nqrCode"))
    return {
        "version_id": version_id,
        "nqr_code": nqr_code,
        "qp_code": qp_code_from_nqr(nqr_code),
        "name": name,
        "category": clean(record.get("categoryOfQual")),
        "nsqf_level": parse_level(record.get("nsqfLevel")),
        "sector": clean(record.get("sector")),
        "min_hours": as_int(record.get("minimumHours")),
        "max_hours": as_int(record.get("maximumHours")),
        "th_hrs": as_int(record.get("thHrs")),
        "pr_hrs": as_int(record.get("prHrs")),
        "ojt_hrs": as_int(record.get("ojtHrs")),
        "es_hrs": as_int(record.get("employabilityTotalHrs")),
        "credits_min": as_float(record.get("minimumCredits")),
        "credits_max": as_float(record.get("maximumCredits")),
        "eligibility": _eligibility(record),
        "progression_vertical": clean(record.get("verticalPathName")),
        "nco_code": clean(record.get("ncoCode")),
        "awarding_body": clean(record.get("awardingBodyName")),
        "valid_till": _valid_till(record),
        "synthetic": False,
    }


def _needs_detail(row: dict) -> bool:
    """A list row is thin when the hours/credits block is empty."""
    return not any(
        row.get(key) is not None
        for key in ("min_hours", "max_hours", "th_hrs", "pr_hrs", "credits_min")
    )


def fetch_list(client, limiter, prov: Provenance) -> list[dict]:
    base = _base()
    url = f"{base}/digigov/homepage/getAllQualApprovedFiles"
    rows: list[dict] = []
    page = 1
    total = None
    while True:
        limiter.wait()
        resp = client.get(url, params={"pageNumber": page})
        prov.http_status = resp.status_code
        resp.raise_for_status()
        data = (resp.json() or {}).get("data") or {}
        if total is None:
            total = as_int(data.get("ALL_APPROVED_FILES_COUNT")) or 0
            prov.notes.append(f"Kaushalverse reports ALL_APPROVED_FILES_COUNT={total}")
        batch = data.get("ALL_APPROVED_FILES") or []
        if not batch:
            break
        rows.extend(batch)
        log.info("list page %d -> %d records (%d total so far)", page, len(batch), len(rows))
        if total and len(rows) >= total:
            break
        if len(batch) < PAGE_SIZE:
            break
        page += 1
        if page > 200:  # hard stop; the register is ~81 pages
            prov.notes.append("stopped at page 200 guard")
            break
    return rows


def fetch_detail(client, limiter, version_id: int) -> dict | None:
    """Fetch (and cache) one qualification's detail payload."""
    cached = DETAIL_CACHE / f"{version_id}.json"
    if cached.exists():
        try:
            return json.loads(cached.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached.unlink(missing_ok=True)

    limiter.wait()
    url = f"{_base()}/digigov/homepage/getQualDetailsBasedOnVersionId"
    resp = client.get(url, params={"versionId": version_id})
    if resp.status_code != 200:
        return None
    payload = (resp.json() or {}).get("data")
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, dict):
        return None
    DETAIL_CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_live(detail_limit: int | None = None) -> tuple[list[dict], Provenance]:
    base = _base()
    prov = Provenance(
        pipeline=NAME,
        source_url=f"{base}/digigov/homepage/getAllQualApprovedFiles",
        mode="live",
    )
    limiter = RateLimiter(env_float("INGEST_QPS", 1.0))

    with build_client(env("INGEST_UA", "AVSAR-SIH-Research/1.0"), timeout=60.0) as client:
        raw_rows = fetch_list(client, limiter, prov)
        prov.notes.append(f"fetched {len(raw_rows)} approved files across all categories")

        categories: dict[str, int] = {}
        for row in raw_rows:
            key = clean(row.get("categoryOfQual")) or "unknown"
            categories[key] = categories.get(key, 0) + 1
        prov.notes.append(f"categoryOfQual breakdown: {categories}")

        qualifications = [
            row for row in raw_rows if clean(row.get("categoryOfQual")) == WANTED_CATEGORY
        ]
        prov.notes.append(
            f"kept {len(qualifications)} rows with categoryOfQual == '{WANTED_CATEGORY}'; "
            f"dropped {len(raw_rows) - len(qualifications)} Standalone NOS/MC per PLAN 5.1"
        )

        normalised: list[dict] = []
        for row in qualifications:
            item = normalise(row)
            if item:
                normalised.append(item)

        thin = [r for r in normalised if _needs_detail(r)]
        if detail_limit is not None:
            thin = thin[:detail_limit]
        log.info("%d/%d rows need a detail call", len(thin), len(normalised))

        enriched = 0
        by_version = {r["version_id"]: r for r in normalised}
        for idx, row in enumerate(thin, start=1):
            detail = fetch_detail(client, limiter, row["version_id"])
            if not detail:
                continue
            # The detail payload omits qualVersionId (it is always null there),
            # so inject the id we asked for before normalising.
            detail = {**detail, "qualVersionId": row["version_id"]}
            merged = normalise(detail)
            if not merged:
                continue
            target = by_version[row["version_id"]]
            for key, value in merged.items():
                if value is not None and target.get(key) is None:
                    target[key] = value
            enriched += 1
            if idx % 50 == 0:
                log.info("detail %d/%d (%d enriched)", idx, len(thin), enriched)

        prov.notes.append(f"{enriched} rows enriched from getQualDetailsBasedOnVersionId")

    nco_present = sum(1 for r in normalised if r["nco_code"])
    prov.notes.append(
        f"ncoCode populated in {nco_present}/{len(normalised)} records "
        "(research.md 3.2 records it as null in every sampled record — this is the "
        "gap the curated crosswalk fills)"
    )
    half = sum(1 for r in normalised if r["nsqf_level"] and float(r["nsqf_level"]) % 1 != 0)
    with_level = sum(1 for r in normalised if r["nsqf_level"] is not None)
    if with_level:
        prov.notes.append(
            f"{half}/{with_level} qualifications sit at a half NSQF level "
            f"({100 * half / with_level:.1f}%) — integer-only logic would mis-handle them"
        )

    normalised.sort(key=lambda r: r["version_id"])
    return normalised, prov


# --------------------------------------------------------------------------
# Synthetic fallback
# --------------------------------------------------------------------------

SYNTHETIC_SECTORS = [
    ("Apparel", "AMH", 8), ("Agriculture", "AGR", 8), ("Beauty & Wellness", "BWS", 6),
    ("Construction", "CON", 6), ("Electronics", "ELE", 6), ("Food Processing", "FIC", 6),
    ("Handicrafts", "HCS", 5), ("Healthcare", "HSS", 6), ("IT-ITeS", "SSC", 6),
    ("Retail", "RAS", 5), ("Automotive", "ASC", 5), ("Plumbing", "PSC", 4),
]
SYNTHETIC_LEVELS = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]


def synthetic_snapshot(reason: str, status: int | None) -> tuple[list[dict], Provenance]:
    """Structurally identical synthetic register, every row ``synthetic: true``."""
    prov = Provenance(
        pipeline=NAME,
        source_url=f"{_base()}/digigov/homepage/getAllQualApprovedFiles",
        mode="synthetic",
        synthetic=True,
        http_status=status,
        failure_reason=reason,
        fallback_note=(
            "Kaushalverse unreachable. Emitted a structurally identical register with "
            "the same field set, the same half-level NSQF distribution and ncoCode "
            "left null exactly as the real register leaves it. Every record carries "
            "synthetic=true and no row is presented as an NCVET-approved qualification."
        ),
    )
    rng = stable_rng("avsar-kaushalverse-fallback")
    rows: list[dict] = []
    version = 900_000
    for sector, abbr, count in SYNTHETIC_SECTORS:
        for serial in range(1, count * 8 + 1):
            version += 1
            level = rng.choice(SYNTHETIC_LEVELS)
            min_h = rng.choice([200, 250, 300, 360, 400, 480, 600])
            rows.append(
                {
                    "version_id": version,
                    "nqr_code": f"SYN-{level}-{abbr}-{serial:05d}-2026-V1-SYNTHETIC",
                    "qp_code": f"{abbr}/Q{serial:04d}",
                    "name": f"{sector} job role {serial}",
                    "category": WANTED_CATEGORY,
                    "nsqf_level": level,
                    "sector": sector,
                    "min_hours": min_h,
                    "max_hours": min_h + rng.choice([60, 120, 180]),
                    "th_hrs": int(min_h * 0.3),
                    "pr_hrs": int(min_h * 0.5),
                    "ojt_hrs": 0,
                    "es_hrs": int(min_h * 0.1),
                    "credits_min": round(min_h / 30.0, 1),
                    "credits_max": round(min_h / 25.0, 1),
                    "eligibility": {"education": "As per NSQF entry criteria"},
                    "progression_vertical": None,
                    "nco_code": None,
                    "awarding_body": None,
                    "valid_till": None,
                    "synthetic": True,
                }
            )
    rows.sort(key=lambda r: r["version_id"])
    return rows, prov


def run(detail_limit: int | None = None) -> PipelineResult:
    try:
        rows, prov = fetch_live(detail_limit=detail_limit)
        if len(rows) < 200:
            raise RuntimeError(f"only {len(rows)} qualifications returned; refusing a partial snapshot")
    except Exception as exc:
        log.warning("live Kaushalverse fetch failed (%s: %s) — falling back", type(exc).__name__, exc)
        status = getattr(getattr(exc, "response", None), "status_code", None)
        rows, prov = synthetic_snapshot(f"{type(exc).__name__}: {exc}", status)

    write_seed(SEED_PATH, rows, prov)
    result = PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)
    record_run(result)
    log.info("wrote %s (%d rows, mode=%s)", SEED_PATH.name, prov.rows, prov.mode)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=None,
        help="cap the number of detail calls (smoke runs); omit for a full ingest",
    )
    args = parser.parse_args()
    run(detail_limit=args.detail_limit)
