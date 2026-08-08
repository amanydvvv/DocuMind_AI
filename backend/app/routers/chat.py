"""
DocuMind AI - Chat Router
RAG Q&A engine endpoint for natural language document querying with multi-turn memory and user tenant isolation.
"""

import logging
import time
import uuid
from json import dumps

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message, QueryLog, Document
from app.models.user import User
from app.core.ratelimit import limiter
from app.core.security import get_current_user
from app.schemas import ChatRequest, ChatResponse, Citation
from app.services.retrieval import retrieve_context
from app.services.memory import update_conversation_summary
from app.services.generation import (
    generate_answer,
    generate_answer_stream,
    build_token_budgeted_history,
    RateLimitError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


async def _build_corpus_metadata(db: AsyncSession, user_id) -> str:
    """Query the user's actual document count and filenames (ground truth for the LLM)."""
    count_result = await db.execute(
        select(func.count(Document.id)).where(
            Document.user_id == user_id,
            Document.status == "completed",
        )
    )
    doc_count = count_result.scalar_one()

    name_result = await db.execute(
        select(Document.filename).where(
            Document.user_id == user_id,
            Document.status == "completed",
        ).distinct()
    )
    filenames = [row[0] for row in name_result.all()]

    return (
        f"CORPUS METADATA (ground truth — use this for any question about how many "
        f"documents exist or what documents exist, do NOT count retrieved chunks as "
        f"documents): You have {doc_count} document(s): {', '.join(filenames)}"
    )


def _deduplicate_citations(citations: list) -> list:
    """Keep one citation per document_id (the highest scored chunk)."""
    seen = {}
    for cit in citations:
        doc_id = str(cit.document_id)
        if doc_id not in seen or cit.score > seen[doc_id].score:
            seen[doc_id] = cit
    return list(seen.values())


@router.post("", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(
    request: Request,
    request_body: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Query the knowledge base using Retrieval-Augmented Generation (RAG)
    with multi-turn conversation memory, scoped to current user.
    """
    start_time = time.time()

    try:
        # 1. Session Management
        conversation_id = request_body.conversation_id
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
            conv = result.scalar_one_or_none()
            if not conv:
                raise HTTPException(
                    status_code=404, detail=f"Conversation {conversation_id} not found."
                )
        else:
            conv = Conversation(
                id=uuid.uuid4(),
                user_id=current_user.id,
                title=request_body.question[:50]
            )
            db.add(conv)
            await db.flush()
            conversation_id = conv.id

        # 2. Fetch past conversation history (newest first; token budget applied below)
        hist_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        chat_history = build_token_budgeted_history(hist_result.scalars().all())

        # 3. Save user's question as a Message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=request_body.question,
        )
        db.add(user_msg)
        await db.flush()

        # 4. Query corpus metadata (ground truth for the LLM)
        corpus_metadata = await _build_corpus_metadata(db, current_user.id)

        # 5. Retrieve relevant chunks from pgvector scoped to current user
        retrieved_items = await retrieve_context(
            query=request_body.question,
            db=db,
            document_id=request_body.document_id,
            user_id=current_user.id,
            top_k=request_body.top_k,
        )

        chunks = [item[0] for item in retrieved_items]

        # 6. Build citations list with real score & filename
        citations = []
        similarity_scores = []
        for chunk, score, filename in retrieved_items:
            page_num = (
            chunk.page_number
            if chunk.page_number is not None
            else (chunk.metadata_.get("page_number", None) if chunk.metadata_ else None)
        )
            source = chunk.metadata_.get("source", None) if chunk.metadata_ else None
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
                    source=source,
                )
            )

        # Deduplicate citations: one per document, keeping highest score
        citations = _deduplicate_citations(citations)

        avg_similarity = (
            round(sum(similarity_scores) / len(similarity_scores), 4)
            if similarity_scores
            else 0.0
        )

        # 7. Generate answer using Groq (Llama 3.1) with chat history + corpus metadata
        if not chunks:
            answer = "I couldn't find any relevant information in your uploaded documents to answer your question."
        else:
            answer = await generate_answer(
                query=request_body.question,
                chunks=chunks,
                chat_history=chat_history,
                corpus_metadata=corpus_metadata,
                conversation_summary=conv.context_summary,
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # 8. Save assistant's answer as a Message
        citation_dicts = [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "filename": c.filename,
                "page_number": c.page_number,
                "score": c.score,
                "content_preview": c.content_preview,
                "source": c.source,
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

        # 9. Persist QueryLog for analytics
        query_log = QueryLog(
            id=uuid.uuid4(),
            user_id=current_user.id,
            question=request_body.question,
            retrieved_chunks=citation_dicts,
            top_k=request_body.top_k,
            avg_similarity=avg_similarity,
            latency_ms=latency_ms,
        )
        db.add(query_log)
        await db.commit()

        # Summary Buffer Memory: summarize the last 5 messages in the background.
        # The service opens its own session (request-scoped db is closed by then).
        background_tasks.add_task(update_conversation_summary, conversation_id)

        return ChatResponse(
            answer=answer,
            citations=citations,
            conversation_id=conversation_id,
            latency_ms=latency_ms,
            avg_similarity=avg_similarity,
        )

    except RateLimitError as e:
        await db.rollback()
        raise HTTPException(status_code=429, detail=str(e))
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Chat endpoint failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")


@router.post("/stream")
@limiter.limit("10/minute")
async def chat_stream(
    request: Request,
    request_body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Query the knowledge base using RAG with real-time SSE token streaming, scoped to current user.
    """
    start_time = time.time()

    # 1. Session Management
    conversation_id = request_body.conversation_id
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found."
            )
    else:
        conv = Conversation(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title=request_body.question[:50]
        )
        db.add(conv)
        await db.flush()
        conversation_id = conv.id

    # 2. Fetch past history (newest first; token budget applied below)
    hist_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
    )
    chat_history = build_token_budgeted_history(hist_result.scalars().all())

    # 3. Save user's question
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=request_body.question,
    )
    db.add(user_msg)
    await db.flush()

    # 4. Query corpus metadata (ground truth for the LLM)
    corpus_metadata = await _build_corpus_metadata(db, current_user.id)

    # 5. Retrieve context chunks scoped to user
    retrieved_items = await retrieve_context(
        query=request_body.question,
        db=db,
        document_id=request_body.document_id,
        user_id=current_user.id,
        top_k=request_body.top_k,
    )
    chunks = [item[0] for item in retrieved_items]

    citations = []
    similarity_scores = []
    for chunk, score, filename in retrieved_items:
        page_num = (
            chunk.page_number
            if chunk.page_number is not None
            else (chunk.metadata_.get("page_number", None) if chunk.metadata_ else None)
        )
        source = chunk.metadata_.get("source", None) if chunk.metadata_ else None
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
                source=source,
            )
        )

    # Deduplicate citations: one per document, keeping highest score
    citations = _deduplicate_citations(citations)

    avg_similarity = (
        round(sum(similarity_scores) / len(similarity_scores), 4)
        if similarity_scores
        else 0.0
    )

    citation_dicts = [
        {
            "id": str(c.chunk_id),
            "chunk_id": str(c.chunk_id),
            "document_id": str(c.document_id),
            "filename": c.filename,
            "page_number": c.page_number,
            "score": c.score,
            "content_preview": c.content_preview,
            "source": c.source,
        }
        for c in citations
    ]

    async def event_generator():
        full_answer = []
        try:
            # Event 1: Metadata
            meta_payload = dumps({
                "conversation_id": str(conversation_id),
                "citations": citation_dicts,
                "avg_similarity": avg_similarity
            })
            yield f"event: metadata\ndata: {meta_payload}\n\n"

            if not chunks:
                no_info = "I couldn't find any relevant information in your uploaded documents to answer your question."
                full_answer.append(no_info)
                token_payload = dumps({"delta": no_info})
                yield f"event: token\ndata: {token_payload}\n\n"
            else:
                async for token in generate_answer_stream(
                    query=request_body.question,
                    chunks=chunks,
                    chat_history=chat_history,
                    corpus_metadata=corpus_metadata,
                    conversation_summary=conv.context_summary,
                ):
                    full_answer.append(token)
                    token_payload = dumps({"delta": token})
                    yield f"event: token\ndata: {token_payload}\n\n"

            complete_text = "".join(full_answer)
            latency_ms = int((time.time() - start_time) * 1000)

            # Persist assistant message & query log
            assistant_msg = Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role="assistant",
                content=complete_text,
                citations=citation_dicts,
                latency_ms=latency_ms,
            )
            db.add(assistant_msg)

            query_log = QueryLog(
                id=uuid.uuid4(),
                user_id=current_user.id,
                question=request_body.question,
                retrieved_chunks=citation_dicts,
                top_k=request_body.top_k,
                avg_similarity=avg_similarity,
                latency_ms=latency_ms,
            )
            db.add(query_log)
            await db.commit()

            done_payload = dumps({"latency_ms": latency_ms})
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception:
            await db.rollback()
            err_payload = dumps({"detail": "An internal error occurred during generation."})
            yield f"event: error\ndata: {err_payload}\n\n"

    # Summary Buffer Memory: summarize the last 5 messages once the stream
    # finishes. The service opens its own isolated session, so it is safe to
    # run after the request-scoped db is closed.
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        background=BackgroundTask(update_conversation_summary, conversation_id),
    )
