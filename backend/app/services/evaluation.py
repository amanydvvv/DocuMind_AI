"""
DocuMind AI - Retrieval Evaluation Harness (schema + retrieval runner)

This module is the plumbing layer for the LLM-as-judge eval harness
(see docs/PLAN_EVAL_GUARDRAILS.md, Feature 1, Steps 2-3). It deliberately
lives in `app/services/` but imports nothing from the request path
(routers, generation, main) - importing this module has no side effects on
live traffic.

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
"""

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, field_validator

from app.services import retrieval


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

    @field_validator("expected_chunk_markers", "answer_facts", "docs")
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
    """A chunk surviving the full hybrid pipeline, in final retrieval order."""

    chunk_id: str
    document_id: Optional[str]
    content: str
    score: float


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
) -> RetrievalRunResult:
    """
    Run the hybrid retrieval pipeline for one golden entry.

    Composes the Stage-1 retrievers and Stage-2 RRF + re-rank internals
    directly instead of going through the cache-wrapped retrieve_context(),
    so cache state can never influence eval results. Knob overrides patch
    current module-level constants explicitly at call time.
    """
    overrides = dict(overrides or {})

    with _knob_override(retrieval_module=retrieval, overrides=overrides):
        vector_candidates = await retrieval._retrieve_vector_candidates(
            query=entry.question,
            db=session,
            document_id=document_id,
            user_id=user_id,
            limit=retrieval.VECTOR_TOP_N,
        )
        lexical_candidates = await retrieval._retrieve_lexical_candidates(
            query=entry.question,
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
            query=entry.question,
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
        )
        for chunk, score in reranked
    ]

    return RetrievalRunResult(
        entry_id=entry.id,
        question=entry.question,
        expected_chunk_markers=entry.expected_chunk_markers,
        retrieved=retrieved,
        knobs_applied=overrides,
    )