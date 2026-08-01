"""
DocuMind AI - Chat Router
RAG Q&A engine endpoint for natural language document querying with multi-turn memory.
"""

import time
import uuid

from json import dumps
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message, QueryLog
from app.schemas import ChatRequest, ChatResponse, Citation
from app.services.retrieval import retrieve_context
from app.services.generation import generate_answer, generate_answer_stream, RateLimitError

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge base using Retrieval-Augmented Generation (RAG)
    with multi-turn conversation memory.
    """
    start_time = time.time()

    try:
        # 1. Session Management
        conversation_id = request.conversation_id
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                raise HTTPException(
                    status_code=404, detail=f"Conversation {conversation_id} not found."
                )
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

        # 8. Persist QueryLog for analytics
        query_log = QueryLog(
            id=uuid.uuid4(),
            question=request.question,
            retrieved_chunks=citation_dicts,
            top_k=request.top_k,
            avg_similarity=avg_similarity,
            latency_ms=latency_ms,
        )
        db.add(query_log)
        await db.commit()

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
        raise HTTPException(status_code=500, detail=f"RAG engine failed: {str(e)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Query the knowledge base using RAG with real-time SSE token streaming.
    """
    start_time = time.time()

    # 1. Session Management
    conversation_id = request.conversation_id
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found."
            )
    else:
        conv = Conversation(id=uuid.uuid4(), title=request.question[:50])
        db.add(conv)
        await db.flush()
        conversation_id = conv.id

    # 2. Fetch past history
    hist_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    chat_history = list(hist_result.scalars().all())[-10:]

    # 3. Save user's question
    user_msg = Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)
    await db.flush()

    # 4. Retrieve context chunks
    retrieved_items = await retrieve_context(
        query=request.question, db=db, document_id=request.document_id
    )
    chunks = [item[0] for item in retrieved_items]

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
                no_info = "I couldn't find any relevant information in the uploaded documents to answer your question."
                full_answer.append(no_info)
                token_payload = dumps({"delta": no_info})
                yield f"event: token\ndata: {token_payload}\n\n"
            else:
                async for token in generate_answer_stream(
                    query=request.question, chunks=chunks, chat_history=chat_history
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
                question=request.question,
                retrieved_chunks=citation_dicts,
                top_k=request.top_k,
                avg_similarity=avg_similarity,
                latency_ms=latency_ms,
            )
            db.add(query_log)
            await db.commit()

            done_payload = dumps({"latency_ms": latency_ms})
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as e:
            await db.rollback()
            err_payload = dumps({"detail": str(e)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
