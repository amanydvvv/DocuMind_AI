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

# Initialize the embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GOOGLE_API_KEY,
)


from typing import Optional

import base64
import httpx


async def _ocr_pdf_page(page) -> str:
    """Fallback OCR for scanned PDF pages using Gemini Vision REST API."""
    if not settings.GOOGLE_API_KEY:
        return ""
    try:
        pix = page.get_pixmap(dpi=150)
        img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        model = settings.GENERATIVE_MODEL if "gemini" in settings.GENERATIVE_MODEL.lower() else "gemini-1.5-flash"
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


async def ingest_document(document_id: str, file_path: Optional[str] = None):
    """
    Background task to ingest a document: extract text, chunk, embed, and store in the DB.
    Bulletproofed with robust error handling, scanned PDF OCR fallback, and logging.
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
                    raise ValueError(f"Unsupported file type: {doc.file_type}")
            except Exception as e:
                logger.error(f"Failed to parse document {document_id}: {e}", exc_info=True)
                doc.status = "error"
                doc.error_message = f"Parsing error: {str(e)}"
                await db.commit()
                return

            if not pages:
                logger.warning(f"No text extracted from document {document_id}")
                doc.status = "error"
                doc.error_message = "No readable text found in document. Please upload a searchable PDF or Markdown file."
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
                doc.status = "error"
                doc.error_message = "No readable text chunks could be extracted."
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
