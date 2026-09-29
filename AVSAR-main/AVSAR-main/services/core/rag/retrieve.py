"""Hybrid retrieval over ``doc_chunks`` — ARCHITECTURE.md section 8.

    2. **Hybrid RAG** (for open scheme questions): BM25 (Postgres tsvector w/
       Hindi analyzer config 'simple' + custom stopwords) ∩ pgvector cosine
       (multilingual-e5-normalized), reciprocal-rank fusion, top-6 chunks into
       `scheme_fact`.

Why fusion rather than either alone — research.md section 9.2, measured on a
PDF-regulation benchmark:

* bigger chunks help BM25 (Hit@8 .750 -> .833) but **collapse dense ranking**
  (MRR .722 -> .577 through semantic dilution);
* **hybrid BM25 + dense fused by Reciprocal Rank Fusion wins overall** —
  Hit@8 .875-.917 versus BM25 .750 and dense-only .792.

The same section also explains the chunker's decision to prefix each chunk with
its chapter/section path: *"Multi-hop questions cap Chain-MRR at 0.44 even at
perfect recall unless section paths are embedded in each chunk."*

Config ``'simple'`` is not laziness: Postgres ships no stemmer for Hindi,
Marathi or Telugu, so any language-specific configuration would silently
mis-stem Devanagari. ARCHITECTURE section 8 names `'simple'` explicitly.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("avsar.rag")

#: Standard RRF constant. Damps the contribution of low-ranked hits so a single
#: retriever cannot dominate the fusion.
RRF_K = 60

DEFAULT_LIMIT = 6
CANDIDATES_PER_RETRIEVER = 20

#: Stop-words that carry no retrieval signal. ARCHITECTURE section 8 asks for
#: "config 'simple' + custom stopwords"; with no Hindi stemmer available these
#: are removed from the BM25 query rather than from the index.
STOPWORDS = {
    "en": {"the", "a", "an", "of", "for", "to", "is", "are", "what", "how", "much", "i", "can", "get"},
    "hi": {"का", "की", "के", "है", "हैं", "में", "और", "को", "पर", "से", "क्या", "कितना", "मैं", "मुझे"},
    "mr": {"चा", "ची", "चे", "आहे", "आहेत", "मध्ये", "आणि", "ला", "वर", "पासून", "काय", "किती", "मी"},
    "te": {"యొక్క", "ఉంది", "ఉన్నాయి", "లో", "మరియు", "కు", "పై", "నుండి", "ఏమిటి", "ఎంత", "నేను"},
}
ALL_STOPWORDS = set().union(*STOPWORDS.values())

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tsquery(question: str) -> str:
    """Build a safe OR-tsquery from free text.

    Tokens are extracted and re-joined rather than interpolated, so a question
    containing ``&``, ``|`` or ``!`` cannot become a tsquery injection.
    """
    tokens = [
        token.lower()
        for token in _TOKEN_RE.findall(question or "")
        if len(token) > 1 and token.lower() not in ALL_STOPWORDS
    ]
    return " | ".join(tokens[:24])


def bm25_search(db: Session, question: str, limit: int = CANDIDATES_PER_RETRIEVER) -> list[dict]:
    """Lexical half: Postgres full-text ranking over ``doc_chunks.tsv``."""
    query = _tsquery(question)
    if not query:
        return []
    rows = db.execute(
        text(
            "SELECT id, source, page, section, chunk, synthetic, "
            "       ts_rank_cd(tsv, to_tsquery('simple', :q)) AS score "
            "FROM doc_chunks "
            "WHERE tsv @@ to_tsquery('simple', :q) "
            "ORDER BY score DESC LIMIT :k"
        ),
        {"q": query, "k": limit},
    ).mappings().all()
    return [dict(row) for row in rows]


def vector_search(db: Session, question: str, limit: int = CANDIDATES_PER_RETRIEVER) -> list[dict]:
    """Dense half: pgvector cosine over multilingual-e5 embeddings."""
    from core.rag.embedder import assert_compatible, assert_dimension, get_embedder

    embedder = get_embedder()
    metadata = db.execute(
        text(
            "SELECT DISTINCT backend, vector_dims(embedding) AS dimension "
            "FROM doc_chunks WHERE embedding IS NOT NULL"
        )
    ).mappings().all()
    for row in metadata:
        assert_compatible(row["backend"], embedder.name)
        assert_dimension(embedder.dim, row["dimension"])

    vector = embedder.encode_query(question)
    rows = db.execute(
        text(
            "SELECT id, source, page, section, chunk, synthetic, "
            "       1 - (embedding <=> CAST(:v AS vector)) AS score "
            "FROM doc_chunks ORDER BY embedding <=> CAST(:v AS vector) LIMIT :k"
        ),
        {"v": str(vector), "k": limit},
    ).mappings().all()
    return [
        {
            **dict(row),
            "provenance": {
                "source": row["source"],
                "synthetic": bool(row["synthetic"]),
            },
        }
        for row in rows
    ]


def _citation(row: dict) -> str:
    """doc + page, exactly as PLAN.md section 5.1 pipeline 06 requires."""
    titles = {
        "pmajay_gia_2023": "PM-AJAY Guidelines (May 2023 Revised)",
        "nsqf_gazette": "NSQF Gazette Notification (27 Dec 2013)",
    }
    source = row.get("source")
    title = titles.get(str(source), str(source))
    parts = [title]
    if row.get("section"):
        parts.append(str(row["section"]))
    if row.get("page"):
        parts.append(f"p. {row['page']}")
    citation = ", ".join(parts)
    if row.get("synthetic"):
        citation += " [SYNTHETIC]"
    return citation


def reciprocal_rank_fusion(
    rankings: list[list[dict]], k: int = RRF_K, limit: int = DEFAULT_LIMIT
) -> list[dict]:
    """Fuse ranked lists by ``sum(1 / (k + rank))``.

    Rank-based, so it does not need the two retrievers' scores to be on
    comparable scales — which they emphatically are not (``ts_rank_cd`` is
    unbounded, cosine sits in a ~0.04-wide band).
    """
    scores: dict[int, float] = {}
    payloads: dict[int, dict] = {}
    contributions: dict[int, dict[str, int]] = {}

    names = ["bm25", "vector"]
    for index, ranking in enumerate(rankings):
        name = names[index] if index < len(names) else f"retriever{index}"
        for rank, row in enumerate(ranking, start=1):
            doc_id = int(row["id"])
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            payloads.setdefault(doc_id, row)
            contributions.setdefault(doc_id, {})[name] = rank

    fused = []
    for doc_id, score in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])):
        row = dict(payloads[doc_id])
        row["rrf_score"] = round(score, 6)
        row["ranks"] = contributions[doc_id]
        row["retrievers"] = sorted(contributions[doc_id])
        row["citation"] = _citation(row)
        fused.append(row)
    return fused[:limit]


def hybrid_search(db: Session, question: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """BM25 ∪ pgvector, fused by RRF. Returns top-``limit`` with citations."""
    lexical: list[dict] = []
    dense: list[dict] = []

    try:
        lexical = bm25_search(db, question)
    except Exception as exc:
        log.warning("BM25 half unavailable: %s", exc)
    try:
        dense = vector_search(db, question)
    except Exception as exc:
        # A backend mismatch or a missing model must degrade to lexical-only
        # rather than take the whole answer path down.
        log.warning("dense half unavailable: %s", exc)

    if not lexical and not dense:
        return []
    return reciprocal_rank_fusion([lexical, dense], limit=limit)
