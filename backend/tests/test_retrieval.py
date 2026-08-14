"""
KueryCore AI — Retrieval Unit Tests
Validates Reciprocal Rank Fusion (RRF) math, blending, and deduplication so that
chunks surfaced by BOTH the pgvector dense path and PostgreSQL FTS path are
merged once and ranked above single-source candidates.
"""

import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.services.retrieval import (
    RRF_K,
    RRF_FUSED_TOP_K,
    _phrase_coverage_rerank,
    _reciprocal_rank_fusion,
)


def _make_chunk(content: str) -> SimpleNamespace:
    """Stand-in for a SQLAlchemy Chunk: only `id` and `content` are read by retrieval."""
    return SimpleNamespace(id=uuid.uuid4(), content=content)


@pytest.mark.asyncio
async def test_rrf_blended_chunks_rank_above_single_source_candidates():
    chunk_both = _make_chunk("matched by vector and FTS")
    chunk_vec_only = _make_chunk("matched by vector only")
    chunk_lex_only = _make_chunk("matched by fts only")

    vector_candidates = [(chunk_both, 0.92), (chunk_vec_only, 0.81)]
    lexical_candidates = [(chunk_both, 0.7), (chunk_lex_only, 0.6)]

    fused = await asyncio.to_thread(
        _reciprocal_rank_fusion, vector_candidates, lexical_candidates
    )

    ids = [item["chunk"].id for item in fused]
    assert ids == [chunk_both.id, chunk_vec_only.id, chunk_lex_only.id], (
        "A chunk blended from both retrieval paths must outrank every single-source candidate"
    )

    # Chunk A is rank 1 in both lists -> 1/(60+1) + 1/(60+1)
    both = next(item for item in fused if item["chunk"].id == chunk_both.id)
    assert both["rrf_score"] == pytest.approx(2.0 / (RRF_K + 1), abs=1e-6)
    assert both["vec_rank"] == 1 and both["lex_rank"] == 1
    assert both["raw_vec_score"] == 0.92 and both["raw_lex_score"] == 0.7


@pytest.mark.asyncio
async def test_rrf_deduplicates_chunks_returned_by_both_paths():
    shared = _make_chunk("identical chunk returned by vector AND fts retrievers")

    vector_candidates = [(shared, 0.95)]
    lexical_candidates = [(shared, 0.88)]

    fused = await asyncio.to_thread(
        _reciprocal_rank_fusion, vector_candidates, lexical_candidates
    )

    assert len(fused) == 1, "Same chunk merged once across retrieval paths"
    item = fused[0]
    assert item["chunk"].id == shared.id
    assert item["vec_rank"] == 1 and item["lex_rank"] == 1
    assert item["raw_vec_score"] == 0.95 and item["raw_lex_score"] == 0.88
    assert item["rrf_score"] == pytest.approx(2 / (RRF_K + 1), abs=1e-6)


@pytest.mark.asyncio
async def test_rrf_rrf_score_math_uses_per_list_rank():
    # Rank positions are computed per input list, not after merging.
    chunk = _make_chunk("ranked third by vector, fifth by fts")
    filler = _make_chunk("filler")

    vector_candidates = [
        (filler, 0.3),
        (filler, 0.3),
        (chunk, 0.6),
        (filler, 0.3),
    ]
    lexical_candidates = [
        (filler, 0.2),
        (filler, 0.2),
        (filler, 0.2),
        (filler, 0.2),
        (chunk, 0.9),
    ]

    fused = await asyncio.to_thread(
        _reciprocal_rank_fusion, vector_candidates, lexical_candidates
    )
    item = next(x for x in fused if x["chunk"].id == chunk.id)

    expected = 1.0 / (RRF_K + 3) + 1.0 / (RRF_K + 5)
    assert item["rrf_score"] == pytest.approx(expected, abs=1e-6)


@pytest.mark.asyncio
async def test_rrf_respects_top_fused_limit():
    vector_candidates = [(f"chunk-{i}", 0.5) for i in range(20)]
    lexical_candidates = [(f"chunk-lex-{i}", 0.5) for i in range(20)]
    vector_candidates = [(_make_chunk(c), 0.5) for c, _ in vector_candidates]
    lexical_candidates = [(_make_chunk(c), 0.5) for c, _ in lexical_candidates]

    fused = await asyncio.to_thread(
        _reciprocal_rank_fusion, vector_candidates, lexical_candidates
    )

    assert len(fused) == RRF_FUSED_TOP_K


def test_rrf_default_k_constant():
    assert RRF_K == 60


def _chunk_with_metadata(content: str) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), content=content, metadata_={})


def test_phrase_rerank_surfaces_raw_similarity_on_metadata():
    chunk_a = _chunk_with_metadata("alpha topic")
    chunk_b = _chunk_with_metadata("beta unrelated")
    fused = [
        {"chunk": chunk_a, "raw_vec_score": 0.87, "raw_lex_score": 0.5},
        {"chunk": chunk_b, "raw_vec_score": 0.11, "raw_lex_score": 0.2},
    ]

    reranked = _phrase_coverage_rerank(fused, query="alpha topic", final_top_k=5)

    by_id = {c.id: c for c, _ in reranked}
    assert by_id[chunk_a.id].metadata_["raw_similarity"] == 0.87
    assert by_id[chunk_b.id].metadata_["raw_similarity"] == 0.11


def test_phrase_rerank_skips_raw_similarity_when_key_missing():
    chunk = SimpleNamespace(id=uuid.uuid4(), content="orphan", metadata_={})
    fused = [{"chunk": chunk, "raw_lex_score": 0.5}]

    reranked = _phrase_coverage_rerank(fused, query="orphan", final_top_k=5)

    assert "raw_similarity" not in reranked[0][0].metadata_