"""
DocuMind AI — Summary Buffer Memory
Rolling conversational context summarization to keep LLM context windows clean.
"""

import logging
import re
from uuid import UUID

from sqlalchemy import select

from app.database import async_session
from app.models import Message, Conversation
from app.services.generation import get_llm

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = (
    "You are a concise conversation summarizer. Condense the conversation into a 2-3 sentence summary. "
    "Focus strictly on user intent, key entities, and main facts.\n\n"
    "CRITICAL INSTRUCTION: Output ONLY the raw summary text. Do NOT include any introductory or meta-text "
    "such as 'Here is a summary:', 'Sure!', 'Summary:', or quotes around the response.\n"
)

# Strip common LLM preamble patterns and stray quoting/whitespace
_PREAMBLE_RE = re.compile(
    r"^(here\s*is|here\'s|sure|summary:?|in summary:?)\b.*?:?\s*",
    flags=re.IGNORECASE,
)


async def update_conversation_summary(conversation_id: UUID) -> None:
    """
    Summarize the most recent messages in a conversation and persist the result.

    Runs in a FastAPI background task, so it manages its OWN session lifecycle
    rather than receiving a request-scoped session (which FastAPI closes before
    background tasks fire).

    Fetches the latest 5 messages for `conversation_id`, asks Groq to condense
    them, and saves the summary to `conversation.context_summary`.
    """
    async with async_session() as db:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        messages = list(result.scalars().all())

        if len(messages) < 2:
            logger.debug("Skipping summary for conversation %s: fewer than 2 messages", conversation_id)
            return

        messages.reverse()

        dialogue = "\n".join(
            f"{'User' if msg.role == 'user' else 'AI'}: {msg.content}"
            for msg in messages
        )

        llm = get_llm()
        response = await llm.ainvoke(SUMMARY_PROMPT + "\n\n" + dialogue)
        summary_text = response.content.strip()

        # Clean out common LLM preamble patterns
        summary_text = _PREAMBLE_RE.sub("", summary_text).strip(' \t\n\r"\'')

        if not summary_text:
            logger.warning("LLM returned an empty summary for conversation %s", conversation_id)
            return

        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            logger.warning("Conversation %s not found; summary not persisted", conversation_id)
            return

        conversation.context_summary = summary_text
        await db.commit()