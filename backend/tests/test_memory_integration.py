"""
KueryCore AI — Summary Buffer Memory Integration Test
Verifies update_conversation_summary persists a clean, preamble-free summary
for a conversation with >= 2 messages, using its own isolated session.
"""

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import async_session
from app.models import User, Conversation, Message
from app.services.memory import update_conversation_summary


@pytest.mark.asyncio
async def test_update_conversation_summary_persists_clean_summary():
    user_id = None
    conv_id = None
    try:
        # Setup: temporary user + conversation
        async with async_session() as db:
            user = User(
                id=uuid.uuid4(),
                email=f"memory_test_{uuid.uuid4().hex[:6]}@example.com",
                hashed_password=hash_password("TestPass123!"),
                is_active=True,
            )
            db.add(user)
            await db.flush()
            user_id = user.id

            conv = Conversation(
                id=uuid.uuid4(),
                user_id=user.id,
                title="Memory integration test",
            )
            db.add(conv)
            await db.flush()
            conv_id = conv.id

            # Seed: 1 user message + 1 assistant message
            db.add_all([
                Message(
                    id=uuid.uuid4(),
                    conversation_id=conv.id,
                    role="user",
                    content="How many documents do I have uploaded?",
                ),
                Message(
                    id=uuid.uuid4(),
                    conversation_id=conv.id,
                    role="assistant",
                    content="You have 3 documents uploaded so far.",
                ),
            ])
            await db.commit()

        # Execute: run the background-worker logic directly
        await update_conversation_summary(conv_id)

        # Assert: fetch via a FRESH session (isolated lifecycle proof)
        async with async_session() as db:
            stored = await db.get(Conversation, conv_id)
            assert stored is not None
            summary = stored.context_summary
            assert summary is not None, "context_summary must be populated"
            assert summary.strip(), "context_summary must be non-empty"
            lowered = summary.lower()
            assert "here is a summary" not in lowered, "preamble 'here is a summary' leaked"
            assert "here's a summary" not in lowered, "preamble 'here's a summary' leaked"
            assert not lowered.startswith("summary:"), "preamble 'summary:' leaked"
            assert not lowered.startswith("sure"), "preamble 'sure' leaked"
            print(f"\nStored summary: {summary}")
    finally:
        # Teardown: purge test data in dependency-safe order (messages -> conversation -> user)
        async with async_session() as db:
            if conv_id is not None:
                await db.execute(delete(Message).where(Message.conversation_id == conv_id))
                await db.execute(delete(Conversation).where(Conversation.id == conv_id))
            if user_id is not None:
                await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
