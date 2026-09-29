"""Portable Phase 2 snapshot/load convergence tests."""

from __future__ import annotations

from pathlib import Path

from pipelines.common import (
    converge_records,
    enrich_records,
    record_fingerprint,
    records_fingerprint,
    snapshot_manifest,
)


def test_two_pass_canonical_snapshot_has_stable_keys_ids_and_fingerprint():
    provenance = {
        "pipeline": "phase2-fixture",
        "source_name": "fixture-register",
        "source_version": "2026-09",
        "mode": "mixed",
        "synthetic": True,
        "fetched_at": "2026-09-29T10:00:00+00:00",
    }
    rows, failures = enrich_records(
        [
            {
                "version_id": 4501,
                "qp_code": "SOL/Q00001",
                "name": "Solar Technician",
                "nsqf_level": "4.5",
                "source_record_id": "qual-4501",
                "synthetic": True,
            },
            {
                "source_record_id": "centre-1",
                "district_code": "D1",
                "centre_name": "Synthetic Centre",
                "coordinate_status": "synthetic",
                "synthetic": True,
            },
            {
                "source_record_id": "programme-1",
                "title": "Solar workshop",
                "programme_type": "workshop",
                "synthetic": True,
            },
        ],
        provenance,
        require_source_record_id=True,
    )
    assert failures == []
    store: dict[tuple[object, ...], dict] = {}
    first = converge_records(
        store,
        rows,
        ("source_name", "source_record_id"),
        entity="phase2-fixture",
        provenance=provenance,
    )
    second = converge_records(
        store,
        rows,
        ("source_name", "source_record_id"),
        entity="phase2-fixture",
        provenance={**provenance, "fetched_at": "2026-09-30T10:00:00+00:00"},
    )

    assert first.inserted == 3
    assert second.skipped == 3
    assert first.fingerprint == second.fingerprint == records_fingerprint(rows)
    assert list(store) == [
        ("fixture-register", "qual-4501"),
        ("fixture-register", "centre-1"),
        ("fixture-register", "programme-1"),
    ]
    assert len({id(row) for row in store.values()}) == 3
    assert store[("fixture-register", "qual-4501")]["nsqf_level"] == "4.5"
    assert all(row["synthetic"] for row in store.values())


def test_fingerprint_ignores_fetch_and_verification_timestamps_but_detects_content_changes():
    row = {"source_record_id": "x", "title": "Original", "fetched_at": "one"}
    changed_timestamp = {**row, "fetched_at": "two", "last_verified_at": "three"}
    changed_content = {**changed_timestamp, "title": "Changed"}
    assert record_fingerprint(row) == record_fingerprint(changed_timestamp)
    assert record_fingerprint(row) != record_fingerprint(changed_content)


def test_missing_source_identity_is_failure_and_not_a_generated_key():
    rows, failures = enrich_records(
        [{"title": "No identity", "synthetic": True}],
        {"pipeline": "fixture", "source_version": "v1", "mode": "synthetic"},
        require_source_record_id=True,
    )
    assert rows == []
    assert failures == ["row 0: missing source_record_id"]


def test_snapshot_manifest_uses_content_hash_and_reports_missing_inputs(tmp_path: Path):
    present = tmp_path / "snapshot.json"
    present.write_text('{"records": []}\n', encoding="utf-8")
    manifest = snapshot_manifest([present, tmp_path / "missing.json"])
    assert manifest[0]["status"] == "missing"
    assert manifest[1]["status"] == "present"
    assert len(manifest[1]["sha256"]) == 64
