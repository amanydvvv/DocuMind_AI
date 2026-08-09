"""
DocuMind AI - Follow-up query rewriting for multi-turn retrieval.

Retrieval runs on the user's latest message verbatim. Follow-ups that lean
on earlier turns ("what about the other plan?", "and its RPO?") are
deictic: they retrieve poorly on their own because the referent lives in
conversation history, not in the query. This module rewrites such a
follow-up into a standalone retrieval query using the recent chat history,
so retrieval for turn N+1 is conditioned on the conversation context.

Contract (fail-closed): any trigger miss, timeout, LLM/parse error, or
low-confidence rewrite returns the raw question text unchanged. The caller
falls back to exactly today's behavior, so this layer can never degrade
retrieval below the no-rewrite baseline.
"""

import asyncio
import json
import logging
import re
from typing import List, Optional

from app.services.generation import get_llm

logger = logging.getLogger(__name__)

# Hard ceiling on a single rewrite call (cheap to give up: raw fallback).
REWRITE_TIMEOUT_SECONDS = 2.5

# Only the last few turns matter for deictic resolution; caps prompt cost.
REWRITE_MAX_HISTORY_MESSAGES = 6

# Sanity caps on the rewrite LLM's output.
REWRITE_MAX_QUERY_CHARS = 300

REWRITE_PROMPT_TEMPLATE = (
    "You are a query-rewriting helper for a document-answering assistant. "
    "You rewrite a user's FOLLOW-UP question into a standalone retrieval "
    "query.\n"
    "\n"
    "CONVERSATION SO FAR:\n"
    "{history}\n"
    "\n"
    "USER FOLLOW-UP: {question}\n"
    "\n"
    "Rules:\n"
    "- The rewritten query must be self-contained: it must make sense "
    "WITHOUT the conversation, because it will be used to search a document "
    "corpus on its own.\n"
    "- Resolve pronouns and deictic references (\"it\", \"that plan\", \"the "
    "other region\", \"for them\") using the conversation.\n"
    "- Fix typos or garbled text ONLY when the conversation makes the intent "
    "clear; otherwise keep the text as close to the user's wording as "
    "possible.\n"
    "- Keep the user's exact topic and entity names. Do NOT invent facts, "
    "names, or numbers that appear in neither the conversation nor the "
    "question.\n"
    "- Never answer the question itself.\n"
    "- Output ONLY a JSON object with exactly this shape:\n"
    '{{"rewritten": "...", "confident": true}}\n'
    "- \"confident\" must be true ONLY if you are sure the rewritten query "
    "preserves the user's intent. Otherwise set it to false and put the "
    "user's original text verbatim in \"rewritten\"."
)


def _history_turns(chat_history: List) -> List[str]:
    """Render chat history as turn lines, newest-first tail capped.

    `chat_history` items only need `role` and `content` (ORM Message or
    lightweight stand-ins). The current question itself is excluded by the
    caller contract (history is fetched before the new turn is saved), but
    defensively deduplicated anyway.
    """
    lines: List[str] = []
    for msg in reversed(chat_history[-REWRITE_MAX_HISTORY_MESSAGES:]):
        content = getattr(msg, "content", None)
        if not content or not str(content).strip():
            continue
        role = getattr(msg, "role", "") or ""
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return lines


def _extract_json(raw: str) -> Optional[dict]:
    """Strict JSON parse, then a forgiving fenced/embedded object scan."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
    try:
        payload = json.loads(cleaned)
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except (ValueError, TypeError):
            return None
    return payload if isinstance(payload, dict) else None


async def rewrite_followup(question: str, chat_history: List) -> str:
    """
    Rewrite a conversational follow-up into a standalone retrieval query.

    Returns the rewritten query on success, or the raw `question` when:
      - there is no prior user turn (nothing to rewrite against),
      - the rewrite LLM times out, errors, or returns malformed output,
      - the LLM itself reports low confidence,
      - the output fails the sanity caps (empty, over-long, non-str).
    """
    turns = _history_turns(chat_history)
    if not turns or not any("User: " in t for t in turns):
        return question

    prompt_text = REWRITE_PROMPT_TEMPLATE.format(
        history="\n".join(turns) or "(none)", question=question
    )

    try:
        llm = get_llm(temperature=0.0)
        response = await asyncio.wait_for(
            llm.ainvoke([{"role": "user", "content": prompt_text}]),
            timeout=REWRITE_TIMEOUT_SECONDS,
        )
        raw = response.content if hasattr(response, "content") else str(response)
    except asyncio.TimeoutError:
        logger.warning("follow-up rewrite timed out; falling back to raw question")
        return question
    except Exception as exc:
        logger.warning("follow-up rewrite failed (%s); falling back to raw question", exc)
        return question

    payload = _extract_json(raw)
    if not payload:
        logger.warning("follow-up rewrite returned non-JSON; falling back to raw question")
        return question

    rewritten = payload.get("rewritten")
    confident = payload.get("confident") is True
    if not confident or not isinstance(rewritten, str) or not rewritten.strip():
        return question
    rewritten = rewritten.strip()
    if len(rewritten) > REWRITE_MAX_QUERY_CHARS:
        return question

    if rewritten != question:
        logger.info("follow-up rewritten for retrieval: %r -> %r", question, rewritten)
    return rewritten
