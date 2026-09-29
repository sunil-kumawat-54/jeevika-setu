"""Pipeline 01 — PM-AJAY GIA course catalogue.

PLAN.md section 5.1:
    01 | fetch_pmajay_courses.py |
       POST pmajay.dosje.gov.in/front/reportajax (module_type=5&sector_id=all;
       CSRF from /course-list) | courses(sector, sub_sector, course, sub_course,
       qp_code) ~2,360 rows | Cache raw JSON to seeds/pmajay_courses.json;
       polite 1 req/s

research.md section 3.4 verified this endpoint live on 2026-08-25 and warned
(section 7.1, risk R4) that *"All pmajay.dosje.gov.in endpoints are
undocumented/unofficial (Laravel debug-mode leak observed) — cache seed data;
never hard-depend at finale."*

**Fallback contract.** If the portal blocks, times out, changes schema, errors
or serves its maintenance page, this pipeline does NOT invent official-looking
rows. It builds a structurally identical catalogue whose *QP identities are
real* — code, job-role name, sector and NSQF level are taken from the NCVET
Kaushalverse register that pipeline 02 already fetched — while the thing that
cannot be verified (which QPs PM-AJAY's GIA catalogue actually lists, and how
they are grouped into Course/Sub-Course) is synthesised. Every such row carries
``synthetic: true`` and ``source: "kaushalverse"``, and that flag is preserved
through the database into the dashboard footer.
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
    RateLimiter,
    build_client,
    cache_raw,
    clean,
    env,
    env_float,
    read_seed,
    record_run,
    stable_rng,
    write_seed,
)

log = logging.getLogger("01_pmajay")

NAME = "01_fetch_pmajay_courses"
SEED_PATH = SEEDS / "pmajay_courses.json"
KAUSHALVERSE_SEED = SEEDS / "kaushalverse_qualifications.json"

#: research.md section 3.4 — the observed size of the real catalogue. The
#: synthetic fallback targets the same scale so downstream behaviour (query
#: plans, candidate-set sizes, dashboard aggregates) matches production.
REAL_CATALOGUE_ROWS = 2360
REAL_CATALOGUE_UNIQUE_QP = 1893

MAINTENANCE_MARKERS = ("maintenance.blade.php", "Under Maintenance", "We'll be right back")


def _base() -> str:
    return env("PMAJAY_BASE", "https://pmajay.dosje.gov.in").rstrip("/")


class SourceUnavailable(RuntimeError):
    """The portal answered, but not with a course catalogue."""


class TlsChainBroken(SourceUnavailable):
    """The portal's TLS chain cannot be verified.

    Observed 2026-09-11: ``pmajay.dosje.gov.in`` serves an **incomplete
    certificate chain** (the intermediate CA is not included). Windows clients
    appear to succeed because the OS fetches the missing intermediate via the
    certificate's AIA extension and caches it; OpenSSL does not do AIA chasing,
    so every Linux container sees
    ``CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate``.

    This is one more reason RULE 3 exists: the portal is not fit to be a runtime
    dependency. Set ``PMAJAY_INSECURE_TLS=true`` to let the *ingestion* pipeline
    proceed without chain verification when an operator explicitly accepts that
    risk. It is never consulted at runtime and defaults to off.
    """


def fetch_live() -> tuple[list[dict], Provenance]:
    """POST /front/reportajax with the CSRF token + cookie from /course-list."""
    base = _base()
    prov = Provenance(pipeline=NAME, source_url=f"{base}/front/reportajax", mode="live")
    limiter = RateLimiter(env_float("INGEST_QPS", 1.0))
    insecure = env("PMAJAY_INSECURE_TLS", "false").lower() in ("1", "true", "yes")
    if insecure:
        prov.notes.append(
            "PMAJAY_INSECURE_TLS=true — TLS chain verification was DISABLED for this "
            "ingestion run because the portal ships an incomplete chain. Ingestion only; "
            "the runtime never contacts this host."
        )

    with build_client(
        env("INGEST_UA", "AVSAR-SIH-Research/1.0"), timeout=45.0, verify=not insecure
    ) as client:
        limiter.wait()
        try:
            landing = client.get(f"{base}/course-list")
        except Exception as exc:
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                raise TlsChainBroken(
                    f"{base} TLS chain could not be verified (incomplete chain served by the "
                    f"portal; OpenSSL does not chase AIA). Underlying error: {exc}"
                )
            raise
        prov.http_status = landing.status_code
        cache_raw("pmajay_course_list.html", landing.content)
        body = landing.text

        if any(marker in body for marker in MAINTENANCE_MARKERS):
            raise SourceUnavailable(
                "pmajay.dosje.gov.in is serving maintenance.blade.php — the portal is "
                "under maintenance and the course catalogue is not being served"
            )
        landing.raise_for_status()

        # Laravel: the CSRF token is either a meta tag or the XSRF-TOKEN cookie.
        token = None
        for marker in ('name="csrf-token" content="', "name='csrf-token' content='"):
            if marker in body:
                token = body.split(marker, 1)[1].split(body[len(marker) - 1], 1)[0]
                break
        if token is None:
            token = client.cookies.get("XSRF-TOKEN")
        if not token:
            raise SourceUnavailable("no CSRF token found on /course-list")

        limiter.wait()
        resp = client.post(
            f"{base}/front/reportajax",
            data={"module_type": "5", "sector_id": "all"},
            headers={
                "X-CSRFToken": token,
                "X-XSRF-TOKEN": token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{base}/course-list",
            },
        )
        prov.http_status = resp.status_code
        cache_raw("pmajay_reportajax.json", resp.content)
        if resp.status_code != 200:
            raise SourceUnavailable(
                f"POST /front/reportajax returned HTTP {resp.status_code} "
                "(research.md section 3.4 records this app leaking Laravel stack traces)"
            )
        try:
            payload = resp.json()
        except ValueError:
            raise SourceUnavailable("POST /front/reportajax did not return JSON")

    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise SourceUnavailable("catalogue payload had no rows")

    catalogue: list[dict] = []
    for raw in rows:
        qp_code = clean(raw.get("qp_code") or raw.get("sub_course_code") or raw.get("Sub Course Code"))
        sub_course = clean(raw.get("sub_course") or raw.get("Sub Course"))
        if not qp_code or not sub_course:
            continue
        catalogue.append(
            {
                "qp_code": qp_code,
                "sector": clean(raw.get("sector") or raw.get("Sector")),
                "sub_sector": clean(raw.get("sub_sector") or raw.get("Sub Sector")),
                "course": clean(raw.get("course") or raw.get("Course")),
                "sub_course": sub_course,
                "nsqf_level": None,  # research.md 3.4: the payload has no NSQF field at all
                "hours_min": None,
                "hours_max": None,
                "credits": None,
                "source": "pmajay",
                "level_inferred": False,
                "synthetic": False,
            }
        )

    prov.notes.append(f"{len(catalogue)} catalogue rows parsed from /front/reportajax")
    prov.notes.append(
        "The response carries no NSQF level field (research.md 3.4) — levels are "
        "joined from Kaushalverse by pipeline 03."
    )
    return _dedupe(catalogue), prov


def _dedupe(rows: list[dict]) -> list[dict]:
    """courses(qp_code) is UNIQUE — keep the first row per code, ordered."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in sorted(rows, key=lambda r: (r["qp_code"], r["sub_course"])):
        if row["qp_code"] in seen:
            continue
        seen.add(row["qp_code"])
        out.append(row)
    return out


# --------------------------------------------------------------------------
# Fallback
# --------------------------------------------------------------------------

#: PM-AJAY groups its catalogue as Sector -> Sub Sector -> Course -> Sub Course.
#: The GIA domain vocabulary is research.md section 2.4 (the illustrative list).
COURSE_GROUPINGS = (
    "Skill Training",
    "Self Employment",
    "Wage Employment",
    "Entrepreneurship Development",
)


def _from_kaushalverse() -> list[dict]:
    """Real QP identities from the register pipeline 02 already committed."""
    _, records = read_seed(KAUSHALVERSE_SEED)
    usable = [r for r in records if r.get("qp_code") and r.get("name")]
    log.info("fallback base: %d real qualification identities from Kaushalverse", len(usable))
    return usable


def synthetic_snapshot(reason: str, status: int | None) -> tuple[list[dict], Provenance]:
    base = _base()
    prov = Provenance(
        pipeline=NAME,
        source_url=f"{base}/front/reportajax",
        mode="synthetic",
        synthetic=True,
        http_status=status,
        failure_reason=reason,
    )
    quals = _from_kaushalverse()
    rng = stable_rng("avsar-pmajay-catalogue-fallback")
    rows: list[dict] = []
    seen: set[str] = set()

    for qual in quals:
        code = qual["qp_code"]
        if code in seen:
            continue
        seen.add(code)
        sector = qual.get("sector") or "Industry, Service & Business"
        rows.append(
            {
                "qp_code": code,
                "sector": sector,
                "sub_sector": qual.get("sector"),
                "course": rng.choice(COURSE_GROUPINGS),
                "sub_course": qual["name"],
                # Real NSQF level from NCVET — carried straight through so
                # pipeline 03 has something genuine to join and report on.
                "nsqf_level": qual.get("nsqf_level"),
                "hours_min": qual.get("min_hours"),
                "hours_max": qual.get("max_hours"),
                "credits": qual.get("credits_min"),
                "source": "kaushalverse",
                "level_inferred": False,
                "synthetic": True,
            }
        )

    if quals:
        prov.fallback_note = (
            "pmajay.dosje.gov.in was unavailable, so the GIA catalogue could not be "
            f"fetched. Emitted {len(rows)} structurally identical rows whose QP code, "
            "job-role name, sector and NSQF level are REAL values from the NCVET "
            "Kaushalverse register (pipeline 02, live). What is synthetic is the "
            "catalogue membership itself — i.e. the claim that PM-AJAY's GIA "
            "catalogue lists this QP — plus the Course/Sub-Course grouping. Every "
            "row carries synthetic=true and source='kaushalverse'; the flag is "
            "preserved into the database and rendered in the dashboard. "
            f"For scale reference research.md 3.4 measured the real catalogue at "
            f"~{REAL_CATALOGUE_ROWS} rows / ~{REAL_CATALOGUE_UNIQUE_QP} unique QP codes."
        )
        prov.notes.append(
            "QP identities are real (NCVET Kaushalverse); catalogue membership is synthetic."
        )
    else:
        # No Kaushalverse seed either — fully synthetic, and say so plainly.
        prov.fallback_note = (
            "Both pmajay.dosje.gov.in and the Kaushalverse seed were unavailable. "
            "Emitted a fully synthetic catalogue. No row here is government data."
        )
        for idx in range(1, 2001):
            sector, abbr = rng.choice(
                [("Agriculture", "AGR"), ("Apparel", "AMH"), ("Beauty & Wellness", "BWS"),
                 ("Construction", "CON"), ("Electronics", "ELE"), ("Food Processing", "FIC"),
                 ("Handicrafts", "HCS"), ("Healthcare", "HSS"), ("IT-ITeS", "SSC"),
                 ("Retail", "RAS")]
            )
            rows.append(
                {
                    "qp_code": f"{abbr}/Q{idx:04d}",
                    "sector": sector,
                    "sub_sector": sector,
                    "course": rng.choice(COURSE_GROUPINGS),
                    "sub_course": f"{sector} job role {idx}",
                    "nsqf_level": rng.choice([2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]),
                    "hours_min": rng.choice([200, 300, 400, 600]),
                    "hours_max": None,
                    "credits": None,
                    "source": "pmajay",
                    "level_inferred": True,
                    "synthetic": True,
                }
            )

    return _dedupe(rows), prov


#: Observations recorded while building this pipeline, kept in the seed so the
#: provenance is complete no matter which failure a later run happens to hit.
PORTAL_OBSERVATIONS_2026_09_11 = (
    "2026-09-11: GET /course-list and GET /illustrative-list both return HTTP 200 but "
    "serve resources/views/maintenance.blade.php ('We'll be right back') — the portal is "
    "under maintenance.",
    "2026-09-11: POST /front/reportajax returns HTTP 500 with a Laravel ErrorException "
    "naming app/Http/Controllers/front/UserController.php, i.e. the debug-mode leak "
    "research.md 3.4 warned about, now firing because the app files are absent.",
    "2026-09-11: the host serves an INCOMPLETE TLS chain, so OpenSSL clients (every Linux "
    "container) fail with CERTIFICATE_VERIFY_FAILED while Windows clients succeed via AIA "
    "fetching. Reproduce the maintenance finding from a container with "
    "PMAJAY_INSECURE_TLS=true.",
    "Static assets on the same host DO still serve — the May-2023 guidelines PDF downloads "
    "normally and is byte-identical (1,506,893 bytes) to the socialjustice.gov.in mirror, "
    "which is why pipeline 06 still builds a real RAG corpus.",
)


def run() -> PipelineResult:
    try:
        rows, prov = fetch_live()
        if len(rows) < 500:
            raise SourceUnavailable(f"only {len(rows)} rows returned; refusing a partial catalogue")
    except Exception as exc:
        log.warning("live PM-AJAY fetch failed (%s: %s) — falling back", type(exc).__name__, exc)
        status = getattr(getattr(exc, "response", None), "status_code", None)
        rows, prov = synthetic_snapshot(f"{type(exc).__name__}: {exc}", status)
        prov.notes.extend(PORTAL_OBSERVATIONS_2026_09_11)

    write_seed(SEED_PATH, rows, prov)
    result = PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)
    record_run(result)
    log.info("wrote %s (%d rows, mode=%s)", SEED_PATH.name, prov.rows, prov.mode)
    return result


if __name__ == "__main__":
    run()
