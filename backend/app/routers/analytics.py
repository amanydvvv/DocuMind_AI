"""
DocuMind AI — Analytics Router
Retrieval quality analytics, usage summaries, and per-document query frequencies.
"""

from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, Chunk, QueryLog
from app.schemas import (
    QueryLogResponse,
    AnalyticsSummary,
    DocumentQueryFrequency,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/queries")
async def get_query_logs(
    limit: int = Query(default=50, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Query log history with similarity scores and latency."""
    total_result = await db.execute(select(func.count(QueryLog.id)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(QueryLog)
        .order_by(QueryLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "queries": [QueryLogResponse.model_validate(log) for log in logs],
        "total": total,
    }


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Aggregate analytics stats across queries, documents, and vector chunks."""
    total_queries_res = await db.execute(select(func.count(QueryLog.id)))
    total_queries = total_queries_res.scalar_one()

    avg_res = await db.execute(
        select(
            func.avg(QueryLog.latency_ms),
            func.avg(QueryLog.avg_similarity),
        )
    )
    avg_latency, avg_sim = avg_res.one()

    total_docs_res = await db.execute(select(func.count(Document.id)))
    total_documents = total_docs_res.scalar_one()

    total_chunks_res = await db.execute(select(func.count(Chunk.id)))
    total_chunks = total_chunks_res.scalar_one()

    return AnalyticsSummary(
        total_queries=total_queries,
        avg_latency_ms=float(avg_latency) if avg_latency is not None else 0.0,
        avg_similarity=round(float(avg_sim), 4) if avg_sim is not None else 0.0,
        total_documents=total_documents,
        total_chunks=total_chunks,
    )


@router.get("/documents")
async def get_document_frequency(db: AsyncSession = Depends(get_db)):
    """Per-document query retrieval frequency."""
    # Fetch all query logs retrieved_chunks
    result = await db.execute(select(QueryLog.retrieved_chunks))
    all_chunks_lists = result.scalars().all()

    doc_counter = Counter()
    for chunks_list in all_chunks_lists:
        if not chunks_list:
            continue
        # Unique document_ids per query turn to avoid double counting same query
        query_doc_ids = set()
        for item in chunks_list:
            doc_id_str = item.get("document_id")
            if doc_id_str:
                query_doc_ids.add(doc_id_str)
        for doc_id in query_doc_ids:
            doc_counter[doc_id] += 1

    # Fetch document metadata for filenames
    docs_result = await db.execute(select(Document.id, Document.filename))
    doc_map = {str(doc_id): filename for doc_id, filename in docs_result.all()}

    frequencies = []
    for doc_id_str, count in doc_counter.most_common():
        if doc_id_str in doc_map:
            frequencies.append(
                DocumentQueryFrequency(
                    document_id=UUID(doc_id_str),
                    filename=doc_map[doc_id_str],
                    query_count=count,
                )
            )

    return {"documents": frequencies}
