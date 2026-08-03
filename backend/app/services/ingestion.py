import os
import uuid
import logging
from pathlib import Path
from typing import Optional

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Document, Chunk
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize the embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY,
    timeout=30.0,
)


import base64
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_RATE_LIMIT_ERR_MARKERS = ("429", "Quota exceeded", "ResourceExhausted", "rate limit")


def _is_rate_limit(exc: Exception) -> bool:
    err_str = str(exc)
    return any(marker.lower() in err_str.lower() for marker in _RATE_LIMIT_ERR_MARKERS)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _embed_texts(texts: list[str]):
    """Embed a batch of texts with retry on transient rate limits/network errors."""
    try:
        return await embeddings.aembed_documents(texts)
    except Exception as exc:
        logger.warning(f"Embedding batch failed ({len(texts)} texts): {exc}")
        raise


def _normalize_embedding(vector: list, dimension: int) -> list:
    """Ensure the embedding vector matches the configured dimension."""
    if len(vector) != dimension:
        logger.warning(f"Embedding dimension mismatch: got {len(vector)}, expected {dimension}. Adjusting.")
    if len(vector) > dimension:
        return vector[:dimension]
    return vector + [0.0] * (dimension - len(vector))


async def _ocr_pdf_page(page) -> str:
    """Fallback OCR for scanned PDF pages using Gemini Vision REST API."""
    if not settings.GOOGLE_API_KEY:
        return ""
    try:
        pix = page.get_pixmap(dpi=150)
        img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        model = settings.GENERATIVE_MODEL if "gemini" in settings.GENERATIVE_MODEL.lower() else "gemini-3.6-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GOOGLE_API_KEY}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extract and transcribe all text from this scanned document image accurately. Return only the extracted text."},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }]
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
    except Exception as e:
        logger.warning(f"OCR fallback failed for page: {e}")
    return ""


def _resolve_file_path(doc: Document, file_path: Optional[str] = None) -> str:
    """Derive the on-disk path for a document if one was not supplied."""
    if file_path:
        return file_path
    ext = doc.file_type if doc.file_type != "markdown" else "md"
    return str(Path(settings.UPLOAD_DIR) / f"{doc.id}.{ext}")


async def _ingest_pipeline(db: AsyncSession, doc: Document, file_path: Optional[str] = None) -> None:
    """
    Core chunking + embedding pipeline: parse text, chunk, embed, and insert rows.

    Raises RuntimeError (or the underlying exception) on any failure so the
    caller — the ingestion state machine — can persist the terminal 'error' status.
    On success the caller is responsible for committing 'completed'.
    """
    file_path = _resolve_file_path(doc, file_path)

    if not os.path.exists(file_path):
        raise RuntimeError(f"File not found: {file_path}")

    # 2. Parse text
    logger.info(f"Parsing file: {file_path}")
    pages = []
    if doc.file_type == "pdf":
        with pymupdf.open(file_path) as pdf:
            doc.page_count = len(pdf)
            for i, page in enumerate(pdf):
                text = page.get_text()
                if not text or not text.strip():
                    logger.info(f"Page {i+1} has no vector text, running Gemini OCR fallback...")
                    text = await _ocr_pdf_page(page)

                if text and text.strip():
                    pages.append({"text": text.strip(), "page_number": i + 1})
    elif doc.file_type == "markdown":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
            if text and text.strip():
                pages.append({"text": text.strip(), "page_number": 1})
            doc.page_count = 1
    else:
        raise RuntimeError(f"Unsupported file type: {doc.file_type}")

    if not pages:
        raise RuntimeError("No readable text found in document. Please upload a searchable PDF or Markdown file.")

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
        raise RuntimeError("No readable text chunks could be extracted.")

    logger.info(f"Extracted {len(chunks_data)} chunks from document {doc.id}")

    # 4. Generate Embeddings & 5. Insert into DB
    logger.info(f"Generating embeddings for {len(chunks_data)} chunks...")
    batch_size = 100
    total_inserted = 0

    for i in range(0, len(chunks_data), batch_size):
        batch_chunks = chunks_data[i:i + batch_size]
        texts = [c["text"] for c in batch_chunks]

        # Generate embeddings (retried on transient rate limits/network errors)
        vectors = await _embed_texts(texts)

        # Insert chunks
        for data, vector in zip(batch_chunks, vectors):
            db_chunk = Chunk(
                document_id=doc.id,
                chunk_index=data["index"],
                content=data["text"],
                metadata_=data["metadata"],
                embedding=_normalize_embedding(vector, settings.EMBEDDING_DIMENSION),
                token_count=len(data["text"]) // 4  # Rough token estimation
            )
            db.add(db_chunk)

        total_inserted += len(batch_chunks)

    logger.info(f"Successfully prepared {total_inserted} embeddings for pgvector.")


async def ingest_document(document_id: str, file_path: Optional[str] = None):
    """
    Backwards-compatible entry point: ingest a single document by id.
    Still used by legacy BackgroundTasks wiring and tests; the durable
    outbox worker (process_pending_documents) is the production path.
    """
    logger.info(f"Starting ingestion for document_id: {document_id}")

    async with async_session() as db:
        try:
            doc_uuid = uuid.UUID(document_id)
            result = await db.execute(select(Document).where(Document.id == doc_uuid))
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error(f"Document {document_id} not found in database for ingestion.")
                return

            doc.status = "processing"
            doc.error_message = None
            await db.commit()

            await _ingest_pipeline(db, doc, file_path)
            doc.status = "completed"
            doc.error_message = None
            await db.commit()
            logger.info(f"Ingestion completed successfully for document {document_id}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Ingestion failed for document {document_id}: {e}", exc_info=True)
            await db.execute(
                update(Document)
                .where(Document.id == uuid.UUID(document_id))
                .values(status="error", error_message=str(e))
            )
            await db.commit()


async def process_pending_documents(db: AsyncSession) -> int:
    """
    Transactional outbox / state-machine worker for the ingestion pipeline.

    Durably claims one 'pending' document at a time via a Postgres row-level
    lock (FOR UPDATE SKIP LOCKED) so concurrent workers never double-process,
    marks it 'processing', then runs the chunking/embedding pipeline in a
    strict try/except: success commits 'completed', any failure commits
    'error' with the stack trace logged. Crash-safe: a 'processing' row is a
    claim that survived, and 'pending' rows are always re-attempted.

    SELECT id FROM documents WHERE status = 'pending' LIMIT 1 FOR UPDATE SKIP LOCKED
    """
    processed = 0

    while True:
        # 1. Atomically claim the oldest pending job (SKIP LOCKED: skip rows
        #    locked by other workers instead of blocking).
        claim_stmt = (
            select(Document.id)
            .where(Document.status == "pending")
            .order_by(Document.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        doc_id = (await db.execute(claim_stmt)).scalar_one_or_none()
        if doc_id is None:
            break

        # 2. Transition pending -> processing (durable claim)
        await db.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(status="processing", error_message=None)
        )
        await db.commit()

        try:
            doc = await db.get(Document, doc_id)
            if doc is None:
                logger.warning(f"Document {doc_id} was deleted after being claimed; skipping.")
                continue

            # 3. Chunking/embedding pipeline (strict try/except)
            await _ingest_pipeline(db, doc)

            # 4a. Success: processing -> completed
            doc.status = "completed"
            doc.error_message = None
            await db.commit()
            logger.info(f"Ingestion completed successfully for document {doc_id}")

        except Exception as e:
            # 4b. Failure: processing -> error (discard partial chunk rows first)
            await db.rollback()
            logger.error(f"Ingestion pipeline failed for document {doc_id}: {e}", exc_info=True)
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(status="error", error_message=str(e))
            )
            await db.commit()

        processed += 1

    return processed
