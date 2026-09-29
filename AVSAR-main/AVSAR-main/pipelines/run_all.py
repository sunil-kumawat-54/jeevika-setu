"""`make ingest` — run the ingestion pipelines in order and write the report.

PLAN.md section 5.1 numbers the pipelines 01-07. The *execution* order below
departs from the numbering in exactly one place, deliberately:

    00 districts -> 02 Kaushalverse -> 01 PM-AJAY -> 03 join -> 05 supply
       -> 06 guidelines RAG -> 07 demo sessions

**02 runs before 01** because pipeline 01's documented fallback builds its
catalogue from the NCVET register that 02 fetches. When the PM-AJAY portal is
reachable, 01 ignores that seed entirely and the order is irrelevant; when it is
not, this ordering is what keeps the fallback grounded in real QP identities
instead of invented ones. (Pipeline 04, the curated crosswalk, is authored by
hand in ``data/crosswalk/*.yaml`` and loaded by ``pipelines/04_build_crosswalk.py``.)

Every pipeline is idempotent: re-running writes the same records, so
``make ingest`` twice in a row leaves ``seeds/`` byte-identical apart from the
``fetched_at`` timestamp in each provenance block.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import logging
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "services"))

from pipelines.common import (  # noqa: E402
    SEEDS,
    PipelineResult,
    seed_fingerprint,
    snapshot_manifest,
    summarise,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s")
log = logging.getLogger("run_all")

#: (module filename, human label). Order is execution order, not file numbering.
PIPELINES = (
    ("00_fetch_districts.py", "districts (LGD via data.gov.in)"),
    ("02_fetch_kaushalverse.py", "NCVET Kaushalverse qualification register"),
    ("01_fetch_pmajay_courses.py", "PM-AJAY GIA course catalogue"),
    ("03_join_qp_level.py", "join NSQF levels onto courses"),
    ("04_build_crosswalk.py", "curated aspiration -> QP crosswalk"),
    ("05_seed_district_supply.py", "district centre supply (synthetic by design)"),
    ("06_load_guidelines_rag.py", "guidelines chunks + embeddings"),
    ("08_build_speech_fixtures.py", "mock speech fixtures (airplane-mode demo)"),
)


def _load(filename: str):
    path = REPO / "pipelines" / filename
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AVSAR ingestion pipelines in order")
    parser.add_argument("--only", nargs="*", help="run only these pipeline file stems")
    parser.add_argument("--skip-demo", action="store_true", help="do not seed demo sessions")
    parser.add_argument(
        "--report",
        default=str(REPO / "docs" / "ingest-report.md"),
        help="path for the generated ingest report",
    )
    args = parser.parse_args()

    results: list[PipelineResult] = []
    failures: list[str] = []

    for filename, label in PIPELINES:
        stem = filename[:-3]
        if args.only and stem not in args.only:
            continue
        log.info("=" * 72)
        log.info("RUN %s — %s", stem, label)
        log.info("=" * 72)
        module = _load(filename)
        if module is None:
            log.warning("%s not present — skipped", filename)
            continue
        started = time.monotonic()
        try:
            result = module.run()
        except Exception as exc:
            log.exception("%s FAILED", stem)
            failures.append(f"{stem}: {type(exc).__name__}: {exc}")
            continue
        elapsed = time.monotonic() - started
        if isinstance(result, PipelineResult):
            results.append(result)
            log.info(
                "%s -> %d rows, mode=%s, %.1fs (sha256 %s)",
                stem,
                result.rows,
                result.provenance.mode,
                elapsed,
                seed_fingerprint(result.seed_path)[:12],
            )

    if not args.skip_demo:
        module = _load("07_seed_users_demo.py")
        if module is not None:
            try:
                total = module.run()
                log.info("07_seed_users_demo -> %s synthetic sessions present", total)
            except Exception as exc:
                log.warning(
                    "07_seed_users_demo skipped (%s: %s) — needs a migrated database",
                    type(exc).__name__,
                    exc,
                )

    print("\n" + summarise(results) + "\n")

    snapshot_paths = [path for path in SEEDS.glob("*.json") if path.name != "source_snapshot_manifest.json"]
    manifest = snapshot_manifest(snapshot_paths)
    for entry in manifest:
        with contextlib.suppress(KeyError, ValueError):
            entry["path"] = pathlib.Path(entry["path"]).relative_to(REPO).as_posix()
    (SEEDS / "source_snapshot_manifest.json").write_text(
        json.dumps({"generated_by": "run_all", "snapshots": manifest}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    try:
        from pipelines.write_ingest_report import write_report

        path = write_report(results, failures, pathlib.Path(args.report))
        log.info("wrote %s", path)
    except Exception as exc:
        log.warning("could not write ingest report (%s: %s)", type(exc).__name__, exc)

    if failures:
        log.error("%d pipeline(s) failed:", len(failures))
        for failure in failures:
            log.error("  - %s", failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
