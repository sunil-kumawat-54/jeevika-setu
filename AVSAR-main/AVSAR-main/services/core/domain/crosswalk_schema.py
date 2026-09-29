"""Schema, loader and validator for ``data/crosswalk/*.yaml``.

PLAN.md section 5.2 calls the crosswalk *"the moat"*, and research.md section 3.3
explains why it has to exist at all: the chain the problem statement implies is

    spoken aspiration -> occupation concept -> NCO-2015 code -> NSQF-aligned QP

and **no register publishes the NCO link**. Kaushalverse's ``ncoCode`` is null in
every record (this repo's own ingest confirms 0/1170), NQR's "Proposed
Occupation" is free text, and NCS exposes no taxonomy at all. So the join table
is hand-authored here, versioned, and reviewable.

Validation is deliberately strict — TECH_STACK section 9 requires *"YAML
crosswalk validated against schema on load"*, and Gate 3 requires malformed YAML
to be **rejected**, not silently skipped. A bad entry raises
:class:`CrosswalkValidationError` naming the file, the entry and the problem.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from core.domain.scheme_constants import GIA_DOMAIN_MAX, GIA_DOMAIN_MIN, GIA_DOMAINS

LANGS = ("hi", "mr", "te", "en")
STATUSES = ("auto", "reviewed")

#: ``AGR/Q5301``, ``AP/Q01866``, ``BFSI/Q04712`` — an SSC prefix, a slash, Q, digits.
QP_CODE_RE = re.compile(r"^[A-Z]{2,6}/Q\d{3,6}$")
CONCEPT_RE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")

REQUIRED_ENTRY_KEYS = {"concept", "gia_domain", "qp_codes", "phrases"}
ALLOWED_ENTRY_KEYS = REQUIRED_ENTRY_KEYS | {
    "status",
    "notes",
    "reviewed_by",
    "version",
    "gap_reason",
}


class CrosswalkValidationError(ValueError):
    """Raised when a crosswalk YAML file violates the schema."""


@dataclass(frozen=True, slots=True)
class CrosswalkRow:
    """One ``crosswalk`` table row: a phrase in one language."""

    phrase: str
    lang: str
    gia_domain: int
    concept: str
    qp_codes: tuple[str, ...]
    status: str
    version: int
    source_file: str
    notes: str | None = None
    gap_reason: str | None = None

    @property
    def is_gap(self) -> bool:
        """True when the concept is known but no QP in the register covers it."""
        return not self.qp_codes

    def to_record(self) -> dict:
        return {
            "phrase": self.phrase,
            "lang": self.lang,
            "gia_domain": self.gia_domain,
            "concept": self.concept,
            "qp_codes": list(self.qp_codes),
            "status": self.status,
            "version": self.version,
            "source_file": self.source_file,
        }


@dataclass
class CrosswalkDocument:
    """A parsed ``data/crosswalk/<name>.yaml``."""

    path: pathlib.Path
    entries: list[dict] = field(default_factory=list)
    rows: list[CrosswalkRow] = field(default_factory=list)


def _fail(path: pathlib.Path, detail: str, index: int | None = None) -> None:
    where = f"{path.name}" + (f" entry #{index}" if index is not None else "")
    raise CrosswalkValidationError(f"{where}: {detail}")


def _validate_entry(path: pathlib.Path, index: int, entry: Any) -> list[CrosswalkRow]:
    if not isinstance(entry, dict):
        _fail(path, f"entry must be a mapping, got {type(entry).__name__}", index)

    unknown = set(entry) - ALLOWED_ENTRY_KEYS
    if unknown:
        _fail(path, f"unknown keys {sorted(unknown)}", index)
    missing = REQUIRED_ENTRY_KEYS - set(entry)
    if missing:
        _fail(path, f"missing required keys {sorted(missing)}", index)

    concept = entry["concept"]
    if not isinstance(concept, str) or not CONCEPT_RE.match(concept):
        _fail(path, f"concept {concept!r} must be lower_snake_case (3-41 chars)", index)

    domain = entry["gia_domain"]
    if not isinstance(domain, int) or isinstance(domain, bool):
        _fail(path, f"gia_domain must be an integer, got {domain!r}", index)
    if not (GIA_DOMAIN_MIN <= domain <= GIA_DOMAIN_MAX):
        _fail(
            path,
            f"gia_domain {domain} is outside 1..10 — research.md section 2.4 fixes the "
            f"illustrative list at exactly {len(GIA_DOMAINS)} domains",
            index,
        )

    qp_codes = entry["qp_codes"]
    if not isinstance(qp_codes, list):
        _fail(path, "qp_codes must be a list", index)
    if not qp_codes:
        # A DECLARED GAP: the aspiration is real and common, but no qualification
        # in the ingested register covers it. Modelling that honestly beats
        # mapping the phrase to a near-miss QP, which would make the assistant
        # confidently recommend the wrong trade. Downstream this falls through to
        # semantic recall and then to refusal/handoff, and the dashboard's gap
        # panel (PLAN.md §4.2) flags it as demand with no supply — which is the
        # very signal an officer needs.
        gap_reason = entry.get("gap_reason")
        if not isinstance(gap_reason, str) or len(gap_reason.strip()) < 20:
            _fail(
                path,
                "qp_codes is empty, which is only allowed for a declared gap — add a "
                "'gap_reason' of at least 20 characters explaining why no QP matches",
                index,
            )
    for code in qp_codes:
        if not isinstance(code, str) or not QP_CODE_RE.match(code):
            _fail(path, f"qp_code {code!r} is not of the form SSC/Qnnnn", index)
    if len(set(qp_codes)) != len(qp_codes):
        _fail(path, "qp_codes contains duplicates", index)

    status = entry.get("status", "auto")
    if status not in STATUSES:
        _fail(path, f"status {status!r} must be one of {STATUSES}", index)

    version = entry.get("version", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        _fail(path, f"version {version!r} must be a positive integer", index)

    phrases = entry["phrases"]
    if not isinstance(phrases, dict) or not phrases:
        _fail(path, "phrases must be a non-empty mapping of lang -> list", index)
    bad_langs = set(phrases) - set(LANGS)
    if bad_langs:
        _fail(path, f"unsupported languages {sorted(bad_langs)}; allowed {LANGS}", index)

    rows: list[CrosswalkRow] = []
    for lang, items in phrases.items():
        if not isinstance(items, list) or not items:
            _fail(path, f"phrases.{lang} must be a non-empty list", index)
        for phrase in items:
            if not isinstance(phrase, str):
                _fail(path, f"phrases.{lang} contains a non-string {phrase!r}", index)
            text = phrase.strip()
            if len(text) < 2:
                _fail(path, f"phrases.{lang} entry {phrase!r} is too short", index)
            rows.append(
                CrosswalkRow(
                    phrase=text,
                    lang=lang,
                    gia_domain=domain,
                    concept=concept,
                    qp_codes=tuple(qp_codes),
                    status=status,
                    version=version,
                    source_file=path.name,
                    notes=entry.get("notes"),
                    gap_reason=entry.get("gap_reason"),
                )
            )
    return rows


def load_file(path: pathlib.Path) -> CrosswalkDocument:
    """Parse and validate one crosswalk YAML file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CrosswalkValidationError(f"{path.name}: not valid YAML — {exc}") from exc

    if raw is None:
        _fail(path, "file is empty")
    if not isinstance(raw, dict):
        _fail(path, f"top level must be a mapping, got {type(raw).__name__}")
    if "entries" not in raw:
        _fail(path, "top level is missing the 'entries' key")
    entries = raw["entries"]
    if not isinstance(entries, list) or not entries:
        _fail(path, "'entries' must be a non-empty list")

    doc = CrosswalkDocument(path=path)
    for index, entry in enumerate(entries, start=1):
        doc.rows.extend(_validate_entry(path, index, entry))
        doc.entries.append(entry)
    return doc


def load_dir(directory: pathlib.Path) -> list[CrosswalkRow]:
    """Load every ``*.yaml`` in a directory, rejecting duplicates across files."""
    files = sorted(p for p in directory.glob("*.yaml") if not p.name.startswith("_"))
    if not files:
        raise CrosswalkValidationError(f"no crosswalk YAML files found in {directory}")

    rows: list[CrosswalkRow] = []
    seen: dict[tuple[str, str], str] = {}
    for path in files:
        for row in load_file(path).rows:
            key = (row.phrase.lower(), row.lang)
            if key in seen:
                raise CrosswalkValidationError(
                    f"duplicate phrase {row.phrase!r} ({row.lang}) in {path.name}; "
                    f"already defined in {seen[key]} — crosswalk(phrase, lang) is UNIQUE"
                )
            seen[key] = path.name
            rows.append(row)
    return rows


def summarise(rows: list[CrosswalkRow]) -> dict:
    from collections import Counter

    return {
        "rows": len(rows),
        "concepts": len({r.concept for r in rows}),
        "domains_covered": sorted({r.gia_domain for r in rows}),
        "by_lang": dict(Counter(r.lang for r in rows)),
        "by_status": dict(Counter(r.status for r in rows)),
        "qp_codes_referenced": len({c for r in rows for c in r.qp_codes}),
        "gap_concepts": sorted({r.concept for r in rows if r.is_gap}),
    }
