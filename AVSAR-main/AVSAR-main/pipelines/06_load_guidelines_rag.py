"""Pipeline 06 — guidelines corpus for hybrid RAG.

PLAN.md section 5.1:
    06 | load_guidelines_rag.py | PM-AJAY May-2023 PDF + NSQF gazette + GIA
       chapter -> chunk (~500 tok, section-aware) -> embed
       (multilingual-e5-base) | pgvector table doc_chunks(chunk, embedding,
       source, page) | Powers "scheme facts" answers; citations = doc+page

Two research findings shape the chunker:

* research.md section 9.2: *"Multi-hop questions cap Chain-MRR at 0.44 even at
  perfect recall unless section paths are embedded in each chunk"* — so the
  detected chapter/section path is **prefixed into the chunk text itself**, not
  merely stored in the ``section`` column. It therefore rides along into both
  the embedding and the tsvector.
* research.md section 9.2 (Contextual Retrieval): chunk context is worth ~35%
  fewer retrieval failures and is cheap to compute offline — which is exactly
  where this runs.

Sources (TECH_STACK.md section 2.3):
    https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf
    (mirror https://socialjustice.gov.in/writereaddata/UploadFile/36851753087331.pdf)
    https://ncvet.gov.in/wp-content/uploads/2022/08/NSQF.pdf

If a PDF cannot be fetched or parsed, the pipeline falls back to a synthetic
corpus built from the verbatim scheme facts already committed in
``scheme_constants.CANONICAL_FACTS`` (themselves transcribed from research.md
section 2.3) with ``synthetic: true`` — it never invents guideline prose.
"""

from __future__ import annotations

import logging
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "services"))

from pipelines.common import (  # noqa: E402
    RAW,
    SEEDS,
    PipelineResult,
    Provenance,
    RateLimiter,
    build_client,
    env,
    env_float,
    record_run,
    write_seed,
)

log = logging.getLogger("06_rag")

NAME = "06_load_guidelines_rag"
SEED_PATH = SEEDS / "doc_chunks.json"

#: ~500 tokens. We chunk on characters (language-agnostic, no tokenizer needed
#: offline); ~4 chars/token for English policy prose puts 2000 chars near the
#: 500-token target PLAN.md section 5.1 asks for.
CHUNK_CHARS = 2000
CHUNK_OVERLAP = 200
MIN_CHUNK_CHARS = 120

SOURCES = (
    {
        "key": "pmajay_gia_2023",
        "title": "PM-AJAY Guidelines (May 2023 Revised)",
        "urls": (
            "https://pmajay.dosje.gov.in/Writereaddata/Guidelines_PM-Ajay_may2023.pdf",
            "https://socialjustice.gov.in/writereaddata/UploadFile/36851753087331.pdf",
        ),
        "filename": "guidelines_pmajay_may2023.pdf",
    },
    {
        "key": "nsqf_gazette",
        "title": "NSQF Gazette Notification (27 Dec 2013)",
        "urls": ("https://ncvet.gov.in/wp-content/uploads/2022/08/NSQF.pdf",),
        "filename": "nsqf_gazette.pdf",
    },
)

#: Headings inside these documents: "Chapter 3", "3.7", "7.A.a.iv", "Annexure-I".
_HEADING_PATTERNS = (
    re.compile(r"^\s*(CHAPTER\s+[IVXLC0-9]+\b.*)$", re.IGNORECASE),
    re.compile(r"^\s*(ANNEXURE\s*[-–]?\s*[IVXLC0-9]+\b.*)$", re.IGNORECASE),
    re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3}\s+[A-Z][^\n]{4,80})$"),
    re.compile(r"^\s*(\d{1,2}\.[A-Z](?:\.[a-z]+)*\.?\s+[^\n]{4,80})$"),
)

_WS = re.compile(r"[ \t ]+")
_MULTINEWLINE = re.compile(r"\n{3,}")


def download(client, limiter, spec: dict, prov: Provenance) -> bytes | None:
    cached = RAW / spec["filename"]
    if cached.exists() and cached.stat().st_size > 10_000:
        log.info("%s: using cached %s", spec["key"], cached.name)
        return cached.read_bytes()
    for url in spec["urls"]:
        try:
            limiter.wait()
            resp = client.get(url)
            prov.http_status = resp.status_code
            if resp.status_code == 200 and resp.content[:5] == b"%PDF-":
                cached.write_bytes(resp.content)
                prov.notes.append(f"{spec['key']}: fetched {len(resp.content):,} bytes from {url}")
                return resp.content
            prov.notes.append(f"{spec['key']}: {url} -> HTTP {resp.status_code}, not a PDF")
        except Exception as exc:
            prov.notes.append(f"{spec['key']}: {url} failed ({type(exc).__name__}: {exc})")
    return None


def extract_pages(data: bytes) -> list[str]:
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        text = _WS.sub(" ", text)
        pages.append(_MULTINEWLINE.sub("\n\n", text).strip())
    return pages


def detect_section(line: str) -> str | None:
    stripped = line.strip()
    if not (4 <= len(stripped) <= 110):
        return None
    for pattern in _HEADING_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return _WS.sub(" ", match.group(1)).strip()
    return None


def chunk_page(text: str, current_section: str | None) -> tuple[list[tuple[str, str | None]], str | None]:
    """Split one page into (chunk, section) pairs, tracking the running section."""
    if not text:
        return [], current_section

    # Walk lines so a heading can retag the chunks that follow it.
    segments: list[tuple[str, str | None]] = []
    buffer: list[str] = []
    section = current_section

    def flush() -> None:
        nonlocal buffer
        body = "\n".join(buffer).strip()
        buffer = []
        if len(body) < MIN_CHUNK_CHARS:
            if body and segments:
                prev_body, prev_sec = segments[-1]
                segments[-1] = (prev_body + "\n" + body, prev_sec)
            elif body:
                segments.append((body, section))
            return
        start = 0
        while start < len(body):
            piece = body[start : start + CHUNK_CHARS]
            segments.append((piece.strip(), section))
            if start + CHUNK_CHARS >= len(body):
                break
            start += CHUNK_CHARS - CHUNK_OVERLAP

    for line in text.split("\n"):
        heading = detect_section(line)
        if heading:
            flush()
            section = heading
        buffer.append(line)
    flush()
    return [(body, sec) for body, sec in segments if len(body) >= MIN_CHUNK_CHARS], section


def build_chunks(pages: list[str], source_key: str, title: str) -> list[dict]:
    chunks: list[dict] = []
    section: str | None = None
    for page_no, page_text in enumerate(pages, start=1):
        pieces, section = chunk_page(page_text, section)
        for body, sec in pieces:
            # research.md 9.2: prefix the section path INTO the chunk text so it
            # reaches the embedding and the tsvector, not just the column.
            path = f"{title} | {sec}" if sec else title
            chunks.append(
                {
                    "source": source_key,
                    "page": page_no,
                    "section": sec,
                    "chunk": f"[{path} | p.{page_no}]\n{body}",
                    "synthetic": False,
                }
            )
    return chunks


def synthetic_chunks() -> list[dict]:
    """Fallback corpus from constants already cited to research.md section 2.3."""
    from core.domain.scheme_constants import CANONICAL_FACTS, GUIDELINES_TITLE

    rows = []
    for idx, (key, fact) in enumerate(sorted(CANONICAL_FACTS.items()), start=1):
        rows.append(
            {
                "source": "pmajay_gia_2023",
                "page": idx,
                "section": f"Canonical fact: {key}",
                "chunk": (
                    f"[{GUIDELINES_TITLE} | canonical fact {key}]\n"
                    f"{fact['answer_en']}\nCitation: {fact['citation']} (via {fact['source']})"
                ),
                "synthetic": True,
            }
        )
    return rows


def embed_chunks(chunks: list[dict], prov: Provenance) -> list[dict]:
    from core.rag.embedder import get_embedder

    embedder = get_embedder()
    prov.notes.append(f"embedding backend: {embedder.name} (dim={embedder.dim}), CPU")
    texts = [c["chunk"] for c in chunks]
    vectors: list[list[float]] = []
    batch = 32
    for i in range(0, len(texts), batch):
        vectors.extend(embedder.encode_passages(texts[i : i + batch]))
        if (i // batch) % 10 == 0:
            log.info("embedded %d/%d chunks", min(i + batch, len(texts)), len(texts))
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk["embedding"] = vector
        chunk["backend"] = embedder.name
    return chunks


def run() -> PipelineResult:
    prov = Provenance(
        pipeline=NAME,
        source_url=SOURCES[0]["urls"][0],
        mode="live",
    )
    limiter = RateLimiter(env_float("INGEST_QPS", 1.0))
    chunks: list[dict] = []

    with build_client(env("INGEST_UA", "AVSAR-SIH-Research/1.0"), timeout=120.0) as client:
        for spec in SOURCES:
            data = download(client, limiter, spec, prov)
            if not data:
                prov.notes.append(f"{spec['key']}: unavailable, skipped")
                continue
            try:
                pages = extract_pages(data)
            except Exception as exc:
                prov.notes.append(f"{spec['key']}: PDF parse failed ({type(exc).__name__}: {exc})")
                continue
            prov.notes.append(f"{spec['key']}: {len(pages)} pages extracted")
            built = build_chunks(pages, spec["key"], spec["title"])
            prov.notes.append(f"{spec['key']}: {len(built)} chunks")
            chunks.extend(built)

    if not chunks:
        prov.mode = "synthetic"
        prov.synthetic = True
        prov.failure_reason = "no guideline PDF could be fetched or parsed"
        prov.fallback_note = (
            "Built the RAG corpus from scheme_constants.CANONICAL_FACTS instead — every "
            "entry is a fact already transcribed from research.md 2.3 with its citation. "
            "No guideline prose was invented; each chunk carries synthetic=true."
        )
        chunks = synthetic_chunks()

    # doc_chunks(source,page,section,chunk) is UNIQUE — dedupe before embedding.
    seen: set[tuple] = set()
    unique = []
    for chunk in chunks:
        key = (chunk["source"], chunk["page"], chunk["section"], chunk["chunk"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)

    unique = embed_chunks(unique, prov)
    unique.sort(key=lambda c: (c["source"], c["page"], c["chunk"][:40]))

    write_seed(SEED_PATH, unique, prov)
    result = PipelineResult(name=NAME, seed_path=SEED_PATH, provenance=prov)
    record_run(result)
    log.info("wrote %s (%d chunks, mode=%s)", SEED_PATH.name, prov.rows, prov.mode)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
    run()
