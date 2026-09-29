"""Load committed ``seeds/*.json`` snapshots into Postgres.

This is the **only** path by which catalogue data reaches the runtime database.
RULE 3: the running service never calls a government portal; it reads rows that
pipelines 00-07 already wrote into ``seeds/``.

Every loader is **idempotent** — it upserts on the table's natural key, so
running ``make seed`` repeatedly converges to the same rows. The ``synthetic``
flag on each record is carried through verbatim so the dashboard can label it.
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services"))
sys.path.insert(0, str(REPO))

from core.models.tables import (  # noqa: E402
    CentreSupply,
    Course,
    Crosswalk,
    District,
    DistrictDemand,
    DocChunk,
    Opportunity,
    Programme,
    QpDescription,
    Qualification,
    SourceSnapshot,
    TrainingCentre,
)
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from pipelines.common import (  # noqa: E402
    SEEDS,
    LoadReport,
    enrich_records,
    read_seed,
    record_fingerprint,
    records_fingerprint,
)

log = logging.getLogger("load_to_db")

BATCH = 500


def _chunks(rows: list[dict], size: int = BATCH):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _upsert(db: Session, model, rows: list[dict], conflict: list[str]) -> int:
    """Bulk INSERT ... ON CONFLICT DO UPDATE on the given natural key."""
    if not rows:
        return 0
    columns = {c.name for c in model.__table__.columns}
    written = 0
    for batch in _chunks(rows):
        cleaned = [{k: v for k, v in row.items() if k in columns} for row in batch]
        stmt = pg_insert(model.__table__).values(cleaned)
        updatable = {
            c: stmt.excluded[c]
            for c in cleaned[0]
            if c not in conflict and c not in ("id", "created_at", "fetched_at")
        }
        if updatable:
            stmt = stmt.on_conflict_do_update(index_elements=conflict, set_=updatable)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict)
        db.execute(stmt)
        written += len(cleaned)
    db.flush()
    return written


def _seed_rows(path: pathlib.Path, *, require_source_record_id: bool = False) -> tuple[dict, list[dict], list[str]]:
    provenance, records = read_seed(path)
    rows, failures = enrich_records(
        records,
        provenance,
        require_source_record_id=require_source_record_id,
    )
    return provenance, rows, failures


def _identity(row: dict, conflict: list[str]) -> tuple:
    return tuple(row.get(field) for field in conflict)


def _upsert_report(
    db: Session,
    model,
    rows: list[dict],
    conflict: list[str],
    *,
    entity: str,
    provenance: dict,
    initial_failures: list[str] | None = None,
) -> LoadReport:
    """Upsert one entity while distinguishing unchanged rows from updates."""
    columns = {column.name for column in model.__table__.columns}
    prepared = [{key: value for key, value in row.items() if key in columns} for row in rows]
    report = LoadReport(
        entity=entity,
        input_rows=len(rows) + len(initial_failures or []),
        fingerprint=records_fingerprint(rows),
        source_name=provenance.get("source_name") or provenance.get("pipeline"),
        source_version=provenance.get("source_version") or provenance.get("snapshot_id"),
        mode=provenance.get("mode", "unavailable"),
        synthetic_rows=sum(bool(row.get("synthetic")) for row in rows),
        failures=list(initial_failures or []),
        failed=len(initial_failures or []),
    )
    existing: dict[tuple, str | None] = {}
    for row in prepared:
        key = _identity(row, conflict)
        filters = [getattr(model, field) == value for field, value in zip(conflict, key, strict=True)]
        previous = db.execute(select(model.record_fingerprint).where(*filters)).scalar_one_or_none()
        existing[key] = previous

    for row in prepared:
        key = _identity(row, conflict)
        fingerprint = row.get("record_fingerprint") or record_fingerprint(row)
        row["record_fingerprint"] = fingerprint
        statement = pg_insert(model.__table__).values(row)
        updatable = {
            column: statement.excluded[column]
            for column in row
            if column not in conflict and column not in ("id", "created_at", "fetched_at")
        }
        if updatable:
            statement = statement.on_conflict_do_update(index_elements=conflict, set_=updatable)
        else:
            statement = statement.on_conflict_do_nothing(index_elements=conflict)
        try:
            with db.begin_nested():
                db.execute(statement)
        except Exception as exc:
            report.failed += 1
            report.failures.append(f"{entity} {key}: {type(exc).__name__}: {exc}")
            continue
        previous = existing.get(key)
        if previous is None:
            report.inserted += 1
        elif previous == fingerprint:
            report.skipped += 1
        else:
            report.updated += 1
    db.flush()
    return report


def _missing_report(entity: str, path: pathlib.Path) -> LoadReport:
    return LoadReport(entity=entity, failures=[f"missing snapshot: {path.name}"], failed=1)


# --------------------------------------------------------------------------
# Loaders
# --------------------------------------------------------------------------


def load_districts(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "districts.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no district seed at %s", path)
        return 0
    count = _upsert(db, District, records, ["code"])
    log.info("districts: %d rows upserted from %s", count, path.name)
    return count


def load_courses(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "pmajay_courses.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no course seed at %s", path)
        return 0
    count = _upsert(db, Course, records, ["qp_code"])
    log.info("courses: %d rows upserted from %s", count, path.name)
    return count


def load_qualifications(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "kaushalverse_qualifications.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no qualification seed at %s", path)
        return 0
    # version_id is the natural key; drop rows without one rather than invent it.
    usable = [r for r in records if r.get("version_id") is not None]
    skipped = len(records) - len(usable)
    count = _upsert(db, Qualification, usable, ["version_id"])
    log.info("qualifications: %d rows upserted (%d skipped, no version_id)", count, skipped)
    return count


def load_source_snapshot(db: Session, path: pathlib.Path) -> LoadReport:
    provenance, records, failures = _seed_rows(path)
    if not path.exists():
        return _missing_report("source_snapshots", path)
    source_name = provenance.get("source_name") or provenance.get("pipeline") or path.stem
    source_version = provenance.get("source_version") or provenance.get("snapshot_id") or "unversioned"
    row = {
        "source_name": source_name,
        "source_version": source_version,
        "source_url": provenance.get("source_url"),
        "fetched_at": provenance.get("fetched_at"),
        "last_verified_at": provenance.get("last_verified_at"),
        "freshness_at": provenance.get("freshness_at"),
        "verification_status": provenance.get("verification_status", "unverified"),
        "verification_note": provenance.get("verification_note") or provenance.get("fallback_note"),
        "synthetic": bool(provenance.get("synthetic")),
        "record_fingerprint": records_fingerprint(records),
    }
    return _upsert_report(
        db,
        SourceSnapshot,
        [row],
        ["source_name", "source_version"],
        entity="source_snapshots",
        provenance=provenance,
        initial_failures=failures,
    )


def _load_canonical(
    db: Session,
    filename: str,
    model,
    conflict: list[str],
    *,
    entity: str,
    required_identity: bool = True,
) -> LoadReport:
    path = SEEDS / filename
    if not path.exists():
        return _missing_report(entity, path)
    provenance, rows, failures = _seed_rows(path, require_source_record_id=required_identity)
    return _upsert_report(
        db,
        model,
        rows,
        conflict,
        entity=entity,
        provenance=provenance,
        initial_failures=failures,
    )


def load_training_centres(db: Session) -> LoadReport:
    return _load_canonical(
        db, "training_centres.json", TrainingCentre, ["source_name", "source_record_id"], entity="training_centres"
    )


def load_programmes(db: Session) -> LoadReport:
    path = SEEDS / "programmes.json"
    if not path.exists():
        return _missing_report("programmes", path)
    provenance, rows, failures = _seed_rows(path)
    centre_ids = dict(
        db.execute(select(TrainingCentre.source_record_id, TrainingCentre.id)).all()
    )
    qualification_ids = dict(db.execute(select(Qualification.qp_code, Qualification.id)).all())
    resolved: list[dict] = []
    for row in rows:
        centre_id = centre_ids.get(row.pop("centre_source_record_id", None))
        if centre_id is None:
            failures.append(f"programme {row.get('source_record_id')}: centre source identity not loaded")
            continue
        row["centre_id"] = centre_id
        qp_code = row.pop("qp_code", None)
        if qp_code in qualification_ids:
            row["qualification_id"] = qualification_ids[qp_code]
        resolved.append(row)
    return _upsert_report(
        db,
        Programme,
        resolved,
        ["source_name", "source_record_id"],
        entity="programmes",
        provenance=provenance,
        initial_failures=failures,
    )


def load_opportunities(db: Session) -> LoadReport:
    return _load_canonical(
        db, "opportunities.json", Opportunity, ["source_name", "source_record_id"], entity="opportunities"
    )


def load_district_demand(db: Session) -> LoadReport:
    return _load_canonical(
        db,
        "district_demand.json",
        DistrictDemand,
        ["district_code", "block_code", "role_key", "period", "period_start"],
        entity="district_demand",
    )


def load_centre_supply(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "centre_supply.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no centre_supply seed at %s", path)
        return 0
    known = {code for (code,) in db.execute(select(District.code))}
    usable = [r for r in records if r.get("district_code") in known]
    dropped = len(records) - len(usable)
    if dropped:
        log.warning("centre_supply: dropped %d rows with unknown district_code", dropped)
    count = _upsert(db, CentreSupply, usable, ["district_code", "qp_code", "centre_name"])
    log.info("centre_supply: %d rows upserted from %s", count, path.name)
    return count


def load_crosswalk(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "crosswalk.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no crosswalk seed at %s", path)
        return 0
    count = _upsert(db, Crosswalk, records, ["phrase", "lang"])
    log.info("crosswalk: %d rows upserted from %s", count, path.name)
    return count


def load_qp_descriptions(db: Session, path: pathlib.Path | None = None) -> int:
    """Attach embeddings to courses by qp_code (the seed stores the code, not
    the surrogate course id, so the snapshot stays portable)."""
    path = path or SEEDS / "qp_descriptions.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no qp_description seed at %s", path)
        return 0
    id_by_code = dict(db.execute(select(Course.qp_code, Course.id)).all())
    rows = []
    for rec in records:
        course_id = id_by_code.get(rec.get("qp_code"))
        if course_id is None:
            continue
        rows.append(
            {
                "course_id": course_id,
                "text": rec["text"],
                "embedding": rec["embedding"],
                "backend": rec.get("backend", "hashing"),
            }
        )
    dropped = len(records) - len(rows)
    if dropped:
        log.warning("qp_descriptions: dropped %d rows whose qp_code has no course", dropped)
    count = _upsert(db, QpDescription, rows, ["course_id"])
    log.info("qp_descriptions: %d rows upserted from %s", count, path.name)
    return count


def load_doc_chunks(db: Session, path: pathlib.Path | None = None) -> int:
    path = path or SEEDS / "doc_chunks.json"
    _, records = read_seed(path)
    if not records:
        log.warning("no doc_chunk seed at %s", path)
        return 0
    # Conflict target is the generated identity index, not the raw columns —
    # see migration 0002_doc_chunk_identity for why.
    count = _upsert(db, DocChunk, records, ["source", "page", "section_key", "chunk_sha"])
    log.info("doc_chunks: %d rows upserted from %s", count, path.name)
    return count


LOADERS = (
    ("districts", load_districts),
    ("courses", load_courses),
    ("qualifications", load_qualifications),
    ("centre_supply", load_centre_supply),
    ("crosswalk", load_crosswalk),
    ("qp_descriptions", load_qp_descriptions),
    ("doc_chunks", load_doc_chunks),
)

CANONICAL_LOADERS = (
    ("training_centres", load_training_centres),
    ("programmes", load_programmes),
    ("opportunities", load_opportunities),
    ("district_demand", load_district_demand),
)


def load_all(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, loader in LOADERS:
        counts[name] = loader(db)
    return counts


def load_all_reported(db: Session) -> dict[str, LoadReport]:
    reports: dict[str, LoadReport] = {}
    for name, loader in CANONICAL_LOADERS:
        reports[name] = loader(db)
    return reports


def table_counts(db: Session) -> dict[str, int]:
    models = {
        "districts": District,
        "courses": Course,
        "qualifications": Qualification,
        "centre_supply": CentreSupply,
        "crosswalk": Crosswalk,
        "qp_descriptions": QpDescription,
        "doc_chunks": DocChunk,
    }
    return {
        name: db.execute(select(func.count()).select_from(model)).scalar_one()
        for name, model in models.items()
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s")
    from core.db import session_scope

    with session_scope() as session:
        load_all(session)
        print(json.dumps(table_counts(session), indent=2))
