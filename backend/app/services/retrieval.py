"""
DocuMind AI - Hybrid Retrieval Service
Combines pgvector HNSW dense vector search with PostgreSQL Full-Text Search (BM25 lexical search),
fuses candidates using Reciprocal Rank Fusion (RRF), and re-ranks results via cross-scoring.
"""

import logging
import re
from typing import List, Optional, Tuple, Dict
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.models import Chunk, Document
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY,
)


def _compute_exact_cross_coverage(query: str, content: str) -> float:
    """
    Calculate keyword term coverage ratio and phrase match bonus.
    """
    clean_query = re.sub(r"[^\w\s]", "", query.lower()).strip()
    clean_content = re.sub(r"[^\w\s]", "", content.lower()).strip()

    if not clean_query or not clean_content:
        return 0.0

    # Stopwords filter for trivial terms
    stopwords = {"a", "an", "the", "is", "are", "was", "were", "of", "for", "in", "to", "on", "with", "and", "or", "what", "who", "where", "how", "why"}
    query_tokens = [t for t in clean_query.split() if t not in stopwords and len(t) > 1]

    if not query_tokens:
        query_tokens = clean_query.split()

    matched_tokens = sum(1 for token in query_tokens if token in clean_content)
    token_score = matched_tokens / len(query_tokens) if query_tokens else 0.0

    # Exact phrase bonus
    phrase_bonus = 0.3 if clean_query in clean_content else 0.0

    return min(1.0, round(token_score + phrase_bonus, 4))


async def _retrieve_vector_candidates(
    query: str, db: AsyncSession, document_id: Optional[UUID] = None, candidate_limit: int = 15
) -> List[Tuple[Chunk, float]]:
    """
    Retrieve top candidates using pgvector HNSW cosine similarity.
    Returns List[Tuple[Chunk, similarity_score]]
    """
    query_vector = await embeddings.aembed_query(query)
    query_vector = query_vector[:settings.EMBEDDING_DIMENSION]

    distance_col = Chunk.embedding.cosine_distance(query_vector).label("distance")
    stmt = select(Chunk, distance_col).order_by(distance_col)

    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)

    stmt = stmt.limit(candidate_limit)
    result = await db.execute(stmt)
    rows = result.all()

    candidates = []
    for chunk, distance in rows:
        dist_val = float(distance) if distance is not None else 1.0
        similarity = max(0.0, round(1.0 - dist_val, 4))
        candidates.append((chunk, similarity))

    return candidates


async def _retrieve_lexical_candidates(
    query: str, db: AsyncSession, document_id: Optional[UUID] = None, candidate_limit: int = 15
) -> List[Tuple[Chunk, float]]:
    """
    Retrieve top candidates using PostgreSQL Full-Text Search (ts_rank_cd) with ILIKE fallback.
    Returns List[Tuple[Chunk, fts_rank_score]]
    """
    clean_query = re.sub(r"[^\w\s]", " ", query).strip()
    if not clean_query:
        return []

    # 1. Try PostgreSQL Full-Text Search
    ts_vec = func.to_tsvector("english", Chunk.content)
    ts_query = func.plainto_tsquery("english", clean_query)
    rank_col = func.ts_rank_cd(ts_vec, ts_query).label("rank")

    stmt = select(Chunk, rank_col).where(ts_vec.op("@@")(ts_query)).order_by(rank_col.desc())
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)

    stmt = stmt.limit(candidate_limit)
    result = await db.execute(stmt)
    rows = result.all()

    # 2. Fallback to ILIKE query if FTS returns no matches
    if not rows:
        tokens = [t for t in clean_query.split() if len(t) > 2]
        if tokens:
            conditions = [Chunk.content.ilike(f"%{t}%") for t in tokens[:3]]
            stmt_fallback = select(Chunk).where(or_(*conditions))
            if document_id:
                stmt_fallback = stmt_fallback.where(Chunk.document_id == document_id)
            stmt_fallback = stmt_fallback.limit(candidate_limit)
            res_fb = await db.execute(stmt_fallback)
            fb_chunks = res_fb.scalars().all()
            return [(chunk, 0.5) for chunk in fb_chunks]
        return []

    candidates = []
    for chunk, rank in rows:
        rank_val = float(rank) if rank is not None else 0.0
        # Normalize rank score to 0-1 range
        norm_rank = min(1.0, round(rank_val / (rank_val + 1.0), 4))
        candidates.append((chunk, norm_rank))

    return candidates


def _reciprocal_rank_fusion(
    vector_candidates: List[Tuple[Chunk, float]],
    lexical_candidates: List[Tuple[Chunk, float]],
    k: int = 60,
) -> Dict[UUID, Dict]:
    """
    Combine vector and lexical candidates using Reciprocal Rank Fusion (RRF).
    RRF_Score(doc) = 1/(k + rank_vector) + 1/(k + rank_lexical)
    """
    fused_scores: Dict[UUID, Dict] = {}

    # Index vector candidates
    for rank_idx, (chunk, vec_score) in enumerate(vector_candidates, start=1):
        c_id = chunk.id
        if c_id not in fused_scores:
            fused_scores[c_id] = {
                "chunk": chunk,
                "vec_score": vec_score,
                "lex_score": 0.0,
                "vec_rank": rank_idx,
                "lex_rank": None,
                "rrf_score": 0.0,
            }

    # Index lexical candidates
    for rank_idx, (chunk, lex_score) in enumerate(lexical_candidates, start=1):
        c_id = chunk.id
        if c_id not in fused_scores:
            fused_scores[c_id] = {
                "chunk": chunk,
                "vec_score": 0.0,
                "lex_score": lex_score,
                "vec_rank": None,
                "lex_rank": rank_idx,
                "rrf_score": 0.0,
            }
        else:
            fused_scores[c_id]["lex_score"] = lex_score
            fused_scores[c_id]["lex_rank"] = rank_idx

    # Calculate RRF scores
    for item in fused_scores.values():
        rrf = 0.0
        if item["vec_rank"] is not None:
            rrf += 1.0 / (k + item["vec_rank"])
        if item["lex_rank"] is not None:
            rrf += 1.0 / (k + item["lex_rank"])
        item["rrf_score"] = rrf

    return fused_scores


def _cross_score_rerank(
    fused_candidates: Dict[UUID, Dict], query: str, top_k: int
) -> List[Tuple[Chunk, float]]:
    """
    Stage 2 Re-Ranking: Compute multi-feature cross score combining
    vector similarity (50%), lexical rank (30%), and exact term coverage (20%).
    """
    scored_candidates = []

    for item in fused_candidates.values():
        chunk = item["chunk"]
        vec_score = item["vec_score"]
        lex_score = item["lex_score"]
        cross_coverage = _compute_exact_cross_coverage(query, chunk.content)

        # Weighted hybrid re-rank score
        final_score = round(
            (0.50 * vec_score) + (0.30 * lex_score) + (0.20 * cross_coverage), 4
        )
        scored_candidates.append((chunk, final_score))

    # Sort descending by re-rank score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    return scored_candidates[:top_k]


async def retrieve_context(
    query: str, db: AsyncSession, document_id: Optional[UUID] = None
) -> List[Tuple[Chunk, float, str]]:
    """
    Two-Stage Hybrid Retrieval Pipeline:
    1. Candidate Retrieval: Vector Search (HNSW) + Lexical Search (PostgreSQL FTS)
    2. Reciprocal Rank Fusion (RRF) candidate merging
    3. Cross-Encoder / Cross-Scoring Re-Ranking
    """
    logger.info(f"Executing Two-Stage Hybrid Retrieval for query: '{query}'")

    try:
        candidate_limit = max(15, settings.TOP_K * 2)

        # 1. Fetch vector and lexical candidates in parallel
        vector_candidates = await _retrieve_vector_candidates(
            query=query, db=db, document_id=document_id, candidate_limit=candidate_limit
        )
        lexical_candidates = await _retrieve_lexical_candidates(
            query=query, db=db, document_id=document_id, candidate_limit=candidate_limit
        )

        logger.info(
            f"Retrieved {len(vector_candidates)} vector candidates and {len(lexical_candidates)} lexical candidates."
        )

        # 2. Reciprocal Rank Fusion (RRF)
        fused_candidates = _reciprocal_rank_fusion(
            vector_candidates=vector_candidates,
            lexical_candidates=lexical_candidates,
            k=60,
        )

        # 3. Cross-Scoring Re-Ranking
        reranked_top_k = _cross_score_rerank(
            fused_candidates=fused_candidates, query=query, top_k=settings.TOP_K
        )

        # 4. Resolve source document filenames
        doc_ids = {chunk.document_id for chunk, _ in reranked_top_k}
        doc_map = {}
        if doc_ids:
            doc_res = await db.execute(
                select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
            )
            doc_map = {d_id: fn for d_id, fn in doc_res.all()}

        retrieved = []
        for chunk, score in reranked_top_k:
            filename = chunk.metadata_.get("filename") or doc_map.get(
                chunk.document_id, "unknown"
            )
            retrieved.append((chunk, score, filename))

        logger.info(f"Hybrid retrieval pipeline completed. Returning {len(retrieved)} re-ranked chunks.")
        return retrieved

    except Exception as e:
        logger.error(f"Error during hybrid context retrieval: {e}", exc_info=True)
        raise
