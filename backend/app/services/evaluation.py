"""
DocuMind AI - Retrieval Evaluation Harness (schema + retrieval runner + judge)

This module is the plumbing layer for the LLM-as-judge eval harness
(see docs/PLAN_EVAL_GUARDRAILS.md, Feature 1, Steps 2-5). It deliberately
lives in `app/services/` but imports nothing from the request path
(routers, main) - importing this module has no side effects on live traffic.

Step 2 (schema + loader):
  - GoldenEntry: Pydantic model matching backend/tests/eval/golden_set.json
  - load_golden_set(): strict validation; duplicate ids, pass-type entries
    with empty markers or facts, or a docs reference to a file absent from
    the golden data directory all raise EvaluationConfigError.

Step 3 (composed retrieval runner):
  run_retrieval_for_entry() composes the hybrid retrieval pipeline by
  calling the Stage-1 vector + lexical retrievers and Stage-2 RRF fusion
  + phrase-coverage re-rank directly. It deliberately bypasses the
  cache-wrapped retrieve_context() by composition rather than by disabling
  the cache, so eval runs can never leak cache state. Retrieval knobs
  (RRF_K, TOP_Ns, blend weights) can be overridden at runtime for
  knob-flip experiments; overrides are always restored afterwards, even
  on exception.

Step 4 (marker recall@k):
  marker_recall_at_k() is a pure, deterministic arbiter: at least one
  retrieved chunk (within top-k) contains at least one expected marker,
  case-insensitive substring match.

Step 5 (generation + judge pipeline):
  run_evaluation() runs the full loop per entry: composed retrieval, a
  real generation call through generation.generate_answer() (the 2nd-LLM
  call that single-call eval setups miss), then a judge call on
  EVAL_JUDGE_MODEL at temperature=0 with strict JSON parsing - one retry
  on malformed output, then fail-closed (all dimensions fail + judge_error).
  Negative controls are reported separately and a control scoring "pass"
  is flagged as a harness-validity problem, never counted as a normal
  pass. The core run function takes a list of entries so sampling layers
  (CLI --sample) can be added later without refactoring. LLM call counts
  (generation + judge + retries) are tracked and returned for budget
  visibility.
"""

import asyncio
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import get_settings
from app.services import generation, retrieval
from app.services.rewrite import rewrite_followup

logger = logging.getLogger(__name__)
settings = get_settings()


# --------------------------------------------------------------------------
# Step 2 - golden set schema + loader
# --------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "tests" / "eval"
DEFAULT_GOLDEN_FILE = GOLDEN_DIR / "golden_set.json"


class EvaluationConfigError(ValueError):
    """Raised when the golden set or runtime knobs are invalid."""


class GoldenEntry(BaseModel):
    """A single golden Q/A pair with expected retrieval markers."""

    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_chunk_markers: List[str] = Field(default_factory=list)
    answer_facts: List[str] = Field(default_factory=list)
    docs: List[str] = Field(default_factory=list)
    intent: str = ""
    notes: str = ""
    expect_verdict: str = "pass"
    prior_turns: List[str] = Field(default_factory=list)
    forbidden_topics: List[str] = Field(default_factory=list)

    @field_validator("expected_chunk_markers", "answer_facts", "docs", "prior_turns", "forbidden_topics")
    @classmethod
    def _strip_blank_entries(cls, values: List[str]) -> List[str]:
        """Drop empty/whitespace-only strings from the list fields."""
        return [v.strip() for v in values if v.strip()]


def _read_entries(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise EvaluationConfigError(f"golden file {path} must contain a JSON list")
    return raw


def load_golden_set(path: Optional[Path] = None) -> List[GoldenEntry]:
    """
    Load and validate the golden dataset.

    Raises EvaluationConfigError for duplicate ids, pass-type entries with
    empty expected markers or answer facts, or doc references to files that
    do not exist alongside the golden file (default: backend/tests/eval/).
    """
    golden_path = path if path is not None else DEFAULT_GOLDEN_FILE
    entries_dir = golden_path.parent

    raw_entries = _read_entries(golden_path)
    entries: List[GoldenEntry] = []
    seen_ids = set()

    for raw in raw_entries:
        try:
            entry = GoldenEntry(**raw)
        except Exception as exc:
            rid = raw.get("id", "<unknown>")
            raise EvaluationConfigError(
                f"golden entry {rid!r} is invalid: {exc}"
            ) from exc

        if entry.id in seen_ids:
            raise EvaluationConfigError(f"duplicate golden id {entry.id!r}")
        seen_ids.add(entry.id)

        if entry.expect_verdict == "pass":
            if not entry.expected_chunk_markers:
                raise EvaluationConfigError(
                    f"pass-type entry {entry.id!r} has no expected_chunk_markers"
                )
            if not entry.answer_facts:
                raise EvaluationConfigError(
                    f"pass-type entry {entry.id!r} has no answer_facts"
                )

        for doc_name in entry.docs:
            if not (entries_dir / doc_name).is_file():
                raise EvaluationConfigError(
                    f"entry {entry.id!r} references missing doc file {doc_name!r}"
                )

        entries.append(entry)

    return entries


# --------------------------------------------------------------------------
# Step 2b - runtime knob overrides
# --------------------------------------------------------------------------

# Module attributes on app.services.retrieval that the harness may patch.
# Chunk-size / overlap / cache knobs are deliberately NOT listed here:
# they are ingestion-time (config.py) and out of scope for v1.
ALLOWED_RETRIEVAL_KNOBS = (
    "VECTOR_TOP_N",
    "LEXICAL_TOP_N",
    "RRF_K",
    "RRF_FUSED_TOP_K",
    "FINAL_TOP_K",
    "WEIGHT_VECTOR_NORM",
    "WEIGHT_LEXICAL_NORM",
    "WEIGHT_PHRASE_NORM",
)


@contextmanager
def _knob_override(retrieval_module, overrides: Mapping[str, Any]):
    """Apply knob overrides for the duration of a run and always restore."""
    invalid = set(overrides) - set(ALLOWED_RETRIEVAL_KNOBS)
    if invalid:
        raise EvaluationConfigError(
            f"unknown retrieval knobs: {sorted(invalid)}; "
            f"allowed: {sorted(ALLOWED_RETRIEVAL_KNOBS)}"
        )

    saved = {name: getattr(retrieval_module, name) for name in overrides}
    for name, value in overrides.items():
        setattr(retrieval_module, name, value)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(retrieval_module, name, value)


# --------------------------------------------------------------------------
# Step 3 - composed retrieval runner
# --------------------------------------------------------------------------


@dataclass
class RetrievedChunk:
    """A chunk surviving the full hybrid pipeline, in final retrieval order.

    Carries the fields generation consumes (page_number, metadata_) so the
    eval path exercises the same context formatting as the live chat path.
    """

    chunk_id: str
    document_id: Optional[str]
    content: str
    score: float
    page_number: Optional[int] = None
    metadata_: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalRunResult:
    """Output of a single-golden-entry retrieval run."""

    entry_id: str
    question: str
    expected_chunk_markers: List[str]
    retrieved: List[RetrievedChunk]
    knobs_applied: Dict[str, Any]


async def run_retrieval_for_entry(
    entry: GoldenEntry,
    session,
    *,
    user_id=None,
    document_id=None,
    overrides: Optional[Mapping[str, Any]] = None,
    query_override: Optional[str] = None,
) -> RetrievalRunResult:
    """
    Run the hybrid retrieval pipeline for one golden entry.

    Composes the Stage-1 retrievers and Stage-2 RRF + re-rank internals
    directly instead of going through the cache-wrapped retrieve_context(),
    so cache state can never influence eval results. Knob overrides patch
    current module-level constants explicitly at call time.

    `query_override` is the standalone (rewritten) retrieval query for
    multi-turn entries: retrieval runs on the resolved follow-up while the
    golden `question` stays the generation/judge ground truth.
    """
    overrides = dict(overrides or {})
    query = query_override if query_override is not None else entry.question

    with _knob_override(retrieval_module=retrieval, overrides=overrides):
        vector_candidates = await retrieval._retrieve_vector_candidates(
            query=query,
            db=session,
            document_id=document_id,
            user_id=user_id,
            limit=retrieval.VECTOR_TOP_N,
        )
        lexical_candidates = await retrieval._retrieve_lexical_candidates(
            query=query,
            db=session,
            document_id=document_id,
            user_id=user_id,
            limit=retrieval.LEXICAL_TOP_N,
        )

        fused = retrieval._reciprocal_rank_fusion(
            vector_candidates=vector_candidates,
            lexical_candidates=lexical_candidates,
            k=retrieval.RRF_K,
            top_fused_limit=retrieval.RRF_FUSED_TOP_K,
        )
        reranked = retrieval._phrase_coverage_rerank(
            fused_candidates=fused,
            query=query,
            final_top_k=retrieval.FINAL_TOP_K,
        )

    retrieved = [
        RetrievedChunk(
            chunk_id=str(chunk.id),
            document_id=(
                str(chunk.document_id) if chunk.document_id is not None else None
            ),
            content=chunk.content,
            score=score,
            page_number=getattr(chunk, "page_number", None),
            metadata_=dict(getattr(chunk, "metadata_", None) or {}),
        )
for chunk, score in reranked
    ]

    return RetrievalRunResult(
        entry_id=entry.id,
        question=query,
        expected_chunk_markers=entry.expected_chunk_markers,
        retrieved=retrieved,
        knobs_applied=overrides,
    )


# --------------------------------------------------------------------------
# Step 4 - deterministic marker recall@k
# --------------------------------------------------------------------------


def marker_recall_at_k(
    expected_markers: List[str], retrieved: List[RetrievedChunk]
) -> bool:
    """
    True if at least one retrieved chunk (within top-k, i.e. the given
    ordered list) contains at least one expected marker as a case-insensitive
    substring. Pure and deterministic - the cheap, non-flaky arbiter that
    runs alongside the LLM judge. An entry with no markers is never a
    recall hit (returns False).

    Negative-control semantics: their markers are deliberately absent from
    the corpus, so marker recall is EXPECTED to be False there. It is still
    computed and reported for every entry, because a True on a negative
    control would mean a fabricated marker accidentally appears in
    retrieved text - something the harness must surface, not hide. Pass
    rates in the aggregated report exclude negative controls by design.
    """
    if not expected_markers:
        return False
    markers = [marker.lower() for marker in expected_markers]
    for chunk in retrieved:
        content = chunk.content.lower()
        if any(marker in content for marker in markers):
            return True
    return False

# --------------------------------------------------------------------------
# Step 5 - generation + judge pipeline
# --------------------------------------------------------------------------

JUDGE_DIMENSIONS = ("retrieval_pass", "groundedness_pass", "completeness_pass")

# Per-chunk character budget sent to the judge (token economy).
JUDGE_CHUNK_CHAR_LIMIT = 2500

# Attempts for a well-formed judge response before failing closed.
JUDGE_MAX_ATTEMPTS = 2

JUDGE_PROMPT_TEMPLATE = (
    "You are an evaluation judge for a retrieval-augmented generation (RAG) "
    "system. You are grading ONE question-answer instance. Base every decision "
    "strictly on the materials provided below; do not use outside knowledge.\n"
    "\n"
    "QUESTION:\n{question}\n"
    "\n"
    "REFERENCE FACTS that a correct answer must cover (ground truth):\n{facts}\n"
    "\n"
    "RETRIEVED CONTEXT (the chunks the answer was generated from):\n{chunks}\n"
    "\n"
    "GENERATED ANSWER:\n{answer}\n"
    "\n"
    "Return ONLY a valid JSON object with exactly these three boolean fields:\n"
    '{{"retrieval_pass": bool, "groundedness_pass": bool, '
    '"completeness_pass": bool}}\n'
    "\n"
    "Definitions:\n"
    "- retrieval_pass: whether the retrieved context chunks contain the "
    "information needed to answer the question.\n"
    "- groundedness_pass: whether the generated answer is fully supported by "
    "the retrieved context, with no hallucinated or unsupported claims.\n"
    "- completeness_pass: whether the generated answer covers all the "
    "reference facts, or explicitly says it cannot when the context lacks "
    "them.\n"
    "Do not output anything besides the JSON object."
)

JUDGE_RETRY_SUFFIX = (
    "\n\nYour previous response was not valid JSON. Output ONLY the JSON "
    "object, nothing else."
)


def _format_chunks_for_judge(chunks: List[RetrievedChunk]) -> str:
    """Render retrieved chunks (rank, score, truncated content) for the judge."""
    if not chunks:
        return "(no chunks retrieved)"
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        content = chunk.content.strip()
        if len(content) > JUDGE_CHUNK_CHAR_LIMIT:
            content = content[:JUDGE_CHUNK_CHAR_LIMIT] + " ...[truncated]"
        lines.append(f"[{i}] (score={chunk.score:.3f})\n{content}")
    return "\n\n".join(lines)


def _parse_judge_json(raw: str) -> Optional[Dict[str, bool]]:
    """
    Strict parser: the response must be a JSON object whose three judge
    dimensions are all present and all booleans. Anything else (prose, code
    fences, missing or non-bool fields, partial object) is malformed.
    """
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    parsed: Dict[str, bool] = {}
    for dim in JUDGE_DIMENSIONS:
        value = payload.get(dim)
        if not isinstance(value, bool):
            return None
        parsed[dim] = value
    return parsed


async def _invoke_judge(judge_llm, prompt_text: str) -> str:
    """Single judge LLM call; returns the raw response text."""
    response = await judge_llm.ainvoke([{"role": "user", "content": prompt_text}])
    return response.content if hasattr(response, "content") else str(response)


async def _judge_answer(
    judge_llm, entry: GoldenEntry, answer: str, chunks: List[RetrievedChunk]
) -> tuple[Dict[str, bool], bool, int]:
    """
    Judge one answer. Returns (dimensions, judge_error, attempts).

    Fail-closed contract: malformed or failing judge output is NEVER treated
    as a pass. On malformed output the call is retried once; if the retry is
    also malformed (or the judge call raises), all three dimensions are
    marked fail and judge_error is set.
    """
    prompt_text = JUDGE_PROMPT_TEMPLATE.format(
        question=entry.question,
        facts="\n".join(f"- {fact}" for fact in entry.answer_facts) or "(none)",
        chunks=_format_chunks_for_judge(chunks),
        answer=answer or "(no answer generated)",
    )

    attempts = 0
    for attempt in range(JUDGE_MAX_ATTEMPTS):
        attempts += 1
        text = prompt_text if attempt == 0 else prompt_text + JUDGE_RETRY_SUFFIX
        try:
            raw = await _invoke_judge(judge_llm, text)
        except Exception as exc:
            logger.warning("judge call failed for %s: %s", entry.id, exc)
            await asyncio.sleep(5)
            raw = ""
        parsed = _parse_judge_json(raw)
        if parsed is not None:
            return parsed, False, attempts

    logger.warning(
        "judge returned malformed output for %s after %d attempt(s); failing closed",
        entry.id,
        attempts,
    )
    return {dim: False for dim in JUDGE_DIMENSIONS}, True, attempts


@dataclass
class QuestionResult:
    """Per-question eval outcome, including verdicts on negative controls."""

    entry_id: str
    expect_verdict: str
    is_negative_control: bool
    marker_recall: bool
    retrieval_pass: bool
    groundedness_pass: bool
    completeness_pass: bool
    judge_error: bool
    generated_answer: str
    knobs_applied: Dict[str, Any]
    topic_leak: bool = False
    rewritten_query: Optional[str] = None


@dataclass
class EvalReport:
    """Aggregated eval output for one run over a list of entries."""

    questions: List[QuestionResult]
    llm_calls: int

    def summary(self) -> Dict[str, Any]:
        """Collapse the report into a printable/assertable summary dict.

Pass rates are computed over pass-type entries only; negative
        controls are reported separately (per-id dimension outcomes) and a
        control is flagged as a harness-validity violation only when its
        fabricated info is retrievable (marker_recall or retrieval_pass) or
        its forbidden topics leak into the generated answer (topic_leak) -
        see the violations computation below for the groundedness nuance.
        """
        dims = ("marker_recall",) + JUDGE_DIMENSIONS
        pass_type = [q for q in self.questions if not q.is_negative_control]
        neg_controls = [q for q in self.questions if q.is_negative_control]

        pass_rates: Dict[str, Optional[float]] = {}
        for dim in dims:
            if pass_type:
                hits = sum(1 for q in pass_type if getattr(q, dim))
                pass_rates[dim] = hits / len(pass_type)
            else:
                pass_rates[dim] = None

        # Deterministic counterpart to the judge dimensions: the answer never
        # mentions an entry's forbidden topics. Only meaningful for entries
        # that declare them; entries with none cannot leak by construction.
        if pass_type:
            pass_rates["topic_leak_pass"] = sum(
                1 for q in pass_type if not q.topic_leak
            ) / len(pass_type)
        else:
            pass_rates["topic_leak_pass"] = None

        negative_controls = {
            q.entry_id: {
                **{dim: getattr(q, dim) for dim in dims},
                "topic_leak": q.topic_leak,
            }
            for q in neg_controls
        }
        # A control is only ever "passed" by the harness when its FABRICATED
        # information is actually retrievable (marker_recall or retrieval_pass
        # True) or leaks into the answer (topic_leak True). groundedness/
        # completeness on a control are informational: an answer that
        # honestly refuses to confirm the fabricated facts is legitimately
        # grounded in the unrelated context the retriever found, so a True
        # there is not a validity problem and must not trip exit 2.
        violations = [
            q.entry_id
            for q in neg_controls
            if q.marker_recall or q.retrieval_pass or q.topic_leak
        ]

        return {
            "total_questions": len(self.questions),
            "llm_calls": self.llm_calls,
            "pass_rates": pass_rates,
            "negative_controls": negative_controls,
            "negative_control_violations": violations,
            "judge_errors": [q.entry_id for q in self.questions if q.judge_error],
        }


async def run_evaluation(
    entries: List[GoldenEntry],
    session,
    *,
    user_id=None,
    document_id=None,
    overrides: Optional[Mapping[str, Any]] = None,
    judge_temperature: float = 0.0,
) -> EvalReport:
    """
    Run the full generation + judge pipeline over the GIVEN entries.

    The entry list is a parameter (not "load all 32"): callers may pass a
    subset for sampling/ablation without refactoring this function.

Per entry:
      (a) composed retrieval (Step 3 runner) -> chunks; for entries with
          prior_turns, the follow-up is first rewritten against fake turns
          (the same fail-closed rewrite_followup() the live chat path uses)
          and retrieval runs on the standalone query, never the deictic text
      (b) generation.generate_answer() on those chunks - the real generation
          cascade at default temperature 0.3 - this is the 2nd LLM call that
          single-call eval designs miss; calling it is mandatory, retrieval
          alone is never judged
      (c) topic_leak check: deterministic - any forbidden_topics substring
          present in the generated answer is a leak (fail-closed: no
          substrings declared means no leak possible)
      (d) judge on EVAL_JUDGE_MODEL at temperature=0 with strict JSON
          parsing (one retry, then fail-closed)

    LLM calls are counted (generation + judge + retries + rewrites) and
    returned in the report for budget visibility; no limit is enforced here.
    """
    llm_calls = 0
    judge_llm = generation.get_llm(
        temperature=judge_temperature,
        model_name=settings.EVAL_JUDGE_MODEL,
    )

    questions: List[QuestionResult] = []
    for entry in entries:
        rewritten = None
        retrieval_query = entry.question
        if entry.prior_turns:
            # Lightweight stand-ins: history items only need role/content.
            prior_msgs = [
                SimpleNamespace(role="user", content=turn)
                for turn in entry.prior_turns
            ]
            rewritten = await rewrite_followup(entry.question, prior_msgs)
            llm_calls += 1
            if rewritten and rewritten != entry.question:
                retrieval_query = rewritten
            else:
                rewritten = None

        retrieval_result = await run_retrieval_for_entry(
            entry,
            session,
            user_id=user_id,
            document_id=document_id,
            overrides=overrides,
            query_override=retrieval_query,
        )

        recall = marker_recall_at_k(
            entry.expected_chunk_markers, retrieval_result.retrieved
        )

        answer = await generation.generate_answer(
            entry.question, retrieval_result.retrieved, resolved_query=rewritten
        )
        llm_calls += 1

        answer_lower = answer.lower()
        topic_leak = any(
            topic.lower() in answer_lower for topic in entry.forbidden_topics
        )

        dimensions, judge_error, attempts = await _judge_answer(
            judge_llm, entry, answer, retrieval_result.retrieved
        )
        llm_calls += attempts

        questions.append(
            QuestionResult(
                entry_id=entry.id,
                expect_verdict=entry.expect_verdict,
                is_negative_control=entry.expect_verdict == "fail",
                marker_recall=recall,
                retrieval_pass=dimensions["retrieval_pass"],
                groundedness_pass=dimensions["groundedness_pass"],
                completeness_pass=dimensions["completeness_pass"],
                judge_error=judge_error,
                generated_answer=answer,
                knobs_applied=dict(overrides or {}),
                topic_leak=topic_leak,
                rewritten_query=rewritten,
            )
        )

    return EvalReport(questions=questions, llm_calls=llm_calls)

