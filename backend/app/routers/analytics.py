"""
DocuMind AI — Analytics Router (Stub)
Placeholder for retrieval quality analytics — will be implemented in Phase 5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/queries")
async def get_query_logs():
    """Query log history with similarity scores. (Phase 5)"""
    return {"queries": [], "total": 0}


@router.get("/summary")
async def get_summary():
    """Aggregate analytics stats. (Phase 5)"""
    return {
        "total_queries": 0,
        "avg_latency_ms": 0.0,
        "avg_similarity": 0.0,
        "total_documents": 0,
        "total_chunks": 0,
    }


@router.get("/documents")
async def get_document_frequency():
    """Per-document query frequency. (Phase 5)"""
    return {"documents": []}
