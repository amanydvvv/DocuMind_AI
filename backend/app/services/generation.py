import logging
import os
from typing import List, Optional

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
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
    """
    Build a resilient LLM with a fallback cascade:
      1. Groq  llama-3.1-8b-instant   (fast, low-latency — primary)
      2. Groq  llama-3.3-70b-versatile (higher capacity pool)
      3. Groq  qwen3-32b              (different model family, separate queue)
      4. Gemini 1.5 Flash              (cross-provider safety net)

    If any model returns a 503, 429, or any other error, LangChain's
    with_fallbacks() automatically tries the next one in the chain.
    """
    groq_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

    if not groq_key and not gemini_key:
        raise RuntimeError(
            "Neither GROQ_API_KEY nor GEMINI_API_KEY is set. "
            "At least one LLM provider key is required for chat generation."
        )

    fallbacks = []

    # --- Primary: Groq llama-3.1-8b-instant ---
    primary = None
    if groq_key:
        primary = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3,
            max_retries=1,  # one retry with backoff before cascading
        )

        # --- Fallback 1: Groq llama-3.3-70b-versatile ---
        fallbacks.append(ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_retries=0,
        ))

        # --- Fallback 2: Groq qwen3-32b ---
        fallbacks.append(ChatGroq(
            api_key=groq_key,
            model_name="qwen3-32b",
            temperature=0.3,
            max_retries=0,
        ))

    # --- Fallback 3 (cross-provider): Gemini 1.5 Flash ---
    if gemini_key:
        gemini_fallback = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_key,
            temperature=0.3,
            max_output_tokens=1024,
        )
        if primary is None:
            # Groq key missing — Gemini is the only provider
            primary = gemini_fallback
        else:
            fallbacks.append(gemini_fallback)

    if primary is None:
        raise RuntimeError(
            "Could not initialise any LLM. Check your API key environment variables."
        )

    if fallbacks:
        logger.info(
            "LLM fallback cascade active: %s → %s",
            primary.model_name if hasattr(primary, 'model_name') else str(primary),
            " → ".join(
                fb.model_name if hasattr(fb, 'model_name') else str(fb)
                for fb in fallbacks
            ),
        )
        return primary.with_fallbacks(fallbacks)

    return primary


RAG_PROMPT_TEMPLATE = """
You are an expert AI assistant tasked with answering questions based ONLY on the provided context and conversation history.

{corpus_metadata}

{chat_history_section}

Context information is below.
---------------------
{context}
---------------------

IMPORTANT: The context above contains retrieved text CHUNKS, not separate documents.
Multiple chunks may come from the SAME document. When answering questions about
how many documents exist, what documents exist, or listing document names, use
ONLY the CORPUS METADATA block above — never count the retrieved chunks as documents.

Given the context information, chat history, and no prior knowledge, answer the user's query.
If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
Do not hallucinate.

User Query: {query}
Answer:
"""

prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["corpus_metadata", "chat_history_section", "context", "query"]
)

class RateLimitError(Exception):
    """Raised when the LLM provider hits rate limits or quota bounds."""
    pass


# Error markers that should trigger fallback (via RateLimitError or LangChain's with_fallbacks)
FALLBACK_TRIGGER_MARKERS = (
    "429",
    "Quota exceeded",
    "ResourceExhausted",
    "rate limit",
    "503",
    "queue is full",
)


def _is_fallback_error(err: Exception) -> bool:
    """Check if an error should trigger the fallback cascade."""
    err_str = str(err)
    return any(marker.lower() in err_str.lower() for marker in FALLBACK_TRIGGER_MARKERS)


async def generate_answer(
    query: str,
    chunks: List[Chunk],
    chat_history: Optional[List[Message]] = None,
    corpus_metadata: str = "",
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
            "corpus_metadata": corpus_metadata,
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        })
        return response.content
    except Exception as e:
        if _is_fallback_error(e):
            logger.warning(f"LLM error triggers fallback: {e}")
            raise RateLimitError(
                "The AI service is currently at capacity or quota limits have been reached. Please try again in a moment."
            )
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        raise


async def generate_answer_stream(
    query: str,
    chunks: List[Chunk],
    chat_history: Optional[List[Message]] = None,
    corpus_metadata: str = "",
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
            "corpus_metadata": corpus_metadata,
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        }):
            if chunk_response.content:
                yield chunk_response.content
    except Exception as e:
        if _is_fallback_error(e):
            logger.warning(f"LLM error triggers fallback during stream: {e}")
            raise RateLimitError(
                "The AI service is currently at capacity or quota limits have been reached. Please try again in a moment."
            )
        logger.error(f"Error during LLM token streaming: {e}", exc_info=True)
        raise