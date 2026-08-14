"""
KueryCore AI — ORM Models
SQLAlchemy models for documents, chunks, conversations, messages, and query logs.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
    text,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import get_settings

settings = get_settings()


from app.models.user import User

class Document(Base):
    """Uploaded documents tracked for ingestion status."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    display_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # 'pdf' | 'markdown'
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_bytes: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Chunk(Base):
    """Text chunks with vector embeddings, linked to source documents."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    embedding: Mapped[Any] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index(
            "idx_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "idx_chunks_fts",
            text("to_tsvector('english', content)"),
            postgresql_using="gin",
        ),
    )


from app.models.conversation import Conversation, Message


class QueryLog(Base):
    """Query logs for analytics and evaluation benchmarking."""

    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("idx_query_logs_created", "created_at"),)
