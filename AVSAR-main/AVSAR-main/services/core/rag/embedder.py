"""Embedding backends — one interface, two implementations.

TECH_STACK.md section 1 selects **multilingual-e5-base**
(``intfloat/multilingual-e5-base``, 768-dim) for its cross-lingual hi/mr/te<->en
retrieval, self-hosted at zero marginal cost. TECH_STACK section 3 adds the
model's own requirement: *"encode with ``query:``/``passage:`` prefixes"*.

Two backends implement the same contract:

``E5Embedder``
    The real thing. sentence-transformers on **CPU** (ARCHITECTURE section 10
    keeps embeddings in pipelines, not at request time, so CPU is enough).

``HashingEmbedder``
    A dependency-free, deterministic character-n-gram hashing projection into
    the same 768 dimensions with the same L2 normalisation. It exists so the
    entire system — ingestion, retrieval, recommendation, demo — still runs on a
    clean machine with no model download and no network (RULE 1). Retrieval
    quality is materially lower; it is a *fallback*, never a claim of parity.

The backend name is written into ``qp_descriptions.backend`` and
``doc_chunks.backend`` on every row, and :func:`assert_compatible` refuses to
mix vector spaces — comparing an e5 vector against a hashed one is meaningless,
and silently doing so would corrupt every recommendation downstream.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import threading
from typing import Protocol

from core.config import settings

log = logging.getLogger("avsar.embedder")

DIM = 768
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class Embedder(Protocol):
    name: str
    dim: int

    def encode_query(self, text: str) -> list[float]: ...
    def encode_passages(self, texts: list[str]) -> list[list[float]]: ...


def _l2(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        # A zero vector breaks cosine distance; nudge it to a fixed unit basis.
        out = [0.0] * len(vector)
        out[0] = 1.0
        return out
    return [v / norm for v in vector]


# --------------------------------------------------------------------------
# Deterministic fallback
# --------------------------------------------------------------------------


class HashingEmbedder:
    """Deterministic hashed character-n-gram embedding into R^768.

    Signed feature hashing over word tokens plus 3/4-character n-grams. The
    n-grams matter: they give partial credit for Devanagari/Telugu morphology
    and for the code-mixed spellings beneficiaries actually produce
    ("silai" / "सिलाई" / "silaai"), which pure word hashing would miss entirely.

    Deterministic across processes and runs — the same text always yields the
    same vector, which is what lets Gate 4's determinism test hold.
    """

    name = "hashing"
    dim = DIM

    def __init__(self, dim: int = DIM) -> None:
        self.dim = dim

    @staticmethod
    def _features(text: str) -> list[str]:
        lowered = (text or "").strip().lower()
        tokens = _TOKEN_RE.findall(lowered)
        features: list[str] = [f"w:{t}" for t in tokens]
        features += [f"b:{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        compact = "".join(tokens)
        for n in (3, 4):
            features += [f"c{n}:{compact[i : i + n]}" for i in range(len(compact) - n + 1)]
        return features

    def _encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for feature in self._features(text):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            # Sub-linear weighting keeps one repeated n-gram from dominating.
            vector[index] += sign
        return _l2(vector)

    def encode_query(self, text: str) -> list[float]:
        return self._encode(text)

    def encode_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._encode(t) for t in texts]


# --------------------------------------------------------------------------
# Real multilingual-e5
# --------------------------------------------------------------------------


class E5Embedder:
    """``intfloat/multilingual-e5-base`` via sentence-transformers, CPU only."""

    name = "e5"
    dim = DIM

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer  # imported lazily

        self.model_name = model_name or settings.embedding_model
        log.info("loading %s on CPU", self.model_name)
        self._model = SentenceTransformer(self.model_name, device="cpu")
        self.dim = int(self._model.get_sentence_embedding_dimension())
        if self.dim != DIM:
            raise RuntimeError(
                f"{self.model_name} produces {self.dim}-dim vectors but the schema "
                f"declares VECTOR({DIM})"
            )

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts,
            batch_size=16,
            convert_to_numpy=True,
            normalize_embeddings=True,  # e5 is trained for cosine on unit vectors
            show_progress_bar=False,
        )
        return [[float(v) for v in row] for row in vectors]

    def encode_query(self, text: str) -> list[float]:
        # TECH_STACK section 3: the model REQUIRES these prefixes.
        return self._encode([E5_QUERY_PREFIX + (text or "")])[0]

    def encode_passages(self, texts: list[str]) -> list[list[float]]:
        return self._encode([E5_PASSAGE_PREFIX + (t or "") for t in texts])


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------

_LOCK = threading.Lock()
_CACHED: Embedder | None = None


def _build(backend: str) -> Embedder:
    backend = (backend or "auto").lower()
    if backend == "hashing":
        return HashingEmbedder()
    if backend == "e5":
        return E5Embedder()
    # auto
    try:
        return E5Embedder()
    except Exception as exc:
        log.warning(
            "multilingual-e5 unavailable (%s: %s) — falling back to the deterministic "
            "hashing embedder. Retrieval quality is lower; install "
            "services/core/requirements-ml.txt for the real model.",
            type(exc).__name__,
            exc,
        )
        return HashingEmbedder()


def get_embedder(backend: str | None = None, *, refresh: bool = False) -> Embedder:
    """Process-wide embedder, built once (model load is expensive)."""
    global _CACHED
    with _LOCK:
        if _CACHED is None or refresh or backend is not None:
            chosen = _build(backend or settings.embedding_backend)
            if backend is None:
                _CACHED = chosen
            return chosen
        return _CACHED


def assert_compatible(expected: str | None, actual: str) -> None:
    """Refuse to compare vectors produced by different backends.

    An e5 vector and a hashed vector live in unrelated spaces; a cosine distance
    between them is noise. Rather than quietly return nonsense recommendations,
    the caller is told to re-run the embedding job.
    """
    if expected and expected != actual:
        raise RuntimeError(
            f"embedding backend mismatch: index was built with '{expected}' but the "
            f"runtime is using '{actual}'. Re-run `make ingest` (or POST /admin/reembed) "
            "so the whole index shares one vector space."
        )


def assert_dimension(expected: int | None, actual: int) -> None:
    """Refuse vectors whose physical dimension differs from the runtime index."""
    if expected is not None and int(expected) != int(actual):
        raise RuntimeError(
            f"embedding dimension mismatch: index has {actual} dimensions but the "
            f"runtime expects {expected}. Re-run the embedding job for one index."
        )


def quantise(vector: list[float], places: int = 6) -> list[float]:
    """Round a vector before it is written to a committed seed file.

    768 float64s serialise to ~11 KB of JSON per row; six decimals halves that
    with no measurable effect on cosine ranking, and it keeps ``seeds/*.json``
    reviewable in a diff.
    """
    return [round(float(v), places) for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for already-normalised vectors (still safe if not)."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
