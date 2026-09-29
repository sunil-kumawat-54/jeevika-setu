"""Pipeline 03 — join NSQF levels onto the course catalogue.

PLAN.md section 5.1:
    03 | join_qp_level.py | inner join courses.qp_code <-> qualifications
       (match on code prefix + name fuzzy) | enriches courses.nsqf_level, hours,
       credits | Expect imperfect coverage; log unmatched %; fallback: infer
       level band from hours (200-600h STT ~ L3-L4 heuristic, flagged)

Why the join exists at all (research.md section 3.4): the PM-AJAY catalogue
*"has no NSQF level field anywhere in the response (the literal string 'NSQF'
never occurs)"*, so levels must come from NCVET's register.

Three match strategies, applied in order and recorded per row so the coverage
report is auditable:

1. ``exact_qp_code``  — courses.qp_code == qualifications.qp_code
2. ``code_serial``    — the numeric serial inside the QP code matches, ignoring
                        zero padding and the SSC prefix's spelling
3. ``name_fuzzy``     — normalised job-role names match (difflib ratio >= 0.92)

Anything still unmatched falls back to inferring a *band* from notional hours
using the GIA duration bands in research.md section 2.3, and is flagged
``level_inferred: true`` — never presented as an NCVET-assigned level.

Writes ``docs/ingest-report.md``'s join section data to
``seeds/join_report.json`` and never mutates a real level with an inferred one.
"""

from __future__ import annotations

import difflib
import logging
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pipelines.common import (  # noqa: E402
    SEEDS,
    PipelineResult,
    Provenance,
    read_seed,
    record_fingerprint,
    record_run,
    write_seed,
)

log = logging.getLogger("03_join")

NAME = "03_join_qp_level"
COURSES_SEED = SEEDS / "pmajay_courses.json"
QUALS_SEED = SEEDS / "kaushalverse_qualifications.json"
JOIN_REPORT = SEEDS / "join_report.json"

FUZZY_THRESHOLD = 0.92

#: research.md section 2.3 duration bands -> the NSQF level band a course of that
#: length typically sits in. Used ONLY when no register row can be matched, and
#: always flagged level_inferred=true.
HOURS_TO_LEVEL_BAND = (
    (0, 80, 2.0, "RPL / up-skilling band (32-80 h)"),
    (81, 199, 3.0, "below short-term band"),
    (200, 600, 3.5, "short-term band (200-600 h), research.md 2.3"),
    (601, 10_000, 4.5, "long-term band (6 months - 1 year)"),
)

_SERIAL_RE = re.compile(r"(\d{2,6})")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_name(name: str | None) -> str:
    if not name:
        return ""
    lowered = name.lower()
    for noise in (" - ", "(", ")", "/", ","):
        lowered = lowered.replace(noise, " ")
    return _NON_ALNUM.sub(" ", lowered).strip()


def code_serial(qp_code: str | None) -> str | None:
    """The zero-stripped numeric serial inside a QP code (``AGR/Q05301`` -> ``5301``)."""
    if not qp_code:
        return None
    match = _SERIAL_RE.search(qp_code)
    if not match:
        return None
    return match.group(1).lstrip("0") or "0"


def infer_level_from_hours(hours: int | None) -> tuple[float | None, str | None]:
    if hours is None:
        return None, None
    for low, high, level, note in HOURS_TO_LEVEL_BAND:
        if low <= hours <= high:
            return level, note
    return None, None


def build_index(quals: list[dict]) -> dict:
    by_code: dict[str, dict] = {}
    by_serial: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for qual in quals:
        if qual.get("qp_code"):
            by_code.setdefault(qual["qp_code"], qual)
            serial = code_serial(qual["qp_code"])
            if serial:
                by_serial.setdefault(serial, qual)
        name = norm_name(qual.get("name"))
        if name:
            by_name.setdefault(name, qual)
    return {"by_code": by_code, "by_serial": by_serial, "by_name": by_name}


def match_course(course: dict, index: dict, name_keys: list[str]) -> tuple[dict | None, str]:
    code = course.get("qp_code")
    if code and code in index["by_code"]:
        return index["by_code"][code], "exact_qp_code"

    serial = code_serial(code)
    if serial and serial in index["by_serial"]:
        return index["by_serial"][serial], "code_serial"

    name = norm_name(course.get("sub_course"))
    if name:
        if name in index["by_name"]:
            return index["by_name"][name], "name_exact"
        close = difflib.get_close_matches(name, name_keys, n=1, cutoff=FUZZY_THRESHOLD)
        if close:
            return index["by_name"][close[0]], "name_fuzzy"
    return None, "unmatched"


def run() -> PipelineResult:
    course_prov, courses = read_seed(COURSES_SEED)
    _, quals = read_seed(QUALS_SEED)

    # The join ENRICHES pipeline 01's snapshot; it must not erase how that
    # snapshot was obtained. Overwriting a synthetic provenance with the join's
    # own "live" provenance would silently relabel fallback rows as real data,
    # so pipeline 01's fields are carried forward verbatim.
    prov = Provenance(
        pipeline=f"{course_prov.get('pipeline', '01_fetch_pmajay_courses')} + {NAME}",
        source_url=course_prov.get("source_url", "seeds/pmajay_courses.json"),
        mode=course_prov.get("mode", "live"),
        source_name=course_prov.get("source_name") or course_prov.get("pipeline"),
        source_version=course_prov.get("source_version"),
        last_verified_at=course_prov.get("last_verified_at"),
        freshness_at=course_prov.get("freshness_at"),
        verification_status=course_prov.get("verification_status", "unverified"),
        verification_note=course_prov.get("verification_note"),
        synthetic=bool(course_prov.get("synthetic")),
        http_status=course_prov.get("http_status"),
        failure_reason=course_prov.get("failure_reason"),
        fallback_note=course_prov.get("fallback_note"),
        notes=list(course_prov.get("notes") or []),
    )

    if not courses:
        prov.mode = "synthetic"
        prov.failure_reason = "no course seed present — run pipeline 01 first"
        write_seed(COURSES_SEED, [], prov)
        return PipelineResult(name=NAME, seed_path=COURSES_SEED, provenance=prov)

    index = build_index(quals)
    name_keys = list(index["by_name"].keys())
    strategies: Counter[str] = Counter()
    inferred = 0
    enriched = 0

    for course in courses:
        qual, how = match_course(course, index, name_keys)
        strategies[how] += 1
        course["join_strategy"] = how

        if qual is not None:
            # Never overwrite a real level with anything else.
            if course.get("nsqf_level") is None and qual.get("nsqf_level") is not None:
                course["nsqf_level"] = qual["nsqf_level"]
                course["level_inferred"] = False
                enriched += 1
            if course.get("hours_min") is None:
                course["hours_min"] = qual.get("min_hours")
            if course.get("hours_max") is None:
                course["hours_max"] = qual.get("max_hours")
            if course.get("credits") is None:
                course["credits"] = qual.get("credits_min")
            if course.get("source") == "pmajay":
                course["source"] = "both"
            course["nqr_code"] = qual.get("nqr_code")
            continue

        if course.get("nsqf_level") is None:
            level, note = infer_level_from_hours(course.get("hours_min"))
            if level is not None:
                course["nsqf_level"] = level
                course["level_inferred"] = True
                course["level_inference_note"] = note
                inferred += 1

    total = len(courses)
    with_level = sum(1 for c in courses if c.get("nsqf_level") is not None)
    real_level = sum(
        1 for c in courses if c.get("nsqf_level") is not None and not c.get("level_inferred")
    )
    half_level = sum(
        1
        for c in courses
        if c.get("nsqf_level") is not None and float(c["nsqf_level"]) % 1 != 0
    )
    matched = total - strategies["unmatched"]

    # Honesty guard: when pipeline 01 fell back, the course rows were DERIVED
    # from this very register, so a ~100% match rate proves nothing about the
    # real PM-AJAY<->Kaushalverse join. Say so in the report rather than letting
    # a flattering number stand unqualified.
    derived = bool(course_prov.get("synthetic"))

    prov.notes += [
        f"{total} courses joined against {len(quals)} qualifications",
        f"matched {matched}/{total} ({100 * matched / total:.1f}%) — "
        + ", ".join(f"{k}={v}" for k, v in sorted(strategies.items())),
        f"{real_level}/{total} rows carry a register-assigned NSQF level",
        f"{inferred} rows fell back to an hours-derived band and are flagged level_inferred=true",
        f"{half_level}/{with_level} levelled rows sit at a half level "
        f"({100 * half_level / with_level:.1f}%)" if with_level else "no levelled rows",
    ]
    if derived:
        prov.notes.append(
            "CAVEAT: the course catalogue itself came from pipeline 01's fallback, which "
            "derives course rows FROM this Kaushalverse register. The match rate above is "
            "therefore tautological and is NOT evidence that the real PM-AJAY catalogue "
            "joins cleanly to NCVET. research.md 5.1 expects imperfect coverage against the "
            "live portal; the hours-derived level fallback stays implemented and tested for "
            "that case."
        )
    for note in prov.notes:
        log.info(note)

    write_seed(COURSES_SEED, courses, prov)

    report = {
        "total_courses": total,
        "total_qualifications": len(quals),
        "matched": matched,
        "unmatched": strategies["unmatched"],
        "match_rate_pct": round(100 * matched / total, 2) if total else 0.0,
        "strategies": dict(strategies),
        "with_nsqf_level": with_level,
        "register_assigned_level": real_level,
        "hours_inferred_level": inferred,
        "half_level_rows": half_level,
        "half_level_pct": round(100 * half_level / with_level, 2) if with_level else 0.0,
        "fuzzy_threshold": FUZZY_THRESHOLD,
        "courses_derived_from_register": derived,
        "match_rate_is_tautological": derived,
        "source_name": prov.source_name,
        "source_version": prov.source_version,
        "synthetic": prov.synthetic,
        "record_fingerprint": None,
    }
    report["record_fingerprint"] = record_fingerprint(report)
    report_prov = Provenance(
        pipeline=NAME, source_url="derived", mode="live", rows=1,
        notes=["Join coverage report consumed by docs/ingest-report.md"],
    )
    write_seed(JOIN_REPORT, [report], report_prov)

    result = PipelineResult(name=NAME, seed_path=COURSES_SEED, provenance=prov)
    record_run(result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
