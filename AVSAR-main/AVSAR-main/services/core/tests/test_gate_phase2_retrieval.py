"""Phase 2 retrieval compatibility and canonical authorization contracts."""

from __future__ import annotations

import pathlib

import pytest

from core.rag.embedder import HashingEmbedder, assert_compatible, assert_dimension
from core.rag.retrieve import _tsquery, reciprocal_rank_fusion

REPO = pathlib.Path(__file__).resolve().parents[3]


def test_informal_multilingual_text_is_safe_tsquery_input():
    query = _tsquery("मुझे सिलाई & बिजली | !कहीं")
    assert "&" not in query and "!" not in query
    assert query.split(" | ") == ["जल", "कह"]
    assert query


def test_hashing_backend_is_stable_and_compatible():
    embedder = HashingEmbedder()
    assert embedder.name == "hashing"
    assert embedder.encode_query("silai kaam") == embedder.encode_query("silai kaam")
    assert_compatible("hashing", embedder.name)
    assert_dimension(768, embedder.dim)


def test_mixed_embedding_backend_or_dimension_fails_clearly():
    with pytest.raises(RuntimeError, match="backend mismatch"):
        assert_compatible("e5", "hashing")
    with pytest.raises(RuntimeError, match="dimension mismatch"):
        assert_dimension(768, 384)


def test_rrf_order_is_stable_for_semantic_and_lexical_candidates():
    first = reciprocal_rank_fusion([[{"id": 2}, {"id": 1}], [{"id": 1}, {"id": 3}]], limit=3)
    second = reciprocal_rank_fusion([[{"id": 2}, {"id": 1}], [{"id": 1}, {"id": 3}]], limit=3)
    assert [row["id"] for row in first] == [row["id"] for row in second]
    assert first[0]["id"] == 1


def test_grounded_route_joins_candidates_to_canonical_rows():
    source = (REPO / "services/core/api/recommendations.py").read_text(encoding="utf-8")
    assert "Qualification.qp_code.in_" in source
    assert "ST_DWithin" in source
    assert "ST_Distance" in source
    assert "synthetic" in source and "freshness_at" in source
