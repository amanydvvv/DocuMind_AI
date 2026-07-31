
import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.models import Chunk, Document
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize the embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY,
)


async def retrieve_context(
    query: str, db: AsyncSession, document_id: Optional[UUID] = None
) -> List[Tuple[Chunk, float, str]]:
    """
    Retrieve the top-K relevant document chunks for a given query along with their
    similarity scores and source document filenames, evaluated DB-side.
    """
    logger.info(f"Retrieving context for query: {query}")

    try:
        # 1. Embed the query
        query_vector = await embeddings.aembed_query(query)
        query_vector = query_vector[:settings.EMBEDDING_DIMENSION]

        # 2. Build DB-side vector search query with pgvector distance and LIMIT
        # Note: On very small tables (< ~1k rows), Postgres will naturally choose a Seq Scan
        # over the HNSW index because it's faster. It will automatically switch to using
        # idx_chunks_embedding_hnsw as the table scales up.
        distance_col = Chunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = select(Chunk, distance_col).order_by(distance_col)

        # Optional document filter
        if document_id:
            stmt = stmt.where(Chunk.document_id == document_id)

        # Apply DB-side LIMIT (HNSW index handles accurate top-K filtering)
        stmt = stmt.limit(settings.TOP_K)

        # 3. Execute query directly in database
        result = await db.execute(stmt)
        rows = result.all()

        logger.info(
            f"Retrieved {len(rows)} top-K chunks directly from database query (SQL LIMIT: {settings.TOP_K})."
        )

        # 4. Resolve source document filenames
        doc_ids = {chunk.document_id for chunk, _ in rows}
        doc_map = {}
        if doc_ids:
            doc_res = await db.execute(
                select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
            )
            doc_map = {d_id: fn for d_id, fn in doc_res.all()}

        # 5. Convert distance to 0-1 similarity score ONLY for top-K results
        # SCORE CONVERSION:
        # pgvector cosine distance d is (1 - cosine_similarity).
        # We transform distance to a 0.0 to 1.0 similarity score using:
        #   similarity_score = max(0.0, round(1.0 - float(distance), 4))
        retrieved = []
        for chunk, distance in rows:
            dist_val = float(distance) if distance is not None else 1.0
            similarity = max(0.0, round(1.0 - dist_val, 4))
            filename = chunk.metadata_.get("filename") or doc_map.get(
                chunk.document_id, "unknown"
            )
            retrieved.append((chunk, similarity, filename))

        return retrieved

    except Exception as e:
        logger.error(f"Error during context retrieval: {e}", exc_info=True)
        raise

