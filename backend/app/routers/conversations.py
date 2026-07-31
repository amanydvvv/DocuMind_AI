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
