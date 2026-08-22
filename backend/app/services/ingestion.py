import asyncio
import os
import tempfile
import uuid
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Document, Chunk
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize the embedding model (Groq has no embedding API — Gemini stays)
embeddings = GoogleGenerativeAIEmbeddings(
    model=f"models/{settings.EMBEDDING_MODEL}",
    google_api_key=settings.GEMINI_API_KEY or "dummy-key-for-init",
    timeout=30.0,
)

# OpenAI-compatible client pointed at Groq Cloud. Tight timeout (30s) and a
# single retry so a hung OCR/vision call degrades to the guardrail within
# ~60s worst case (30s attempt + 30s retry) instead of stalling the
# ingestion worker for the openai default of 600s and multiple retries.
groq_client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY or "dummy-key-for-init",
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0,
    max_retries=1,
)


import base64
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_RATE_LIMIT_ERR_MARKERS = ("429", "Quota exceeded", "ResourceExhausted", "rate limit")


def _strip_think_blocks(text: str) -> str | None:
    """Remove <think>...</think> reasoning traces from thinking-model output.

    Returns None when a <think> block is unclosed — i.e. the model response was
    truncated mid-reasoning — so callers can treat the page as failed OCR
    instead of embedding reasoning text that would surface in citations.
    """
    if "<think>" not in text:
        return text.replace("</think>", "")
    while True:
        start = text.find("<think>")
        end = text.find("</think>", start)
        if start == -1 or end == -1:
            break
        text = text[:start] + text[end + len("</think>"):]
    if "<think>" in text:
        return None
    return text.replace("</think>", "")


def _is_rate_limit(exc: Exception) -> bool:
    err_str = str(exc)
    return any(marker.lower() in err_str.lower() for marker in _RATE_LIMIT_ERR_MARKERS)


# --- Pre-flight OCR image-quality gate -------------------------------------
# Empirically calibrated at dpi=150 (the render the vision model actually sees)
# against the Part 6 regression samples:
#   blank.pdf      intensity_std=0.0      edge_frac>30=0.0      grad_mean=0.0
#   noise.pdf      intensity_std=61.2     edge_frac>30=0.1233   grad_mean=8.25
#   live_scan.pdf  intensity_std=31.0     edge_frac>30=0.0158   grad_mean=1.66
# A variance-only check is provably insufficient (noise 61.2 vs scan 31.0
# overlap), and edge density alone has only ~8x separation; the composite
# below rejects structureless noise with ~2x headroom on both axes while real
# scans sit 3-5x clear.
_BLANK_PAGE_STD_THRESHOLD = 2.0
_NOISE_GRAD_MEAN_THRESHOLD = 4.5
_NOISE_EDGE_FRACTION_THRESHOLD = 0.06
_EDGE_GRADIENT_THRESHOLD = 30.0


def _page_metrics_from_samples(samples) -> tuple:
    """Compute (intensity_std, grad_mean, edge_fraction) for a grayscale image.

    edge_fraction is the share of pixels whose gradient magnitude exceeds
    _EDGE_GRADIENT_THRESHOLD. Real documents have sparse strong edges (text
    strokes) on mostly-flat regions; pure random noise has dense, uniformly
    weak gradients — the two statistics together separate them reliably.
    """
    arr = samples.astype(np.float32)
    intensity_std = float(arr.std())
    gy, gx = np.gradient(arr)
    grad_mag = np.sqrt(gx * gx + gy * gy)
    grad_mean = float(grad_mag.mean())
    edge_fraction = float((grad_mag > _EDGE_GRADIENT_THRESHOLD).mean())
    return intensity_std, grad_mean, edge_fraction


def _gate_decision(intensity_std: float, grad_mean: float, edge_fraction: float) -> tuple:
    """Classify a page as blank / structureless noise / readable.

    Returns (is_blank, is_noise). Blank pages have near-zero intensity
    variance; pure noise has high mean gradient AND dense edge pixels, while
    real content keeps both low (sparse strong edges on flat background).
    """
    is_blank = intensity_std < _BLANK_PAGE_STD_THRESHOLD
    is_noise = (
        grad_mean > _NOISE_GRAD_MEAN_THRESHOLD
        and edge_fraction > _NOISE_EDGE_FRACTION_THRESHOLD
    )
    return is_blank, is_noise


def _is_unreadable_page(pix) -> bool:
    """Pre-flight gate: reject blank and structureless-noise pages before OCR.

    Skips the Groq vision call entirely for pages that cannot contain text,
    degrading them to the same 'no readable text' guardrail as OCR failure.
    """
    gray = pymupdf.Pixmap(pymupdf.csGRAY, pix)
    samples = np.frombuffer(gray.samples, dtype=np.uint8).reshape(gray.height, gray.width)
    intensity_std, grad_mean, edge_fraction = _page_metrics_from_samples(samples)
    is_blank, is_noise = _gate_decision(intensity_std, grad_mean, edge_fraction)
    if is_blank or is_noise:
        logger.warning(
            "Pre-flight OCR gate rejected page: intensity_std=%.2f grad_mean=%.2f "
            "edge_fraction=%.4f (blank=%s, noise=%s)",
            intensity_std, grad_mean, edge_fraction, is_blank, is_noise,
        )
        return True
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _embed_texts(texts: list[str]):
    """Embed a batch of texts with retry on transient rate limits/network errors."""
    try:
        return await asyncio.to_thread(
            embeddings.embed_documents,
            texts,
            output_dimensionality=settings.EMBEDDING_DIMENSION,
        )
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


_UNREADABLE_TOKEN = "[UNREADABLE]"

_OCR_PROMPT_TEXT = (
    "Extract and transcribe all text from this scanned document image accurately. "
    "Write each line exactly once, in reading order. Return only the extracted text. "
    "If you cannot confidently transcribe real text from this image (for example a "
    "blank page, pure noise, or an unreadable scan), respond with EXACTLY the literal "
    "token [UNREADABLE] and nothing else. Do not write explanations or hedging such "
    "as 'the image is unclear' — your entire response must be exactly the token "
    "[UNREADABLE] when you cannot transcribe the text."
)


async def _ocr_pdf_page(page) -> str:
    """Fallback OCR for scanned PDF pages using Groq vision model."""
    if not settings.GROQ_API_KEY:
        return ""
    try:
        pix = page.get_pixmap(dpi=150)
        if _is_unreadable_page(pix):
            # Pre-flight quality gate rejected page (blank or structureless noise)
            return ""
        img_b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
        data_url = f"data:image/png;base64,{img_b64}"
        resp = await groq_client.chat.completions.create(
            model=settings.VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _OCR_PROMPT_TEXT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            max_tokens=2000,
        )
        cleaned = _strip_think_blocks(resp.choices[0].message.content)
        if cleaned is None:
            # Response was truncated mid-reasoning: embedding the partial
            # reasoning text could surface it in citations, so fail the page
            # and let the "no readable text" guardrail handle it.
            logger.warning("OCR response truncated mid-reasoning; treating page as failed OCR")
            return ""

        cleaned_str = cleaned.strip()
        if cleaned_str == _UNREADABLE_TOKEN or cleaned_str.startswith(_UNREADABLE_TOKEN):
            logger.warning("OCR model returned sentinel token [UNREADABLE]; treating page as failed OCR")
            return ""

        return cleaned_str
    except Exception as e:
        # Timeout, rate limit, network, and model errors all land here and
        # degrade to the guardrail rejection below.
        logger.warning(f"OCR fallback failed for page: {e}")
    return ""


def _resolve_file_path(doc: Document, file_path: Optional[str] = None) -> str:
    """Derive the on-disk path for a document if one was not supplied."""
    if file_path and os.path.exists(file_path):
        return file_path
    if doc.raw_bytes:
        ext = doc.file_type if doc.file_type != "markdown" else "md"
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(doc.raw_bytes)
            return tmp.name
    ext = doc.file_type if doc.file_type != "markdown" else "md"
    return str(Path(settings.UPLOAD_DIR) / f"{doc.id}.{ext}")


async def _generate_display_title(first_page_text: str, filename: str) -> str:
    """Generate a short human-readable title for the document using a fast model call."""
    if not settings.GROQ_API_KEY:
        return filename
    try:
        sample_text = first_page_text[:1500]
        prompt = (
            f"Based on the following document sample and filename, generate a concise, human-readable title "
            f"(3 to 7 words) that describes the document (e.g. 'Two-Wheeler Insurance Policy' or 'Q3 Financial Report'). "
            f"Return ONLY the title text, with no quotes, explanations, or leading/trailing punctuation.\n\n"
            f"Filename: {filename}\n"
            f"Document Sample:\n{sample_text}"
        )
        resp = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.1,
        )
        title = resp.choices[0].message.content.strip().strip('"').strip("'")
        if title:
            return title
    except Exception as e:
        logger.warning(f"Display title generation failed for {filename}: {e}")
    return filename


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

    # Track if this is a temp file we should clean up (only files under system temp dir)
    is_temp_file = file_path.startswith(tempfile.gettempdir())

    try:
        # 2. Parse text
        logger.info(f"Parsing file: {file_path}")
        pages = []
        if doc.file_type == "pdf":
            with pymupdf.open(file_path) as pdf:
                doc.page_count = len(pdf)
                for i, page in enumerate(pdf):
                    text = page.get_text()
                    source = "text"
                    if not text or not text.strip():
                        logger.info(f"Page {i+1} has no vector text, running Groq OCR fallback...")
                        text = await _ocr_pdf_page(page)
                        source = "ocr"

                    if text and text.strip():
                        pages.append({"text": text.strip(), "page_number": i + 1, "source": source})
        elif doc.file_type == "markdown":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                if text and text.strip():
                    pages.append({"text": text.strip(), "page_number": 1, "source": "text"})
                doc.page_count = 1
        else:
            raise RuntimeError(f"Unsupported file type: {doc.file_type}")

        if not pages:
            raise RuntimeError("No readable text found in document. Please upload a searchable PDF or Markdown file.")

        # Generate human-readable display title if missing
        display_title = await _generate_display_title(pages[0]["text"], doc.filename)
        doc.display_title = display_title

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
                        "display_title": doc.display_title or doc.filename,
                        "source": page.get("source", "text"),
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
                    page_number=data["metadata"].get("page_number"),
                    metadata_=data["metadata"],
                    embedding=_normalize_embedding(vector, settings.EMBEDDING_DIMENSION),
                    token_count=len(data["text"]) // 4  # Rough token estimation
                )
                db.add(db_chunk)

            total_inserted += len(batch_chunks)

        logger.info(f"Successfully prepared {total_inserted} embeddings for pgvector.")
    finally:
        # Clean up temp file created for ingestion (only if under system temp dir)
        if is_temp_file and file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.debug(f"Cleaned up temp ingestion file: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up temp file {file_path}: {e}")


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
