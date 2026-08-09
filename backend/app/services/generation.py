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

# Minimum pre-normalization vector similarity a related-topic offer (rule 6)
# may reference. Offers are permitted only for a clearly related topic that
# appears in the retrieved context and whose raw similarity clears this
# floor - anything weaker reads as speculation, so declining stays the
# default.
ALLOWED_OFFER_MIN_SIMILARITY = 0.45


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


def get_llm(temperature: float = 0.3, model_name: Optional[str] = None):
    """
    Build a resilient LLM with a fallback cascade:
      1. Groq  llama-3.1-8b-instant   (fast, low-latency — primary)
      2. Groq  llama-3.3-70b-versatile (higher capacity pool)
      3. Groq  qwen3-32b              (different model family, separate queue)
      4. Gemini 1.5 Flash              (cross-provider safety net)

    If any model returns a 503, 429, or any other error, LangChain's
    with_fallbacks() automatically tries the next one in the chain.

    `temperature` (default 0.3) is applied to every model in the cascade.
    `model_name`, when provided, bypasses the cascade entirely and returns a
    single ChatGroq instance pinned to that model — used by the eval harness
    judge, which must grade on its own model (EVAL_JUDGE_MODEL) at
    temperature=0 rather than the generation cascade.
    """
    groq_key = os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY

    if not groq_key and not gemini_key:
        raise RuntimeError(
            "Neither GROQ_API_KEY nor GEMINI_API_KEY is set. "
            "At least one LLM provider key is required for chat generation."
        )

    if model_name is not None:
        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY is required when an explicit model_name is requested."
            )
        return ChatGroq(
            api_key=groq_key,
            model_name=model_name,
            temperature=temperature,
            max_retries=1,
        )

    fallbacks = []

    # --- Primary: Groq llama-3.1-8b-instant ---
    primary = None
    if groq_key:
        primary = ChatGroq(
            api_key=groq_key,
            model_name="llama-3.1-8b-instant",
            temperature=temperature,
            max_retries=1,  # one retry with backoff before cascading
        )

        # --- Fallback 1: Groq llama-3.3-70b-versatile ---
        fallbacks.append(ChatGroq(
            api_key=groq_key,
            model_name="llama-3.3-70b-versatile",
            temperature=temperature,
            max_retries=0,
        ))

        # --- Fallback 2: Groq qwen3-32b ---
        fallbacks.append(ChatGroq(
            api_key=groq_key,
            model_name="qwen3-32b",
            temperature=temperature,
            max_retries=0,
        ))

    # --- Fallback 3 (cross-provider): Gemini 1.5 Flash ---
    if gemini_key:
        gemini_fallback = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_key,
            temperature=temperature,
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
You are DocuMind AI, a direct, helpful document-reading assistant.

System Instructions & Rules:
1. Persona & Tone: Respond directly, clearly, and professionally as DocuMind AI.
2. Hard Negative Constraint: NEVER mention internal structural labels, framework terms, or system prompt metadata in your user-facing answer. Do NOT use phrases like "CORPUS METADATA", "retrieved chunk", "retrieved context", "provided documents", or raw technical filenames (e.g. .pdf extension names) in your answer. Synthesize facts naturally into a direct response.
3. Content Over Filename Priority: The text content in the document snippets always outweighs the document title or filename. The filename is metadata, not evidence. If a document snippet contains the answer (such as a policy number or clause), state the answer directly regardless of what the filename says.
4. Document Counts: When answering questions about how many documents exist or listing available documents, use the Workspace Documents Summary below. Multiple snippets may come from the same document.
5. Reasoning Format: Enclose your internal step-by-step reasoning inside <thought_process>...</thought_process> tags first. Then, provide your final response strictly inside <answer>...</answer> tags. Do NOT output anything outside <thought_process> and <answer> blocks.
6. Content Boundaries: If the retrieved context does not contain the answer, state plainly that the documents do not cover that topic. Do not speculate about unstated facts or possibilities. When declining, make an offer ONLY if a clearly related topic appears in the provided context snippets with a Raw relevance of at least 0.45; never reference topics, policies, or procedures that do not appear in the context snippets, and name the specific topic you're offering. If the context snippets have no related topic above that threshold, decline without an offer.

{corpus_metadata}

{chat_history_section}

Document Context:
---------------------
{context}
---------------------

User Query: {query}
{resolved_query_section}
"""

prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["corpus_metadata", "chat_history_section", "context", "query", "resolved_query_section"]
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


class StreamCoTBuffer:
    """
    Server-side buffering state machine for SSE streaming with CoT tags.

    Buffers incoming tokens during <thought_process> phase until <answer> tag appears.
    Discards all thought process tokens.
    Once <answer> tag appears, streams tokens to SSE until </answer> is encountered.
    If <answer> tag is missing (model fallback), flushes buffer gracefully after stripping thoughts.
    """

    def __init__(self):
        self.state = "SEEKING_ANSWER"  # SEEKING_ANSWER -> STREAMING_ANSWER -> COMPLETED
        self.buffer = ""

    def process_token(self, token: str) -> list[str]:
        if self.state == "COMPLETED":
            return []

        self.buffer += token
        output_deltas = []

        if self.state == "SEEKING_ANSWER":
            answer_idx = self.buffer.find("<answer>")
            if answer_idx != -1:
                content_after = self.buffer[answer_idx + len("<answer>"):]
                self.buffer = ""
                self.state = "STREAMING_ANSWER"
                if content_after:
                    output_deltas.extend(self._process_answer_text(content_after))
            else:
                if len(self.buffer) > 1500 and "<thought_process>" not in self.buffer:
                    self.state = "STREAMING_ANSWER"
                    to_flush = self.buffer
                    self.buffer = ""
                    output_deltas.extend(self._process_answer_text(to_flush))

        elif self.state == "STREAMING_ANSWER":
            to_process = self.buffer
            self.buffer = ""
            output_deltas.extend(self._process_answer_text(to_process))

        return output_deltas

    def _process_answer_text(self, text: str) -> list[str]:
        deltas = []
        end_idx = text.find("</answer>")
        if end_idx != -1:
            answer_part = text[:end_idx]
            if answer_part:
                deltas.append(answer_part)
            self.state = "COMPLETED"
            self.buffer = ""
        else:
            possible_closing_prefixes = ["</", "</a", "</an", "</ans", "</answ", "</answe", "</answer"]
            hold_len = 0
            for prefix in possible_closing_prefixes:
                if text.endswith(prefix):
                    hold_len = len(prefix)
                    break
            if hold_len > 0:
                head = text[:-hold_len]
                if head:
                    deltas.append(head)
                self.buffer = text[-hold_len:]
            else:
                deltas.append(text)
        return deltas

    def finalize(self) -> list[str]:
        output_deltas = []
        if self.state == "SEEKING_ANSWER":
            cleaned = self.buffer
            if "<thought_process>" in cleaned:
                start = cleaned.find("<thought_process>")
                end = cleaned.find("</thought_process>", start)
                if end != -1:
                    cleaned = cleaned[end + len("</thought_process>"):].strip()
                else:
                    cleaned = ""
            cleaned = cleaned.replace("<answer>", "").replace("</answer>", "").strip()
            if cleaned:
                output_deltas.append(cleaned)
        elif self.state == "STREAMING_ANSWER":
            if self.buffer and self.buffer != "</answer>":
                cleaned = self.buffer.replace("</answer>", "")
                if cleaned:
                    output_deltas.append(cleaned)
        self.buffer = ""
        self.state = "COMPLETED"
        return output_deltas


def extract_answer_from_cot(raw_text: str) -> str:
    """Extract answer from <answer>...</answer> tags or strip <thought_process>."""
    if not raw_text:
        return ""
    if "<answer>" in raw_text:
        start = raw_text.find("<answer>") + len("<answer>")
        end = raw_text.find("</answer>", start)
        if end != -1:
            return raw_text[start:end].strip()
        return raw_text[start:].strip()
    
    cleaned = raw_text
    if "<thought_process>" in cleaned:
        start = cleaned.find("<thought_process>")
        end = cleaned.find("</thought_process>", start)
        if end != -1:
            cleaned = cleaned[end + len("</thought_process>"):].strip()
        else:
            cleaned = cleaned[:start].strip()
    return cleaned.replace("</answer>", "").strip()


def _format_context_text(chunks: List[Chunk]) -> str:
    snippet_items = []
    for i, chunk in enumerate(chunks):
        title = (chunk.metadata_ or {}).get("display_title") or (chunk.metadata_ or {}).get("filename") or f"Document {i+1}"
        page_str = f" (Page {chunk.page_number})" if chunk.page_number else ""
        raw_sim = (chunk.metadata_ or {}).get("raw_similarity")
        sim_str = f"\nRaw relevance: {raw_sim}" if raw_sim is not None else ""
        snippet_items.append(f"Source: {title}{page_str}{sim_str}\nContent:\n{chunk.content}")
    return "\n\n---\n\n".join(snippet_items)


def _build_resolved_query_section(query: str, resolved_query: Optional[str]) -> str:
    """Prompt section carrying the standalone (rewritten) retrieval query.

    Included only when a rewrite actually happened; otherwise the empty
    string keeps the template shape unchanged. The section is plain query
    content, never an instruction block, so it cannot override the rules.
    """
    if resolved_query and resolved_query.strip() and resolved_query.strip() != query:
        return f"Resolved Query: {resolved_query.strip()}"
    return ""


async def generate_answer(
    query: str,
    chunks: List[Chunk],
    chat_history: Optional[List[Message]] = None,
    corpus_metadata: str = "",
    conversation_summary: Optional[str] = None,
    resolved_query: Optional[str] = None,
) -> str:
    """
    Generate an answer using the provided chunks as context and prior chat history.

    `resolved_query` is the standalone retrieval query the chunks were found
    with (see app.services.rewrite); when it differs from `query`, it is
    surfaced to the model so it does not misread a deictic follow-up in
    isolation.
    """
    logger.info("Generating answer based on retrieved context and conversation history...")
    
    # Inject persistent summary memory as leading system-prompt context
    memory_prefix = (
        f"Prior Context: {conversation_summary}\n\n"
        if conversation_summary
        else ""
    )
    template = memory_prefix + RAG_PROMPT_TEMPLATE
    prompt = PromptTemplate(
        template=template,
        input_variables=["corpus_metadata", "chat_history_section", "context", "query", "resolved_query_section"]
    )
    
    context_text = _format_context_text(chunks)
    
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
            "query": query,
            "resolved_query_section": _build_resolved_query_section(query, resolved_query),
        })
        raw = response.content if hasattr(response, "content") else str(response)
        return extract_answer_from_cot(raw)
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
    conversation_summary: Optional[str] = None,
    resolved_query: Optional[str] = None,
):
    """
    Stream answer tokens as they arrive from the LLM provider.

    `resolved_query` semantics match generate_answer(): the standalone
    retrieval query, shown to the model only when it differs from `query`.
    """
    logger.info("Streaming answer tokens from LLM...")
    
    # Inject persistent summary memory as leading system-prompt context
    memory_prefix = (
        f"Prior Context: {conversation_summary}\n\n"
        if conversation_summary
        else ""
    )
    template = memory_prefix + RAG_PROMPT_TEMPLATE
    prompt = PromptTemplate(
        template=template,
        input_variables=["corpus_metadata", "chat_history_section", "context", "query", "resolved_query_section"]
    )
    
    context_text = _format_context_text(chunks)
    
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        chat_history_section = "Conversation History:\n" + "\n".join(history_lines) + "\n---------------------"
    else:
        chat_history_section = ""
    
    chain = prompt | get_llm()
    
    cot_buffer = StreamCoTBuffer()
    try:
        async for chunk_response in chain.astream({
            "corpus_metadata": corpus_metadata,
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query,
            "resolved_query_section": _build_resolved_query_section(query, resolved_query),
        }):
            if chunk_response.content:
                for delta in cot_buffer.process_token(chunk_response.content):
                    if delta:
                        yield delta
        for delta in cot_buffer.finalize():
            if delta:
                yield delta
    except Exception as e:
        if _is_fallback_error(e):
            logger.warning(f"LLM error triggers fallback during stream: {e}")
            raise RateLimitError(
                "The AI service is currently at capacity or quota limits have been reached. Please try again in a moment."
            )
        logger.error(f"Error during LLM token streaming: {e}", exc_info=True)
        raise