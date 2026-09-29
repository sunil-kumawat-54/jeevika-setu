"""Shared plumbing for the one-shot ingestion pipelines (PLAN.md section 5.1).

Three rules govern everything in this package:

* **RULE 3 — seeds over scraping.** Pipelines run *offline*, write
  ``seeds/*.json``, and those snapshots are committed. The runtime never calls
  ``pmajay.dosje.gov.in`` or ``kaushalverse.ncvet.gov.in``.
* **Politeness.** ``INGEST_QPS=1`` -> one request per second, identified UA,
  raw responses cached under ``seeds/raw/`` (TECH_STACK section 2.3).
* **No fabrication.** When a source blocks, times out, changes schema, errors or
  is unreachable, the pipeline emits a *structurally identical* synthetic
  snapshot with ``synthetic: true`` on every record and a ``provenance`` block
  saying exactly what failed. It never dresses invented rows as official data.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import pathlib
import threading
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx

LOG_FORMAT = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

REPO = pathlib.Path(__file__).resolve().parents[1]
SEEDS = REPO / "seeds"
RAW = SEEDS / "raw"
DOCS = REPO / "docs"

SEEDS.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Politeness
# --------------------------------------------------------------------------


class RateLimiter:
    """Process-wide minimum interval between outbound requests."""

    def __init__(self, qps: float) -> None:
        self._min_interval = 1.0 / qps if qps > 0 else 0.0
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._min_interval - (now - self._last)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last = time.monotonic()


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


@dataclass
class Provenance:
    """Honest record of where a seed file's rows came from.

    ``mode`` is one of ``live`` (fetched from the real source), ``synthetic``
    (the source was unavailable; rows are generated and flagged) or ``mixed``.
    """

    pipeline: str
    source_url: str
    mode: str
    source_name: str | None = None
    source_version: str | None = None
    fetched_at: str = field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())
    last_verified_at: str | None = None
    freshness_at: str | None = None
    verification_status: str = "unverified"
    verification_note: str | None = None
    rows: int = 0
    synthetic: bool = False
    http_status: int | None = None
    failure_reason: str | None = None
    fallback_note: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


VOLATILE_PROVENANCE_KEYS = frozenset({"fetched_at", "last_verified_at"})


def canonical_json(value: Any) -> str:
    """Return the stable JSON representation used by snapshots and loaders."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def canonical_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove only volatile metadata before hashing a canonical source row."""
    return {
        key: value
        for key, value in record.items()
        if key not in VOLATILE_PROVENANCE_KEYS
    }


def record_fingerprint(record: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(canonical_record(record)).encode("utf-8")).hexdigest()


def records_fingerprint(records: Iterable[dict[str, Any]]) -> str:
    canonical = sorted(
        (canonical_record(record) for record in records),
        key=canonical_json,
    )
    return hashlib.sha256(canonical_json(canonical).encode("utf-8")).hexdigest()


def source_identity(provenance: dict[str, Any], path: pathlib.Path | None = None) -> tuple[str, str]:
    """Resolve a stable source name/version without inventing a row identity."""
    name = provenance.get("source_name") or provenance.get("pipeline") or (
        path.stem if path is not None else "unknown"
    )
    version = provenance.get("source_version") or provenance.get("snapshot_id") or "unversioned"
    return str(name), str(version)


def enrich_records(
    records: list[dict[str, Any]],
    provenance: dict[str, Any],
    *,
    require_source_record_id: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Attach source metadata while preserving explicit per-row values.

    A pipeline may inherit source metadata from its input envelope, but it must
    not manufacture a source record identity. Callers can therefore reject rows
    that cannot be safely upserted instead of silently multiplying them.
    """
    source_name, source_version = source_identity(provenance)
    shared = {
        "source_name": source_name,
        "source_version": source_version,
        "fetched_at": provenance.get("fetched_at"),
        "last_verified_at": provenance.get("last_verified_at"),
        "freshness_at": provenance.get("freshness_at"),
        "verification_status": provenance.get("verification_status", "unverified"),
        "verification_note": provenance.get("verification_note") or provenance.get("fallback_note"),
        "synthetic": bool(provenance.get("synthetic", False)),
    }
    accepted: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, original in enumerate(records):
        row = dict(original)
        for key, value in shared.items():
            if row.get(key) is None and value is not None:
                row[key] = value
        if require_source_record_id and not row.get("source_record_id"):
            failures.append(f"row {index}: missing source_record_id")
            continue
        row["record_fingerprint"] = record_fingerprint(row)
        accepted.append(row)
    return accepted, failures


@dataclass
class PipelineResult:
    name: str
    seed_path: pathlib.Path
    provenance: Provenance

    @property
    def rows(self) -> int:
        return self.provenance.rows

    @property
    def synthetic(self) -> bool:
        return self.provenance.synthetic


@dataclass
class LoadReport:
    """Counts and evidence for one deterministic snapshot load."""

    entity: str
    input_rows: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    fingerprint: str = ""
    source_name: str | None = None
    source_version: str | None = None
    mode: str = "unavailable"
    synthetic_rows: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"ok": self.ok}


def converge_records(
    existing: dict[tuple[Any, ...], dict[str, Any]],
    records: list[dict[str, Any]],
    natural_keys: tuple[str, ...],
    *,
    entity: str = "snapshot",
    provenance: dict[str, Any] | None = None,
) -> LoadReport:
    """Model the database upsert contract for portable two-pass tests."""
    provenance = provenance or {}
    report = LoadReport(
        entity=entity,
        input_rows=len(records),
        fingerprint=records_fingerprint(records),
        source_name=provenance.get("source_name") or provenance.get("pipeline"),
        source_version=provenance.get("source_version") or provenance.get("snapshot_id"),
        mode=provenance.get("mode", "unavailable"),
        synthetic_rows=sum(bool(row.get("synthetic")) for row in records),
    )
    for index, row in enumerate(records):
        key = tuple(row.get(field) for field in natural_keys)
        if any(value in (None, "") for value in key):
            report.failed += 1
            report.failures.append(f"row {index}: missing natural key {natural_keys}")
            continue
        fingerprint = row.get("record_fingerprint") or record_fingerprint(row)
        stored = existing.get(key)
        if stored is None:
            existing[key] = dict(row, record_fingerprint=fingerprint)
            report.inserted += 1
        elif stored.get("record_fingerprint") == fingerprint:
            report.skipped += 1
        else:
            existing[key] = dict(row, record_fingerprint=fingerprint)
            report.updated += 1
    return report


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


def build_client(ua: str, timeout: float = 30.0, verify: bool = True) -> httpx.Client:
    """HTTP client for ingestion.

    ``verify=False`` exists only for government hosts that serve an incomplete
    TLS chain, and only when an operator opts in explicitly per pipeline. It is
    never used by the runtime service.
    """
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        verify=verify,
        headers={
            "User-Agent": ua,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        },
    )


def cache_raw(name: str, content: bytes) -> pathlib.Path:
    """Cache a raw response body under seeds/raw/ (TECH_STACK section 2.3)."""
    path = RAW / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


# --------------------------------------------------------------------------
# Seed IO — deterministic and idempotent
# --------------------------------------------------------------------------


def write_seed(path: pathlib.Path, records: list[dict], provenance: Provenance) -> pathlib.Path:
    """Write a seed snapshot.

    The envelope is always ``{provenance, records}``; records are written in a
    stable order with sorted keys so re-running a pipeline against an unchanged
    source produces a byte-identical file (Gate 2 demands idempotency).
    """
    provenance.rows = len(records)
    provenance.source_name = provenance.source_name or provenance.pipeline
    provenance.source_version = provenance.source_version or records_fingerprint(records)[:16]
    provenance.freshness_at = provenance.freshness_at or provenance.fetched_at
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"provenance": provenance.to_dict(), "records": records}
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def read_seed(path: pathlib.Path) -> tuple[dict, list[dict]]:
    if not path.exists():
        return {}, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):  # tolerate a bare list
        return {}, payload
    return payload.get("provenance", {}), payload.get("records", [])


def seed_fingerprint(path: pathlib.Path) -> str:
    """Hash of the *records only* — provenance timestamps must not affect it,
    otherwise idempotency could never be proven."""
    _, records = read_seed(path)
    return records_fingerprint(records)


def snapshot_manifest(paths: Iterable[pathlib.Path]) -> list[dict[str, Any]]:
    """Describe local inputs without putting volatile timestamps in fingerprints."""
    manifest = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        if not path.exists():
            manifest.append({"path": path.as_posix(), "status": "missing"})
            continue
        content = path.read_bytes()
        manifest.append(
            {
                "path": path.as_posix(),
                "status": "present",
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return manifest


def stable_rng(seed_text: str):
    """Deterministic RNG so synthetic snapshots are reproducible byte-for-byte."""
    import random

    return random.Random(int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16))


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def record_run(result: PipelineResult) -> None:
    """Append an ``ingest_runs`` row when a database is reachable.

    Pipelines must still work with no database (a judge may run `make ingest`
    before `make up` finishes), so a failure here is logged and swallowed.
    """
    log = logging.getLogger(result.name)
    try:
        import sys

        sys.path.insert(0, str(REPO / "services"))
        from core.db import session_scope
        from core.models.tables import IngestRun

        with session_scope() as db:
            db.add(
                IngestRun(
                    pipeline=result.name,
                    mode=result.provenance.mode,
                    source_url=result.provenance.source_url,
                    rows=result.rows,
                    ok=not result.synthetic,
                    note=result.provenance.failure_reason or result.provenance.fallback_note,
                )
            )
    except Exception as exc:
        log.info("ingest_runs not recorded (%s) — seed file is still authoritative", type(exc).__name__)


def summarise(results: list[PipelineResult]) -> str:
    lines = ["| # | pipeline | mode | rows | seed file |", "|---|---|---|---|---|"]
    for idx, res in enumerate(results, start=1):
        mode = "SYNTHETIC" if res.synthetic else res.provenance.mode.upper()
        rel = res.seed_path.relative_to(REPO).as_posix()
        lines.append(f"| {idx:02d} | {res.name} | {mode} | {res.rows:,} | `{rel}` |")
    return "\n".join(lines)


def env(name: str, default: str) -> str:
    import os

    return os.environ.get(name, default)


def env_float(name: str, default: float) -> float:
    try:
        return float(env(name, str(default)))
    except ValueError:
        return default


def as_int(value: Any) -> int | None:
    try:
        if value in (None, "", "null", "NA", "N/A"):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    try:
        if value in (None, "", "null", "NA", "N/A"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
