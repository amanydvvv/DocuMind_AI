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
