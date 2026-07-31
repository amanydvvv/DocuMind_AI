"""
DocuMind AI — Conversations Router
Endpoints for managing multi-turn conversation sessions and viewing historical message threads.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Conversation, Message
from app.schemas import (
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversation sessions ordered by last update time."""
    total_res = await db.execute(select(func.count(Conversation.id)))
    total = total_res.scalar_one()

    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()

    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                title=c.title,
                messages=[],
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Get full conversation details including chronologically ordered messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found."
        )

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        messages=[MessageResponse.model_validate(m) for m in messages],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID, db: AsyncSession = Depends(get_db)
):
    """Delete a conversation session and its associated messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=404, detail=f"Conversation {conversation_id} not found."
        )

    await db.delete(conv)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
