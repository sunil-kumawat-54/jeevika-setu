"""Pipeline 04 — build the curated crosswalk and both vector indexes.

PLAN.md section 5.1:
    04 | build_crosswalk.py | curated YAML (data/crosswalk/*.yaml) + embedding
       index | crosswalk(id, phrase, lang, gia_domain, qp_codes[], status)
       v0 ~= 150 entries | Hand-authored by the team using the illustrative-list
       10 domains; each entry reviewed by a second member

This pipeline produces two seed files:

``seeds/crosswalk.json``
    One record per (phrase, lang) — the ``crosswalk`` table rows, each carrying a
    multilingual-e5 embedding of the phrase. Candidate set **C1** in PLAN.md
    section 6 STEP 2 is an exact lookup against these phrases.

``seeds/qp_descriptions.json``
    One record per course, carrying an embedding of a composed QP description
    (job role + sector + level band). Candidate set **C2** is a top-k cosine
    search over these.

Both run on **CPU** (Gate 3 requirement). The embedding backend name is stamped
on every record so the runtime can refuse to mix vector spaces.

Malformed YAML is rejected loudly by ``core.domain.crosswalk_schema`` — the
pipeline does not skip bad entries, because a silently dropped crosswalk row is
a silently missing recommendation.
"""

from __future__ import annotations

import logging
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "services"))

from core.domain.crosswalk_schema import (  # noqa: E402
    CrosswalkValidationError,
    load_dir,
    summarise,
)

from pipelines.common import (  # noqa: E402
    SEEDS,
    PipelineResult,
    Provenance,
    read_seed,
    record_run,
    write_seed,
)

log = logging.getLogger("04_crosswalk")

NAME = "04_build_crosswalk"
CROSSWALK_DIR = REPO / "data" / "crosswalk"
CROSSWALK_SEED = SEEDS / "crosswalk.json"
QP_DESC_SEED = SEEDS / "qp_descriptions.json"
COURSES_SEED = SEEDS / "pmajay_courses.json"

BATCH = 64


def _embedder():
    from core.rag.embedder import get_embedder

    return get_embedder()


def compose_qp_description(course: dict, aliases: list[str] | None = None) -> str:
    """The text that represents a QP in the semantic index (candidate set C2).

    Deliberately more than the job-role name. Two things go in:

    1. Sector, sub-sector, level and hours — context multilingual-e5 can align a
       colloquial aspiration against.
    2. **The curated crosswalk phrases that map to this QP, in hi/mr/te/en.**

    Point 2 is load-bearing. The register is English-only, and measured on this
    corpus e5's cross-lingual recall from a Devanagari/Telugu utterance into an
    English job-role name is poor: the query "मैं सिलाई का काम सीखना चाहती हूँ"
    retrieved "Bijli mistry" and "Safai Mitra" ahead of any sewing QP, with all
    cosines squeezed into 0.77-0.80. Folding the curated phrases into the indexed
    text makes each QP's vector multilingual, so the same query lands in the same
    language space as the document. This stays inside PLAN.md §6 STEP 2's
    definition of C2 (top-k over qp_description embeddings) — it improves what
    each description *says*, not how C2 is computed.
    """
    parts = [course.get("sub_course") or ""]
    if course.get("course"):
        parts.append(str(course["course"]))
    if course.get("sector"):
        parts.append(str(course["sector"]))
    if course.get("sub_sector") and course.get("sub_sector") != course.get("sector"):
        parts.append(str(course["sub_sector"]))
    if course.get("nsqf_level") is not None:
        parts.append(f"NSQF level {course['nsqf_level']}")
    if course.get("hours_min"):
        parts.append(f"{course['hours_min']} hours")
    if aliases:
        parts.append(", ".join(aliases))
    return " | ".join(p for p in parts if p)


def aliases_by_qp_code() -> dict[str, list[str]]:
    """qp_code -> the curated phrases (all languages) that map to it."""
    from collections import defaultdict

    mapping: dict[str, list[str]] = defaultdict(list)
    for row in load_dir(CROSSWALK_DIR):
        for code in row.qp_codes:
            mapping[code].append(row.phrase)
    # Deterministic order keeps the seed byte-identical across runs.
    return {code: sorted(set(phrases)) for code, phrases in mapping.items()}


def build_crosswalk(prov: Provenance) -> list[dict]:
    rows = load_dir(CROSSWALK_DIR)
    stats = summarise(rows)
    prov.notes.append(
        f"{stats['rows']} phrase rows across {stats['concepts']} concepts, "
        f"GIA domains {stats['domains_covered']}"
    )
    prov.notes.append(f"languages: {stats['by_lang']}; status: {stats['by_status']}")
    prov.notes.append(f"{stats['qp_codes_referenced']} distinct QP codes referenced")
    if stats["gap_concepts"]:
        prov.notes.append(
            f"declared coverage gaps (no QP in the register): {stats['gap_concepts']} — "
            "these fall through to semantic recall and then refusal/handoff, and are "
            "flagged by the dashboard gap panel"
        )

    embedder = _embedder()
    prov.notes.append(f"embedding backend: {embedder.name} (dim={embedder.dim}), CPU")

    from core.rag.embedder import quantise

    records = [r.to_record() for r in rows]
    phrases = [r["phrase"] for r in records]
    vectors: list[list[float]] = []
    for i in range(0, len(phrases), BATCH):
        vectors.extend(embedder.encode_passages(phrases[i : i + BATCH]))
        log.info("embedded %d/%d phrases", min(i + BATCH, len(phrases)), len(phrases))
    for record, vector in zip(records, vectors, strict=True):
        record["embedding"] = quantise(vector)
        record["embedding_backend"] = embedder.name

    records.sort(key=lambda r: (r["lang"], r["phrase"]))
    return records


def build_qp_descriptions(prov: Provenance) -> list[dict]:
    _, courses = read_seed(COURSES_SEED)
    if not courses:
        prov.notes.append("no course seed — qp_descriptions skipped")
        return []

    embedder = _embedder()
    from core.rag.embedder import quantise

    aliases = aliases_by_qp_code()
    prov.notes.append(
        f"{len(aliases)} QPs carry curated multilingual aliases folded into their "
        "indexed description, so cross-lingual recall works from hi/mr/te"
    )

    records = []
    texts = []
    for course in courses:
        if not course.get("qp_code"):
            continue
        text = compose_qp_description(course, aliases.get(course["qp_code"]))
        records.append({"qp_code": course["qp_code"], "text": text, "backend": embedder.name})
        texts.append(text)

    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        vectors.extend(embedder.encode_passages(texts[i : i + BATCH]))
        if (i // BATCH) % 5 == 0:
            log.info("embedded %d/%d QP descriptions", min(i + BATCH, len(texts)), len(texts))
    for record, vector in zip(records, vectors, strict=True):
        record["embedding"] = quantise(vector)

    records.sort(key=lambda r: r["qp_code"])
    prov.notes.append(f"{len(records)} QP descriptions embedded with {embedder.name} on CPU")
    return records


def run() -> PipelineResult:
    prov = Provenance(
        pipeline=NAME,
        source_url="data/crosswalk/*.yaml (hand-authored; see docs/crosswalk-method.md)",
        mode="live",
    )

    try:
        crosswalk_records = build_crosswalk(prov)
    except CrosswalkValidationError as exc:
        # A malformed crosswalk is a build failure, never a silent skip.
        log.error("crosswalk validation FAILED: %s", exc)
        raise

    write_seed(CROSSWALK_SEED, crosswalk_records, prov)

    qp_prov = Provenance(
        pipeline=NAME,
        source_url="derived from seeds/pmajay_courses.json",
        mode="live",
        notes=["multilingual-e5 QP description index powering candidate set C2"],
    )
    qp_records = build_qp_descriptions(qp_prov)
    write_seed(QP_DESC_SEED, qp_records, qp_prov)

    result = PipelineResult(name=NAME, seed_path=CROSSWALK_SEED, provenance=prov)
    record_run(result)
    log.info(
        "wrote %s (%d rows) and %s (%d rows)",
        CROSSWALK_SEED.name,
        prov.rows,
        QP_DESC_SEED.name,
        qp_prov.rows,
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
