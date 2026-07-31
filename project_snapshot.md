# Project Snapshot

## 1. Project Identity
### README.md
`README.md` does not exist in the project root.
### Distinct project name variants
Based on previous full repository searches (case-insensitive):
- **'DocuMind AI' / 'DocuMind'**: Found extensively across 15+ files (including `STUDY_GUIDE.md`, `docker-compose.yml`, `requirements.txt`, `main.py`, `config.py`, `chat.py`, etc.).
- **'AI Knowledge Hub'**: 0 results found across the entire repository.

## 2. Full File Structure
```text
File does not exist or cannot be read: tree_output.txt```

## 3. Backend Code
### backend/app/main.py
```python
"""
DocuMind AI — FastAPI Application Entry Point
"""

import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.schemas import HealthResponse
from app.routers import (
    documents_router,
    chat_router,
    conversations_router,
    analytics_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered technical documentation assistant with RAG",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(analytics_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check server, database, and OmniRoute connectivity."""
    from sqlalchemy import text
    from app.database import async_session

    # Database check
    db_status = "unhealthy"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # OmniRoute check
    omniroute_status = "unhealthy"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OMNIROUTE_BASE_URL}/api/health")
            omniroute_status = "healthy" if resp.status_code == 200 else "degraded"
    except Exception:
        omniroute_status = "unreachable"

    overall = "healthy" if db_status == "healthy" else "unhealthy"
    if omniroute_status != "healthy":
        overall = "degraded" if overall == "healthy" else overall

    return HealthResponse(
        status=overall,
        database=db_status,
        omniroute=omniroute_status,
        version=settings.APP_VERSION,
    )

```

### backend/app/config.py
```python
"""
DocuMind AI — Configuration
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://documind:documind_dev@localhost:5435/documind"
    DATABASE_URL_SYNC: str = "postgresql://documind:documind_dev@localhost:5435/documind"

    # OmniRoute / LLM
    OMNIROUTE_BASE_URL: str | None = None
    GOOGLE_API_KEY: str | None = None
    OMNIROUTE_MODEL: str = "auto"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    GENERATIVE_MODEL: str = "gemini-flash-latest"

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "md"]
    UPLOAD_DIR: str = "./uploads"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

```

### backend/app/database.py
```python
"""
DocuMind AI — Database Setup
Async SQLAlchemy engine + session factory with pgvector support.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import get_settings

settings = get_settings()

# We use pgvector with an HNSW index (see app/models/__init__.py).
# Using HNSW avoids the "0 rows returned on small tables" issue that ivfflat suffers from
# when probed with standard asyncpg prepared statements, meaning we do NOT need to disable
# statement_cache_size (which would hurt performance).
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create tables and enable pgvector extension."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine connections on shutdown."""
    await engine.dispose()

```

### backend/app/models/__init__.py
```python
"""
DocuMind AI — ORM Models
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
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import get_settings

settings = get_settings()


class Document(Base):
    """Uploaded documents tracked for ingestion status."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # 'pdf' | 'markdown'
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
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
    )


class Conversation(Base):
    """Multi-turn Q&A conversation sessions."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Message(Base):
    """Individual messages within a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("idx_messages_conversation", "conversation_id"),)


class QueryLog(Base):
    """Query logs for analytics and evaluation benchmarking."""

    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (Index("idx_query_logs_created", "created_at"),)

```

### backend/app/schemas/__init__.py
```python
"""
DocuMind AI — Pydantic Schemas
Request/response models for API validation and serialization.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
#  Documents
# ──────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Document metadata returned from API."""
    id: UUID
    filename: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    documents: list[DocumentResponse]
    total: int


# ──────────────────────────────────────────────
#  Chat / Q&A
# ──────────────────────────────────────────────

class Citation(BaseModel):
    """A single citation linking an answer claim to a source chunk."""
    chunk_id: UUID
    document_id: UUID
    filename: str
    section: Optional[str] = None
    page_number: Optional[int] = None
    score: float
    content_preview: str = Field(..., max_length=300)


class ChatRequest(BaseModel):
    """User question sent to the RAG engine."""
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    top_k: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    """Complete (non-streaming) response with answer and citations."""
    answer: str
    citations: list[Citation]
    conversation_id: UUID
    latency_ms: int
    avg_similarity: float


# ──────────────────────────────────────────────
#  Conversations
# ──────────────────────────────────────────────

class MessageResponse(BaseModel):
    """A single message in a conversation."""
    id: UUID
    role: str
    content: str
    citations: Optional[list[Citation]] = None
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Conversation with its messages."""
    id: UUID
    title: Optional[str] = None
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """List of conversation summaries (without full messages)."""
    conversations: list[ConversationResponse]
    total: int


# ──────────────────────────────────────────────
#  Analytics
# ──────────────────────────────────────────────

class QueryLogResponse(BaseModel):
    """A single query log entry."""
    id: UUID
    question: str
    top_k: int
    avg_similarity: float
    latency_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsSummary(BaseModel):
    """Aggregate analytics stats."""
    total_queries: int
    avg_latency_ms: float
    avg_similarity: float
    total_documents: int
    total_chunks: int


class DocumentQueryFrequency(BaseModel):
    """How often a document's chunks are retrieved."""
    document_id: UUID
    filename: str
    query_count: int


# ──────────────────────────────────────────────
#  Health
# ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Server health check response."""
    status: str  # 'healthy' | 'degraded' | 'unhealthy'
    database: str
    omniroute: str
    version: str

```

### backend/app/schemas/chat.py
```python
File does not exist or cannot be read: backend/app/schemas/chat.py
```

### backend/app/routers/analytics.py
```python
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

```

### backend/app/routers/chat.py
```python
"""
DocuMind AI - Chat Router
RAG Q&A engine endpoint for natural language document querying with multi-turn memory.
"""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ChatResponse, Citation
from app.services.retrieval import retrieve_context
from app.services.generation import generate_answer

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge base using Retrieval-Augmented Generation (RAG)
    with multi-turn conversation memory.
    """
    start_time = time.time()

    try:
        # 1. Conversation Management
        conversation_id = request.conversation_id
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                conv = Conversation(id=conversation_id, title=request.question[:50])
                db.add(conv)
                await db.flush()
        else:
            conv = Conversation(id=uuid.uuid4(), title=request.question[:50])
            db.add(conv)
            await db.flush()
            conversation_id = conv.id

        # 2. Fetch past conversation history (up to last 10 messages)
        hist_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        chat_history = list(hist_result.scalars().all())[-10:]

        # 3. Save user's question as a Message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )
        db.add(user_msg)
        await db.flush()

        # 4. Retrieve relevant chunks from pgvector (Tasks 3 & 4)
        # retrieve_context returns List[Tuple[Chunk, similarity_score, filename]]
        retrieved_items = await retrieve_context(
            query=request.question, db=db, document_id=request.document_id
        )

        chunks = [item[0] for item in retrieved_items]

        # 5. Build citations list with real score & filename (Tasks 3 & 4)
        citations = []
        similarity_scores = []
        for chunk, score, filename in retrieved_items:
            page_num = chunk.metadata_.get("page_number", None) if chunk.metadata_ else None
            similarity_scores.append(score)
            citations.append(
                Citation(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    filename=filename,
                    page_number=page_num,
                    score=score,
                    content_preview=chunk.content[:297] + "..."
                    if len(chunk.content) > 300
                    else chunk.content,
                )
            )

        avg_similarity = (
            round(sum(similarity_scores) / len(similarity_scores), 4)
            if similarity_scores
            else 0.0
        )

        # 6. Generate answer using Google Gemini with chat history (Task 5)
        if not chunks:
            answer = "I couldn't find any relevant information in the uploaded documents to answer your question."
        else:
            answer = await generate_answer(
                query=request.question, chunks=chunks, chat_history=chat_history
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # 7. Save assistant's answer as a Message (Task 5)
        citation_dicts = [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "filename": c.filename,
                "page_number": c.page_number,
                "score": c.score,
                "content_preview": c.content_preview,
            }
            for c in citations
        ]

        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            citations=citation_dicts,
            latency_ms=latency_ms,
        )
        db.add(assistant_msg)
        await db.commit()

        return ChatResponse(
            answer=answer,
            citations=citations,
            conversation_id=conversation_id,
            latency_ms=latency_ms,
            avg_similarity=avg_similarity,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"RAG engine failed: {str(e)}")


```

### backend/app/routers/conversations.py
```python
"""
DocuMind AI — Conversations Router (Stub)
Placeholder for conversation management — will be implemented in Phase 3.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations():
    """List conversation sessions. (Phase 3)"""
    return {"conversations": [], "total": 0}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history. (Phase 3)"""
    return {"message": "Conversation detail — coming in Phase 3"}


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation. (Phase 3)"""
    return {"message": "Conversation deletion — coming in Phase 3"}

```

### backend/app/routers/documents.py
```python
"""
DocuMind AI — Document Management Router
Upload, list, detail, delete, and reindex documents.
"""

import hashlib
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Document, Chunk
from app.schemas import DocumentResponse, DocumentListResponse
from app.services.ingestion import ingest_document

settings = get_settings()
router = APIRouter(prefix="/api/documents", tags=["documents"])


def _allowed_extension(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_EXTENSIONS


def _file_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return "markdown" if ext == "md" else ext


async def _compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF or Markdown file for ingestion."""
    if not file.filename or not _allowed_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {settings.MAX_FILE_SIZE_MB}MB",
        )

    content_hash = await _compute_hash(content)

    # Check for duplicate
    existing = await db.execute(
        select(Document).where(Document.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="This document has already been uploaded (identical content hash).",
        )

    # Save file to disk
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    file_path = upload_dir / f"{file_id}.{ext}"
    file_path.write_bytes(content)

    # Create document record
    doc = Document(
        id=file_id,
        filename=file.filename,
        content_hash=content_hash,
        file_type=_file_type(file.filename),
        file_size=file_size,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    # Queue background ingestion
    background_tasks.add_task(ingest_document, str(file_id), str(file_path))

    # Get chunk count (0 for newly uploaded)
    doc_response = DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=0,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
    return doc_response


@router.get("", response_model=DocumentListResponse)
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all documents with their chunk counts."""
    # Subquery for chunk counts
    chunk_counts = (
        select(Chunk.document_id, func.count(Chunk.id).label("chunk_count"))
        .group_by(Chunk.document_id)
        .subquery()
    )

    result = await db.execute(
        select(Document, func.coalesce(chunk_counts.c.chunk_count, 0).label("chunk_count"))
        .outerjoin(chunk_counts, Document.id == chunk_counts.c.document_id)
        .order_by(Document.created_at.desc())
    )

    documents = []
    for row in result.all():
        doc = row[0]
        count = row[1]
        documents.append(
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                page_count=doc.page_count,
                status=doc.status,
                error_message=doc.error_message,
                chunk_count=count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )

    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get document details including chunk count."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunk_result = await db.execute(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )
    chunk_count = chunk_result.scalar() or 0

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its associated chunks (cascade)."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    upload_dir = Path(settings.UPLOAD_DIR)
    ext = doc.file_type if doc.file_type != "markdown" else "md"
    file_path = upload_dir / f"{doc.id}.{ext}"
    if file_path.exists():
        os.remove(file_path)

    await db.delete(doc)


@router.post("/{document_id}/reindex", response_model=DocumentResponse)
async def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-chunk and re-embed a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete existing chunks
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))

    # Reset status
    doc.status = "pending"
    doc.error_message = None

    # Queue re-ingestion
    background_tasks.add_task(ingest_document, str(document_id))

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        status=doc.status,
        error_message=doc.error_message,
        chunk_count=0,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )

```

### backend/app/services/generation.py
```python

import logging
from typing import List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from app.models import Chunk, Message
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

kwargs = {}
if settings.OMNIROUTE_BASE_URL:
    endpoint = settings.OMNIROUTE_BASE_URL.replace("http://", "").replace("https://", "")
    kwargs["client_options"] = {"api_endpoint": endpoint}

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model=settings.GENERATIVE_MODEL,
    google_api_key=settings.GOOGLE_API_KEY or "omniroute_dummy_key",
    temperature=0.2, # Low temperature for more factual responses
    **kwargs
)

RAG_PROMPT_TEMPLATE = """
You are an expert AI assistant tasked with answering questions based ONLY on the provided context and conversation history.

{chat_history_section}

Context information is below.
---------------------
{context}
---------------------

Given the context information, chat history, and no prior knowledge, answer the user's query.
If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
Do not hallucinate.

User Query: {query}
Answer:
"""

prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["chat_history_section", "context", "query"]
)

async def generate_answer(
    query: str, chunks: List[Chunk], chat_history: Optional[List[Message]] = None
) -> str:
    """
    Generate an answer using the provided chunks as context and prior chat history.
    """
    logger.info("Generating answer based on retrieved context and conversation history...")
    
    # Format context by joining chunk contents
    context_text = "\n\n---\n\n".join(
        [f"Document snippet {i+1}:\n{chunk.content}" for i, chunk in enumerate(chunks)]
    )
    
    # Format chat history if present
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        chat_history_section = "Conversation History:\n" + "\n".join(history_lines) + "\n---------------------"
    else:
        chat_history_section = ""
    
    # Build the prompt chain
    chain = prompt | llm
    
    # Execute the LLM
    try:
        response = await chain.ainvoke({
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        })
        return response.content
    except Exception as e:
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        raise


```

### backend/app/services/ingestion.py
```python
import os
import uuid
import logging
from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import select, delete

from app.database import async_session
from app.models import Document, Chunk
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize the embedding model dynamically
kwargs = {}
if settings.OMNIROUTE_BASE_URL:
    endpoint = settings.OMNIROUTE_BASE_URL.replace("http://", "").replace("https://", "")
    kwargs["client_options"] = {"api_endpoint": endpoint}

embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY or "omniroute_dummy_key",
    **kwargs
)


from typing import Optional

async def ingest_document(document_id: str, file_path: Optional[str] = None):
    """
    Background task to ingest a document: extract text, chunk, embed, and store in the DB.
    Bulletproofed with robust error handling and logging.
    """
    logger.info(f"Starting ingestion for document_id: {document_id}")
    
    async with async_session() as db:
        try:
            # 1. Fetch document
            doc_uuid = uuid.UUID(document_id)
            result = await db.execute(select(Document).where(Document.id == doc_uuid))
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error(f"Document {document_id} not found in database for ingestion.")
                return

            if not file_path:
                ext = doc.file_type if doc.file_type != "markdown" else "md"
                file_path = str(Path(settings.UPLOAD_DIR) / f"{doc.id}.{ext}")

            if not os.path.exists(file_path):
                logger.error(f"File not found on disk: {file_path}")
                doc.status = "error"
                doc.error_message = f"File not found: {file_path}"
                await db.commit()
                return

            # 2. Parse text
            logger.info(f"Parsing file: {file_path}")
            pages = []
            try:
                if doc.file_type == "pdf":
                    with pymupdf.open(file_path) as pdf:
                        doc.page_count = len(pdf)
                        for i, page in enumerate(pdf):
                            text = page.get_text()
                            if text:
                                pages.append({"text": text, "page_number": i + 1})
                elif doc.file_type == "markdown":
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        pages.append({"text": text, "page_number": 1})
                        doc.page_count = 1
                else:
                    raise ValueError(f"Unsupported file type: {doc.file_type}")
            except Exception as e:
                logger.error(f"Failed to parse document {document_id}: {e}", exc_info=True)
                doc.status = "error"
                doc.error_message = f"Parsing error: {str(e)}"
                await db.commit()
                return

            if not pages:
                logger.warning(f"No text extracted from document {document_id}")
                doc.status = "completed"
                doc.error_message = "No text found in document."
                await db.commit()
                return

            # 3. Chunking (using dynamic settings)
            optimal_chunk_size = settings.CHUNK_SIZE
            optimal_chunk_overlap = settings.CHUNK_OVERLAP
            
            logger.info(f"Chunking document with size={optimal_chunk_size}, overlap={optimal_chunk_overlap}")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=optimal_chunk_size,
                chunk_overlap=optimal_chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )

            chunks_data = []
            chunk_index = 0
            for page in pages:
                page_chunks = text_splitter.split_text(page["text"])
                for chunk in page_chunks:
                    chunks_data.append({
                        "text": chunk,
                        "metadata": {
                            "page_number": page["page_number"],
                            "filename": doc.filename,
                        },
                        "index": chunk_index
                    })
                    chunk_index += 1

            if not chunks_data:
                logger.warning(f"No chunks generated for document {document_id}")
                doc.status = "completed"
                await db.commit()
                return
                
            logger.info(f"Extracted {len(chunks_data)} chunks from document {document_id}")

            # 4. Generate Embeddings & 5. Insert into DB
            logger.info(f"Generating embeddings for {len(chunks_data)} chunks...")
            batch_size = 100
            total_inserted = 0
            
            try:
                for i in range(0, len(chunks_data), batch_size):
                    batch_chunks = chunks_data[i:i + batch_size]
                    texts = [c["text"] for c in batch_chunks]
                    
                    # Generate embeddings (wrapped in try/except for rate limiting robustness)
                    vectors = await embeddings.aembed_documents(texts)
                    
                    # Insert chunks
                    for data, vector in zip(batch_chunks, vectors):
                        db_chunk = Chunk(
                            document_id=doc.id,
                            chunk_index=data["index"],
                            content=data["text"],
                            metadata_=data["metadata"],
                            embedding=vector[:settings.EMBEDDING_DIMENSION],
                            token_count=len(data["text"]) // 4  # Rough token estimation
                        )
                        db.add(db_chunk)
                    
                    total_inserted += len(batch_chunks)
                    
                # 6. Update document status
                doc.status = "completed"
                doc.error_message = None
                await db.commit()
                
                logger.info(f"Successfully inserted {total_inserted} embeddings into pgvector.")
                logger.info(f"Ingestion completed successfully for document {document_id}")

            except Exception as e:
                logger.error(f"Error generating embeddings or inserting chunks for document {document_id}: {e}", exc_info=True)
                doc.status = "error"
                doc.error_message = f"Embedding/Database error: {str(e)}"
                await db.commit()
                return

        except Exception as e:
            # Fatal fallback error catch
            logger.critical(f"Critical fatal error ingesting document {document_id}: {e}", exc_info=True)
            try:
                doc_uuid = uuid.UUID(document_id)
                result = await db.execute(select(Document).where(Document.id == doc_uuid))
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "error"
                    doc.error_message = f"Fatal system error: {str(e)}"
                    await db.commit()
            except Exception as rollback_err:
                logger.error(f"Failed to update document error status during critical failure: {rollback_err}")

```

### backend/app/services/retrieval.py
```python

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
kwargs = {}
if settings.OMNIROUTE_BASE_URL:
    endpoint = settings.OMNIROUTE_BASE_URL.replace("http://", "").replace("https://", "")
    kwargs["client_options"] = {"api_endpoint": endpoint}

embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY or "omniroute_dummy_key",
    **kwargs
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


```

### backend/requirements.txt
```python
# DocuMind AI — Python Dependencies

# Web framework
fastapi==0.115.12
uvicorn[standard]==0.34.3
python-multipart==0.0.20

# Database
sqlalchemy[asyncio]==2.0.41
asyncpg==0.30.0
pgvector==0.3.6
alembic==1.15.2

# Settings
pydantic-settings==2.9.1

# LLM / RAG (Phase 2-3)
langchain==0.3.25
langchain-google-genai==2.1.4
langchain-community==0.3.24
langchain-text-splitters==0.3.8

# Document parsing
pymupdf==1.25.5
markdown-it-py==3.0.0

# HTTP client
httpx==0.28.1

# Utilities
python-dotenv==1.1.0

```


## 4. Database State
Schema and Row Counts (Queried live via SQLAlchemy):
```text
Table: query_logs
  - top_k (integer)
  - created_at (timestamp with time zone)
  - retrieved_chunks (jsonb)
  - id (uuid)
  - avg_similarity (double precision)
  - latency_ms (integer)
  - question (text)
  Rows: 0

Table: documents
  - updated_at (timestamp with time zone)
  - file_size (integer)
  - page_count (integer)
  - created_at (timestamp with time zone)
  - id (uuid)
  - error_message (text)
  - filename (character varying)
  - content_hash (character varying)
  - file_type (character varying)
  - status (character varying)
  Rows: 12

Table: chunks
  - created_at (timestamp with time zone)
  - document_id (uuid)
  - chunk_index (integer)
  - id (uuid)
  - metadata (jsonb)
  - embedding (USER-DEFINED)
  - token_count (integer)
  - content (text)
  Rows: 111

Table: conversations
  - id (uuid)
  - created_at (timestamp with time zone)
  - updated_at (timestamp with time zone)
  - title (character varying)
  Rows: 13

Table: messages
  - latency_ms (integer)
  - created_at (timestamp with time zone)
  - conversation_id (uuid)
  - id (uuid)
  - citations (jsonb)
  - content (text)
  - role (character varying)
  Rows: 40

Table: alembic_version
  - version_num (character varying)
  Rows: 1

```

## 5. Frontend State
Listing `frontend/` directory:
```text
frontend/
    src/
```
(The directory exists but is completely empty).

## 6. Testing State
### `backend/tests/test_integration.py`
```python
import pytest
import requests
import time
import os
import uuid
import tempfile

BASE_URL = "http://localhost:8000"
STATE = {}

def test_server_health():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

def test_document_upload():
    unique_id = str(uuid.uuid4())
    content = f"Project Xyzzy is a highly classified initiative to develop a new propulsion system. The lead engineer is Dr. Samantha Carter. It was started in 2024. Random ID: {unique_id}"
    
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
        tmp_file.write(content.encode("utf-8"))
        file_path = tmp_file.name
        
    try:
        with open(file_path, "rb") as f:
            files = {"file": ("test_document.md", f, "text/markdown")}
            response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
            
        assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "id" in data, "No id in response"
        STATE["document_id"] = data["id"]
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_ingestion_completes():
    doc_id = STATE.get("document_id")
    assert doc_id is not None, "Document ID not found from previous test"
    
    timeout = 30
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        if data["status"] == "completed":
            assert data.get("chunk_count", 0) > 0, "Chunk count should be > 0"
            return
        elif data["status"] == "failed":
            pytest.fail(f"Ingestion failed: {data.get('error_message')}")
            
        time.sleep(2)
        
    pytest.fail(f"Ingestion timed out after {timeout} seconds")

def test_chat_clear_match():
    payload = {"question": "Who is the lead engineer for Project Xyzzy?"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    
    assert "answer" in data
    assert "Samantha Carter" in data["answer"] or "Carter" in data["answer"], "Answer did not contain expected keyword"
    assert "citations" in data
    assert len(data["citations"]) > 0, "Citations list is empty"

def test_chat_not_in_document():
    payload = {"question": "What is the budget for Project Xyzzy?"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    answer_lower = data["answer"].lower()
    assert any(x in answer_lower for x in ["not find", "couldn't find", "don't have enough", "not mentioned", "not provided", "no information", "cannot answer"]), f"Fabricated answer detected: {data['answer']}"

def test_chat_nonsense():
    payload = {"question": "asdf qwerty!@#$"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    assert "answer" in data
    assert "citations" in data

```
### Test Run Output
```text
File does not exist or cannot be read: backend/pytest_snapshot.log```

## 7. Documentation State
### `docs/STUDY_GUIDE.md`
```markdown
# DocuMind AI — Personal Study Guide & Interview Notes

> **Purpose:** This document is a living study guide and technical cheat sheet for **DocuMind AI**. It captures every architectural decision, bug fix, and theoretical concept learned during development. Use this to review core engineering concepts and prepare for technical interviews.

---

## 📚 Table of Contents
1. [Phase 1: Foundation & Architecture Concepts](#phase-1-foundation--architecture-concepts)
   - [Why Python (FastAPI) vs. Java (Spring Boot)?](#1-why-python-fastapi-vs-java-spring-boot)
   - [What is Docker & Container Isolation? (The Port Remapping Lesson)](#2-what-is-docker--container-isolation-the-port-remapping-lesson)
   - [Synchronous vs. Asynchronous Execution (Why asyncpg?)](#3-synchronous-vs-asynchronous-execution-why-asyncpg)
   - [What is pgvector & Why Vector Databases?](#4-what-is-pgvector--why-vector-databases)
   - [Pydantic Schemas vs. ORM Models](#5-pydantic-schemas-vs-orm-models)
2. [Phase 2: Ingestion Pipeline Concepts](#phase-2-ingestion-pipeline-concepts)
3. [Phase 3: RAG Retrieval & LLM Generation](#phase-3-rag-retrieval--llm-generation)
4. [💡 Master Interview Cheat Sheet](#-master-interview-cheat-sheet)

---

## Phase 1: Foundation & Architecture Concepts

### 1. Why Python (FastAPI) vs. Java (Spring Boot)?
In general software engineering, **Java (Spring Boot)** is an enterprise giant used heavily in banking and legacy microservices. However, for modern **AI, LLM, and RAG applications**, **Python** is the industry standard.

#### The 3 Core Reasons:
1. **The Day-1 Ecosystem Advantage:** Almost every major AI research lab (OpenAI, Google DeepMind, Anthropic, Meta) releases their official SDKs in Python first. Crucial RAG libraries like **LangChain**, **LlamaIndex**, and **PyMuPDF** are Python-native. Java wrappers (like `Spring AI`) are often 6–12 months behind.
2. **Data & Vector Manipulation:** RAG pipelines require heavy unstructured data processing (stripping PDF text, chunking paragraphs, matrix math for embeddings). Python accomplishes in 15 readable lines what takes 50+ lines of stream boilerplate in Java.
3. **FastAPI Modern Design:** FastAPI provides native asynchronous I/O (`async/await`) out of the box, automatic Swagger/OpenAPI documentation generation, and Pydantic validation that handles messy LLM JSON payloads effortlessly.

---

### 2. What is Docker & Container Isolation? (The Port Remapping Lesson)
During Phase 1, we learned why containers are vital for consistent development.

#### The Concept:
A **Docker Container** is an isolated mini-computer running inside your machine with its own OS, dependencies, and file system. An **Image** (`pgvector/pgvector:pg16`) is the read-only blueprint, while the **Container** (`documind-db`) is the running instance.

#### The Real-World Port Collision We Solved:
* **The Bug:** When we first started Docker on port `5432`, our Python application crashed with `password authentication failed for user "documind"`.
* **The Cause:** Using terminal diagnostics (`netstat -ano`), we discovered that the Windows host machine already had a native PostgreSQL service running in the background on ports `5432` and `5433`. When Python connected to `localhost:5432`, Windows routed the traffic to the old local Windows database instead of our Docker container!
* **The Engineering Fix:** We remapped our Docker host binding in `docker-compose.yml` to **`5435:5432`** (Host Port 5435 -> Container Port 5432). Now, connecting to `localhost:5435` cleanly isolates our traffic into the Docker container without conflicting with native Windows services.

---

### 3. Synchronous vs. Asynchronous Execution (Why `asyncpg`?)
In traditional web frameworks (like Django or old Flask), database requests are **Synchronous (Blocking)**. 

* **Synchronous (Blocking):** When Server Thread A asks PostgreSQL for a record, the thread freezes completely until the database replies. If 1,000 users query at once, the server runs out of threads and crashes.
* **Asynchronous (Non-Blocking):** Using FastAPI and **SQLAlchemy 2.0 Async (`asyncpg`)**, when the server sends a database query, it says: *"I'm going to work on other user requests while you fetch that data. Wake me up when you have the answer."* This allows a single server process to handle thousands of concurrent I/O operations.

---

### 4. What is `pgvector` & Why Vector Databases?
Standard relational databases (like MySQL or plain PostgreSQL) search for exact keyword matches (SQL `LIKE '%keyword%'`). They do not understand *meaning* or *semantics*.

* **Vector Embeddings:** An AI embedding model (like Gemini `text-embedding-004`) converts sentences into lists of floating-point numbers called vectors (e.g., a 768-dimension array). Words with similar meanings point to similar directions in mathematical space.
* **`pgvector` Extension:** Transforms standard PostgreSQL into a vector database. It allows us to store 768-D vectors in SQL columns and use mathematical operators (like Cosine Similarity `<=>`) to find chunks of text that answer a user's question, even if they don't share exact keywords.

---

### 5. Pydantic Schemas vs. ORM Models
In professional backend architecture, we strictly separate our **Database Layer** from our **Network/API Layer**:

| Layer | Library | File Location | Purpose |
| :--- | :--- | :--- | :--- |
| **ORM Models** | `SQLAlchemy` | `app/models/` | Represents SQL database tables and relationships. Directly touches disk storage. |
| **API Schemas** | `Pydantic` | `app/schemas/` | Represents JSON data sent over HTTP. Validates types, enforces required fields, and sanitizes input/output before it ever touches the database. |

---

## Phase 2: Ingestion Pipeline Concepts

- [x] Document Parsing Strategies (PyMuPDF vs. OCR)
- [x] Chunking Algorithms (RecursiveCharacterTextSplitter & Overlap)
- [x] Vector Embedding Generation & Batching

### 1. Document Parsing Strategies (PyMuPDF vs. OCR)
In our pipeline, we use **PyMuPDF** to extract raw text and metadata (like page numbers) from digitally created PDFs. This is vastly faster and more accurate than OCR (Optical Character Recognition) tools like Tesseract, which are only necessary when dealing with scanned images where the text is baked into the pixels.

### 2. Chunking Algorithms (`RecursiveCharacterTextSplitter` & Overlap)
Large language models have finite context windows. We cannot feed a 500-page book at once.
* **Chunking:** We break documents down into smaller, digestible pieces (e.g., 800 characters).
* **`RecursiveCharacterTextSplitter`:** LangChain's smart algorithm that tries to split on paragraphs (`\n\n`) first, then sentences (`\n`), then words, keeping related ideas together rather than cutting words in half.
* **Overlap:** We use a 200-character overlap between chunks to ensure we don't accidentally split a key concept down the middle, preserving the context that connects adjacent chunks.

### 3. Vector Embedding Generation & Batching
Once we have chunks, we convert them into high-dimensional vectors (arrays of floating-point numbers) using `GoogleGenerativeAIEmbeddings` (`text-embedding-004`).
* **Batching:** Instead of sending chunks one by one across the network (which causes massive HTTP overhead), we batch them (e.g., 100 at a time). This optimizes network latency and throughput when talking to the LLM embedding provider via OmniRoute.
* **Storage:** These embeddings are saved in PostgreSQL using the `pgvector` extension to allow for semantic similarity searches later.

### 4. SQLAlchemy 1.4 vs 2.0 Type Hinting (`Column` vs `Mapped`)
Modern Python leans heavily on static type checking (like Pyright/Pylance).
* **The Bug:** Defining models with `status = Column(String)` caused type checkers to throw errors when we wrote `doc.status = "completed"` because they saw us assigning a string to a `Column` object.
* **The Fix:** We migrated our ORM models to SQLAlchemy 2.0 syntax using `Mapped[str] = mapped_column(String)`. This makes the models fully type-safe and eliminates IDE warnings.

### 5. Dynamic Configuration & Pydantic Validation
Hardcoding API keys or endpoints is a dangerous anti-pattern. We learned how to use `pydantic-settings` to load configurations from a `.env` file dynamically.
* **The Bug:** Our background worker was failing because it was hardcoded to hit a mock OmniRoute server (`http://localhost:20128`) even when we wanted to use a direct Google API key. Additionally, Pydantic's strict validation crashed the server when we added an un-registered `GOOGLE_API_KEY` to `.env`.
* **The Fix:** We properly registered `GOOGLE_API_KEY` inside `app/config.py` and rewrote the embedding initialization to dynamically check the environment variables and route traffic correctly without modifying source code.

---

## Phase 3: RAG Retrieval & LLM Generation

- [x] Cosine Similarity vs. Euclidean Distance
- [x] Prompt Engineering & Context Injection
- [x] LangChain Orchestration & Memory
- [x] Vector Indexing (`ivfflat` vs `hnsw`) & Async Caching

### 1. Cosine Similarity vs. Euclidean Distance
When `pgvector` compares a user's question to the document chunks, it needs a mathematical way to define "closeness."
*   **Euclidean Distance (L2):** Measures the straight-line distance between two points in space. If a document is very long, its vector magnitude might throw off the distance calculation.
*   **Cosine Similarity (Distance):** Measures the *angle* between two vectors, regardless of their magnitude (length). We use the `<=>` operator in pgvector for this. If two vectors point in the exact same direction (angle = 0), they are highly similar in meaning. This is the industry standard for LLM embeddings.

### 2. Prompt Engineering & Context Injection
LLMs like Gemini are prone to "hallucinations" (making up facts). To prevent this in a RAG system, we use **Context Injection**.
*   **The Workflow:** We intercept the user's question, perform the vector search, and then wrap both the retrieved chunks and the question in a strict `PromptTemplate`.
*   **The Guardrail:** Our prompt explicitly says: *"You are an expert AI assistant tasked with answering questions based ONLY on the provided context... If the answer is not contained in the context, say 'I don't have enough information'."* This locks the LLM into answering purely from our uploaded documents.

### 3. LangChain Orchestration
Instead of manually crafting HTTP requests to Google's API, we use LangChain's `ChatGoogleGenerativeAI`.
*   LangChain acts as the orchestration layer, utilizing the LCEL (LangChain Expression Language) syntax (`prompt | llm`) to chain the prompt construction directly into the LLM invocation, seamlessly parsing the asynchronous `ainvoke` responses into manageable Python objects.

### 4. Vector Indexing (`ivfflat` vs `hnsw`) & Async Caching
During Phase 3, we hit a critical bug where multi-turn queries returned `0` context chunks randomly when chained together, despite chunks existing in the database.
*   **The Bug:** We originally used an `ivfflat` index on our pgvector `embedding` column. `ivfflat` works by clustering data into "Voronoi partitions". However, on very small datasets (e.g., our small test documents), `ivfflat` fails dramatically because queries probe empty partitions and return zero rows, especially when combined with asyncpg prepared statement caching.
*   **The Fix:** We migrated the database index from `ivfflat` to **`HNSW` (Hierarchical Navigable Small World)**. HNSW builds a multi-layered graph linking nearest neighbors. It handles small datasets perfectly without "empty probe" issues, and natively avoids prepared statement cache conflicts in SQLAlchemy/asyncpg. We forced PostgreSQL to verify index usage using `EXPLAIN ANALYZE` and `SET enable_seqscan = off`.

### Phase 3 Verification & Testing

#### Test Idempotency
An integration test that uploads static content will pass once, then fail on every subsequent run — not because the app broke, but because the app correctly detected a duplicate via content hashing. The fix was to generate unique content per test run (embedding a fresh UUID) rather than reusing a static file. Lesson: a failing test can mean either "the feature broke" or "the test itself isn't idempotent" — distinguishing these is a core debugging skill, and the fix belongs in the test, not the app, when the app's behavior is actually correct.

---

## 💡 Master Interview Cheat Sheet

When an interviewer asks you about your technical decisions on DocuMind AI, use these exact, high-impact responses:

#### Q: "Why did you build this backend in Python instead of Java/Spring Boot?"
> *"I evaluate languages based on the specific workload. For heavy enterprise CRUD transaction engines, Java and Spring Boot are fantastic for their strict OOP contracts. However, for an AI/RAG application, Python is the industry standard. Building DocuMind AI in Python allowed me to leverage native LangChain orchestration, direct vector embedding manipulation, and FastAPI's asynchronous I/O and Pydantic validation—giving me production-grade AI capabilities that would require unnecessary boilerplate in Java."*

#### Q: "How did you handle database connectivity and scaling in your backend?"
> *"I implemented a non-blocking, asynchronous database access layer using **FastAPI**, **SQLAlchemy 2.0 Async ORM**, and the **asyncpg** driver. By utilizing asynchronous execution, server threads aren't blocked waiting for network I/O from the database, allowing the backend to handle high-concurrency RAG queries efficiently without thread exhaustion."*

#### Q: "Tell me about a technical challenge or debugging experience during database setup."
> *"During local environment provisioning with Docker Compose, I encountered password authentication failures because native Windows PostgreSQL background services were colliding on standard ports 5432 and 5433. Using process diagnostics, I identified the host-level socket collisions and remapped our container bindings to an isolated host port (5435), ensuring clean container networking without interfering with existing OS services."*

#### Q: "Why did you use PostgreSQL instead of a specialized vector DB like Pinecone or Weaviate?"
> *"I chose **PostgreSQL with the pgvector extension** to implement a unified transactional and vector store. Running separate databases for relational metadata and vector embeddings adds unnecessary network latency, distributed synchronization complexity, and operational overhead. With pgvector, I can perform ACID-compliant relational joins and cosine similarity vector searches within a single query engine."*

#### Q: "How do you ensure type safety between your database and API?"
> *"I use a combination of Pydantic for API validation and SQLAlchemy 2.0's `Mapped` syntax for ORM models. By explicitly typing model attributes with `Mapped[str] = mapped_column(...)`, I ensure full compatibility with static type checkers like Pyright. This eliminates runtime assignment errors and keeps the codebase incredibly robust."*

#### Q: "How did you manage environment configurations and secrets?"
> *"I utilized `pydantic-settings` to dynamically load environment variables from `.env` files. This enforces strict schema validation at startup—if a required key is missing or an invalid key is present, the application fails fast rather than crashing mid-execution. It also allowed me to seamlessly hot-swap between a local OmniRoute mock server and a live Google API endpoint without altering business logic."*

#### Q: "Tell me about a time you solved a complex production database bug."
> *"While implementing multi-turn RAG retrieval, I encountered a bug where vector searches inconsistently returned zero rows on subsequent queries. I traced the issue to how PostgreSQL's query planner interacts with `asyncpg` prepared statement caching and the `ivfflat` vector index. Because `ivfflat` relies on Voronoi partitioning, small datasets often lead to probing empty partitions, which was exacerbated by cached execution plans. I solved this by migrating the embedding index to `HNSW` (Hierarchical Navigable Small World), which uses graph-based traversal, perfectly bypassing the empty-probe limitation on small datasets while maintaining high retrieval performance at scale. I verified the fix directly in the DB using `EXPLAIN ANALYZE`."*

```
### `docs/PRD.md`
`docs/PRD.md` does not exist.
### `README.md`
Same as Project Identity (does not exist).

## 8. Git State
### `git log --oneline`
```text
7075efe3 Phase 3 complete: RAG Q&A engine verified with full integration test suite (6/6 passing)
```
### `git status`
```text
On branch master
Untracked files:
  (use "git add <file>..." to include in what will be committed)
	tree_output.txt

no changes added to commit (use "git add" and/or "git commit -a")
```

## 9. Environment
### `.env.example`
```text
# DocuMind AI — Environment Variables
# Copy this to .env and fill in your values.

# Database
DATABASE_URL=postgresql+asyncpg://documind:documind_dev@localhost:5435/documind
DATABASE_URL_SYNC=postgresql://documind:documind_dev@localhost:5435/documind

# OmniRoute / LLM
OMNIROUTE_BASE_URL=http://localhost:20128
OMNIROUTE_MODEL=auto
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768

# RAG Settings
CHUNK_SIZE=800
CHUNK_OVERLAP=200
TOP_K=5
SIMILARITY_THRESHOLD=0.3

# Upload
MAX_FILE_SIZE_MB=50
UPLOAD_DIR=./uploads

# CORS (comma-separated if multiple)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Debug
DEBUG=true

```
### `docker-compose.yml`
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: documind-db
    environment:
      POSTGRES_DB: documind
      POSTGRES_USER: documind
      POSTGRES_PASSWORD: documind_dev
    ports:
      - "5435:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U documind -d documind"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: ./backend
    container_name: documind-api
    environment:
      DATABASE_URL: "postgresql+asyncpg://documind:documind_dev@db:5432/documind"
      DATABASE_URL_SYNC: "postgresql://documind:documind_dev@db:5432/documind"
      OMNIROUTE_BASE_URL: "http://host.docker.internal:20128"
      OMNIROUTE_MODEL: "auto"
      EMBEDDING_MODEL: "text-embedding-004"
      DEBUG: "true"
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - uploads:/app/uploads
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:
  uploads:

```