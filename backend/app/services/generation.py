
import logging
import os
from typing import List, Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from app.models import Chunk, Message
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_HISTORY_TOKENS = 3000


def build_token_budgeted_history(messages: List[Message]) -> List[Message]:
    """
    Sliding context window for conversation history based on a token budget.

    Expects `messages` sorted newest-first, and returns the newest messages
    that fit within MAX_HISTORY_TOKENS, re-ordered chronologically (oldest
    first) for the prompt template. Older messages are discarded the moment
    the budget is exceeded.
    """
    selected = []
    accumulated_tokens = 0
    for msg in messages:
        accumulated_tokens += max(1, len(msg.content) // 4)
        if accumulated_tokens > MAX_HISTORY_TOKENS:
            break
        selected.append(msg)
    selected.reverse()
    return selected


def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0.3,
    )

RAG_PROMPT_TEMPLATE = """
You are an expert AI assistant tasked with answering questions based ONLY on the provided context and conversation history.

{chat_history_section}

Context information is below.
---------------------
{context}
---------------------

Given the context information, chat history, and no prior knowledge, answer the user's query.
If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
Do not hallucinate.

User Query: {query}
Answer:
"""

prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["chat_history_section", "context", "query"]
)

class RateLimitError(Exception):
    """Raised when the LLM provider hits rate limits or quota bounds."""
    pass


async def generate_answer(
    query: str, chunks: List[Chunk], chat_history: Optional[List[Message]] = None
) -> str:
    """
    Generate an answer using the provided chunks as context and prior chat history.
    """
    logger.info("Generating answer based on retrieved context and conversation history...")
    
    # Format context by joining chunk contents
    context_text = "\n\n---\n\n".join(
        [f"Document snippet {i+1}:\n{chunk.content}" for i, chunk in enumerate(chunks)]
    )
    
    # Format chat history if present
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        chat_history_section = "Conversation History:\n" + "\n".join(history_lines) + "\n---------------------"
    else:
        chat_history_section = ""
    
    # Build the prompt chain with dynamic LLM instance
    chain = prompt | get_llm()
    
    # Execute the LLM
    try:
        response = await chain.ainvoke({
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        })
        return response.content
    except Exception as e:
        err_str = str(e)
        if (
            "429" in err_str
            or "Quota exceeded" in err_str
            or "ResourceExhausted" in err_str
            or "rate limit" in err_str.lower()
        ):
            logger.warning(f"LLM Rate Limit Exceeded: {e}")
            raise RateLimitError(
                "The AI service is currently at capacity or quota limits have been reached. Please try again in a moment."
            )
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        raise


async def generate_answer_stream(
    query: str, chunks: List[Chunk], chat_history: Optional[List[Message]] = None
):
    """
    Stream answer tokens as they arrive from the LLM provider.
    """
    logger.info("Streaming answer tokens from LLM...")
    
    context_text = "\n\n---\n\n".join(
        [f"Document snippet {i+1}:\n{chunk.content}" for i, chunk in enumerate(chunks)]
    )
    
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        chat_history_section = "Conversation History:\n" + "\n".join(history_lines) + "\n---------------------"
    else:
        chat_history_section = ""
    
    chain = prompt | get_llm()
    
    try:
        async for chunk_response in chain.astream({
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        }):
            if chunk_response.content:
                yield chunk_response.content
    except Exception as e:
        err_str = str(e)
        if (
            "429" in err_str
            or "Quota exceeded" in err_str
            or "ResourceExhausted" in err_str
            or "rate limit" in err_str.lower()
        ):
            logger.warning(f"LLM Rate Limit Exceeded during stream: {e}")
            raise RateLimitError(
                "The AI service is currently at capacity or quota limits have been reached. Please try again in a moment."
            )
        logger.error(f"Error during LLM token streaming: {e}", exc_info=True)
        raise

