"""
DocuMind AI — Evaluation Harness Plumbing Tests (Steps 2-3)

Pure plumbing tests: zero LLM calls, zero live DB. The retrieval pipeline
is mocked at the Stage-1 boundary exactly like test_query_cache.py does,
so these tests only prove the runner composes the retrieval internals
directly (never the cache-wrapped entry point) and that knob overrides
take effect and are always restored afterwards.
"""

import json
import uuid

import pytest

import app.services.retrieval as retrieval
from app.services.evaluation import (
    ALLOWED_RETRIEVAL_KNOBS,
    DEFAULT_GOLDEN_FILE,
    EvaluationConfigError,
    GoldenEntry,
    RetrievalRunResult,
    load_golden_set,
    run_retrieval_for_entry,
)


class FakeChunk:
    """Stand-in for a SQLAlchemy Chunk: only the columns the pipeline reads."""

    def __init__(self, content: str, doc_id=None):
        self.id = uuid.uuid4()
        self.document_id = doc_id if doc_id is not None else uuid.uuid4()
        self.content = content
        self.metadata_ = {}


def _write_golden(tmp_path, entries, docs=("eval_corpus.md",)):
    """Write a golden file (plus the doc files it references) to a temp dir."""
    for doc in docs:
        (tmp_path / doc).write_text("# temp corpus", encoding="utf-8")
    path = tmp_path / "golden_test.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def _entry(**overrides):
    base = {
        "id": "T-001",
        "question": "What is the meal cap?",
        "expected_chunk_markers": ["cap of $75"],
        "answer_facts": ["the cap is $75"],
        "docs": ["eval_corpus.md"],
        "intent": "lexical-exact",
        "notes": "test fixture",
        "expect_verdict": "pass",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Step 2 - schema + loader
# ---------------------------------------------------------------------------


def test_valid_golden_set_loads_cleanly():
    entries = load_golden_set()
    assert len(entries) == 30
    assert sum(1 for e in entries if e.expect_verdict == "fail") == 3


def test_valid_entry_loads_from_other_path(tmp_path):
    path = _write_golden(tmp_path, [_entry()])
    entries = load_golden_set(path)
    assert len(entries) == 1
    assert entries[0].id == "T-001"
    assert entries[0].expected_chunk_markers == ["cap of $75"]


def test_duplicate_id_raises(tmp_path):
    path = _write_golden(tmp_path, [_entry(), _entry()])
    with pytest.raises(EvaluationConfigError, match="duplicate golden id"):
        load_golden_set(path)


def test_pass_entry_without_markers_raises(tmp_path):
    path = _write_golden(tmp_path, [_entry(expected_chunk_markers=[])])
    with pytest.raises(EvaluationConfigError, match="no expected_chunk_markers"):
        load_golden_set(path)


def test_pass_entry_without_facts_raises(tmp_path):
    path = _write_golden(tmp_path, [_entry(answer_facts=[])])
    with pytest.raises(EvaluationConfigError, match="no answer_facts"):
        load_golden_set(path)


def test_bad_doc_reference_raises(tmp_path):
    path = _write_golden(tmp_path, [_entry(docs=["does-not-exist.md"])])
    with pytest.raises(EvaluationConfigError, match="missing doc file"):
        load_golden_set(path)


def test_fail_control_may_have_empty_markers(tmp_path):
    path = _write_golden(
        tmp_path,
        [_entry(expect_verdict="fail", expected_chunk_markers=[], answer_facts=[])],
    )
    entries = load_golden_set(path)
    assert entries[0].expect_verdict == "fail"


def test_default_golden_file_location():
    assert DEFAULT_GOLDEN_FILE.parent.name == "eval"
    assert DEFAULT_GOLDEN_FILE.is_file()
    assert DEFAULT_GOLDEN_FILE.suffix == ".json"


# ---------------------------------------------------------------------------
# Step 3 - runner composition
# ---------------------------------------------------------------------------


class StageSpy:
    """Records Stage-1 invocation; returns deterministic candidates."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.vector_calls = 0
        self.lexical_calls = 0

    async def vector(self, **kwargs):
        self.vector_calls += 1
        return [(c, 0.9) for c in self.chunks]

    async def lexical(self, **kwargs):
        self.lexical_calls += 1
        return [(c, 0.8) for c in self.chunks]


class BoomDB:
    """Any use of the DB session fails the test."""

    def __getattr__(self, _):
        raise AssertionError("runner must not touch the DB session in plumbing tests")


class BoomCache:
    """Any cache access fails the test."""

    storage = {"get": lambda *a, **k: _boom(), "put": lambda *a, **k: _boom()}

    def get(self, *a, **k):
        raise AssertionError("runner must not touch query_cache")

    def put(self, *a, **k):
        raise AssertionError("runner must not touch query_cache")


def _boom():
    raise AssertionError("runner must not touch query_cache")


@pytest.mark.asyncio
async def test_runner_composes_stage1_internals_not_cached_entry(monkeypatch):
    chunks = [FakeChunk("alpha"), FakeChunk("beta")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    def boom_retrieve(*args, **kwargs):
        raise AssertionError("runner must not call cache-wrapped retrieve_context")

    monkeypatch.setattr(retrieval, "retrieve_context", boom_retrieve)
    monkeypatch.setattr(retrieval, "query_cache", BoomCache())

    entry = GoldenEntry(**_entry())
    result = await run_retrieval_for_entry(
        entry, session=BoomDB(), user_id=uuid.uuid4()
    )

    assert isinstance(result, RetrievalRunResult)
    assert spy.vector_calls == 1 and spy.lexical_calls == 1
    assert result.entry_id == entry.id
    assert result.question == entry.question
    assert result.expected_chunk_markers == entry.expected_chunk_markers
    assert [r.content for r in result.retrieved] == ["alpha", "beta"]
    assert all(isinstance(r.chunk_id, str) for r in result.retrieved)
    assert all(r.score >= 0.0 for r in result.retrieved)


# ---------------------------------------------------------------------------
# Step 3 - knob overrides
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_final_top_k_override_changes_shape_and_restores(monkeypatch):
    chunks = [FakeChunk("alpha"), FakeChunk("beta"), FakeChunk("gamma")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    original = retrieval.FINAL_TOP_K

    with_r1 = await run_retrieval_for_entry(
        entry=GoldenEntry(**_entry()),
        session=BoomDB(),
        overrides={"FINAL_TOP_K": 1},
    )
    assert len(with_r1.retrieved) == 1
    assert with_r1.knobs_applied == {"FINAL_TOP_K": 1}
    assert retrieval.FINAL_TOP_K == original
    assert retrieval.FINAL_TOP_K != 1

    without = await run_retrieval_for_entry(
        entry=GoldenEntry(**_entry()),
        session=BoomDB(),
    )
    assert len(without.retrieved) == 3


@pytest.mark.asyncio
async def test_rrf_k_override_reaches_fusion_and_restores(monkeypatch):
    chunks = [FakeChunk("alpha")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    real_fusion = retrieval._reciprocal_rank_fusion
    captured = {}

    def capture_fusion(**kwargs):
        captured["k"] = kwargs.get("k")
        captured["top_fused"] = kwargs.get("top_fused_limit")
        captured["vec_count"] = len(kwargs["vector_candidates"])
        captured["lex_count"] = len(kwargs["lexical_candidates"])
        return real_fusion(
            vector_candidates=kwargs["vector_candidates"],
            lexical_candidates=kwargs["lexical_candidates"],
            k=kwargs.get("k"),
            top_fused_limit=kwargs.get("top_fused_limit"),
        )

    monkeypatch.setattr(retrieval, "_reciprocal_rank_fusion", capture_fusion)

    original = retrieval.RRF_K

    await run_retrieval_for_entry(
        entry=GoldenEntry(**_entry()),
        session=BoomDB(),
        overrides={"RRF_K": 123},
    )

    assert captured["k"] == 123
    assert captured["lex_count"] == captured["vec_count"] == 1
    assert retrieval.RRF_K == original
    assert retrieval.RRF_K != 123


@pytest.mark.asyncio
async def test_weight_overrides_are_accepted(monkeypatch):
    chunks = [FakeChunk("alpha")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    original_vector_w = retrieval.WEIGHT_VECTOR_NORM

    await run_retrieval_for_entry(
        entry=GoldenEntry(**_entry()),
        session=BoomDB(),
        overrides={
            "WEIGHT_VECTOR_NORM": 1.0,
            "WEIGHT_LEXICAL_NORM": 0.0,
            "WEIGHT_PHRASE_NORM": 0.0,
        },
    )

    assert retrieval.WEIGHT_VECTOR_NORM == original_vector_w


@pytest.mark.asyncio
async def test_all_allowed_knobs_patch_without_error(monkeypatch):
    chunks = [FakeChunk("alpha")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    overrides = {knob: getattr(retrieval, knob) for knob in ALLOWED_RETRIEVAL_KNOBS}
    result = await run_retrieval_for_entry(
        entry=GoldenEntry(**_entry()),
        session=BoomDB(),
        overrides=overrides,
    )
    assert result.knobs_applied == overrides


@pytest.mark.asyncio
async def test_unknown_knob_raises(monkeypatch):
    chunks = [FakeChunk("alpha")]
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    entry = GoldenEntry(**_entry())

    with pytest.raises(EvaluationConfigError, match="unknown retrieval knobs"):
        await run_retrieval_for_entry(entry, session=BoomDB(), overrides={"CHUNK_SIZE": 800})

    with pytest.raises(EvaluationConfigError, match="unknown retrieval knobs"):
        await run_retrieval_for_entry(entry, session=BoomDB(), overrides={"CACHE_TTL_SECONDS": 1})


@pytest.mark.asyncio
async def test_knobs_restored_even_when_pipeline_raises(monkeypatch):
    async def failing_vector(**kwargs):
        raise RuntimeError("simulated stage-1 failure")

    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", failing_vector)

    original = retrieval.RRF_K
    with pytest.raises(RuntimeError, match="simulated"):
        await run_retrieval_for_entry(
            entry=GoldenEntry(**_entry()),
            session=BoomDB(),
            overrides={"RRF_K": 999},
        )
    assert retrieval.RRF_K == original