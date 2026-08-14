"""
KueryCore AI Ã¢â‚¬â€ Evaluation Harness Plumbing Tests (Steps 2-5)

Pure plumbing tests: zero LLM calls, zero live DB. The retrieval pipeline
is mocked at the Stage-1 boundary exactly like test_query_cache.py does,
so these tests only prove the runner composes the retrieval internals
directly (never the cache-wrapped entry point), knob overrides take effect
and are always restored afterwards, marker recall is deterministic, and
the generation+judge pipeline is fail-closed with negative controls
reported separately. The judge LLM is stubbed - no real LLM calls.
"""

import json
from types import SimpleNamespace
import uuid

import pytest

import app.services.generation as generation
import app.services.retrieval as retrieval
from app.config import get_settings
from app.services.evaluation import (
    ALLOWED_RETRIEVAL_KNOBS,
    DEFAULT_GOLDEN_FILE,
    EvaluationConfigError,
    GoldenEntry,
    QuestionResult,
    RetrievalRunResult,
    load_golden_set,
    marker_recall_at_k,
    run_evaluation,
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
    assert len(entries) == 37
    assert sum(1 for e in entries if e.expect_verdict == "fail") == 4


def test_multiturn_entries_carry_fields():
    entries = {e.id: e for e in load_golden_set()}
    assert entries["EVAL-032"].prior_turns == [
        "Which AWS region hosts the primary control plane?"
    ]
    assert entries["EVAL-033"].prior_turns
    assert entries["EVAL-033"].forbidden_topics == []
    assert entries["EVAL-034"].prior_turns == []
    assert "Finance & Planning" in entries["EVAL-034"].forbidden_topics


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
    assert retrieval.RRF_K == original# ---------------------------------------------------------------------------
# Step 4 - marker recall@k (deterministic)
# ---------------------------------------------------------------------------


def _recall_entry(markers, contents):
    """Marker-recall fixture: chunks built from plain content strings."""
    chunks = [
        SimpleNamespace(content=c, score=0.9, chunk_id="x", document_id="d")
        for c in contents
    ]
    return chunks


def test_marker_recall_true_on_exact():
    chunks = _recall_entry(None, ["The cap of $75 applies."])
    assert marker_recall_at_k(["cap of $75"], chunks) is True


def test_marker_recall_case_insensitive():
    chunks = _recall_entry(None, ["THE CAP OF $75 IS FINAL."])
    assert marker_recall_at_k(["cap of $75"], chunks) is True


def test_marker_recall_miss_returns_false():
    chunks = _recall_entry(None, ["Unrelated content here."])
    assert marker_recall_at_k(["cap of $75"], chunks) is False


def test_marker_recall_any_marker_matches():
    chunks = _recall_entry(None, ["The chips are nice.", "second marker inside"])
    assert marker_recall_at_k(["one marker", "second marker"], chunks) is True


def test_marker_recall_uses_retrieval_order():
    chunks = _recall_entry(None, ["warm-up text", "needle buried in later chunk"])
    assert marker_recall_at_k(["needle"], chunks) is True


def test_marker_recall_empty_marker_list_never_hits():
    chunks = _recall_entry(None, ["anything"])
    assert marker_recall_at_k([], chunks) is False


# ---------------------------------------------------------------------------
# Step 4b - multi-turn follow-up rewriting (query_override reaches retrieval)
# ---------------------------------------------------------------------------


class QueryCaptureSpy(StageSpy):
    """Stage-1 spy that also records the query each retriever received."""

    def __init__(self, chunks):
        super().__init__(chunks)
        self.queries = []

    async def vector(self, **kwargs):
        self.queries.append(("vector", kwargs.get("query")))
        return await super().vector(**kwargs)

    async def lexical(self, **kwargs):
        self.queries.append(("lexical", kwargs.get("query")))
        return await super().lexical(**kwargs)


@pytest.mark.asyncio
async def test_run_evaluation_rewrites_followup_and_retrieves_resolved(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    spy = QueryCaptureSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    captured = {}

    async def fake_rewrite(question, chat_history):
        captured["question"] = question
        captured["history"] = list(chat_history)
        return "Where does the disaster-recovery replica for us-east-1 run?"

    import app.services.evaluation as evaluation
    monkeypatch.setattr(evaluation, "rewrite_followup", fake_rewrite)

    generated = []

    async def fake_generate(query, chunks, **kwargs):
        generated.append((query, kwargs.get("resolved_query")))
        return "The disaster-recovery replica runs in eu-west-1."

    monkeypatch.setattr(generation, "generate_answer", fake_generate)

    judge = FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ])
    _stub_judge(monkeypatch, judge)

    entry = GoldenEntry(**_entry(
        id="MT-001",
        prior_turns=["Which AWS region hosts the primary control plane?"],
    ))
    report = await run_evaluation([entry], session=BoomDB(), user_id=uuid.uuid4())

    q = report.questions[0]
    assert captured["question"] == entry.question
    assert [m.role for m in captured["history"]] == ["user"]
    # Both Stage-1 retrievers ran on the resolved follow-up, never the raw text.
    assert all(query == "Where does the disaster-recovery replica for us-east-1 run?"
               for _, query in spy.queries)
    assert generated == [
        (entry.question, "Where does the disaster-recovery replica for us-east-1 run?")
    ]
    assert q.rewritten_query == "Where does the disaster-recovery replica for us-east-1 run?"
    assert report.llm_calls == 3  # 1 rewrite + 1 generation + 1 judge attempt


@pytest.mark.asyncio
async def test_run_evaluation_no_rewrite_without_prior_turns(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    spy = QueryCaptureSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    async def boom_rewrite(question, chat_history):
        raise AssertionError("no prior turns -> rewrite must not be called")

    import app.services.evaluation as evaluation
    monkeypatch.setattr(evaluation, "rewrite_followup", boom_rewrite)
    _stub_stages(monkeypatch, chunks)
    _stub_judge(monkeypatch, FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ]))

    entry = GoldenEntry(**_entry())
    report = await run_evaluation([entry], session=BoomDB(), user_id=uuid.uuid4())

    q = report.questions[0]
    assert q.rewritten_query is None
    assert all(query == entry.question for _, query in spy.queries)
    assert report.llm_calls == 2  # no rewrite: generation + judge only


# ---------------------------------------------------------------------------
# Step 4c - deterministic topic-leak check (forbidden topics in answers)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_topic_leak_detected_and_flagged_on_control(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    _stub_judge(monkeypatch, FakeJudgeLLM([
        '{"retrieval_pass": false, "groundedness_pass": false, '
        '"completeness_pass": false}'
    ]))

    leaking_answers = {
        "What is the meal cap?": "The documents do not cover that. You could "
                                 "ask about our Workforce & People Policies instead.",
        "What is the travel cap?": "No such policy exists. Maybe check "
                                   "Finance & Planning.",
    }

    async def fake_generate_answer(query, chunks, **kwargs):
        return leaking_answers[query]

    monkeypatch.setattr(generation, "generate_answer", fake_generate_answer)

    entry_ok = GoldenEntry(**_entry(
        id="L-001",
        question="What is the meal cap?",
        forbidden_topics=["Workforce & People Policies", "Trust & Security"],
    ))
    entry_leak = GoldenEntry(**_entry(
        id="L-002",
        question="What is the travel cap?",
        forbidden_topics=["Finance & Planning"],
        expect_verdict="fail",
    ))
    report = await run_evaluation(
        [entry_ok, entry_leak], session=BoomDB(), user_id=uuid.uuid4()
    )

    by_id = {q.entry_id: q for q in report.questions}
    assert by_id["L-001"].topic_leak is True
    assert by_id["L-002"].topic_leak is True

    summary = report.summary()
    assert summary["negative_control_violations"] == ["L-002"]
    assert summary["negative_controls"]["L-002"]["topic_leak"] is True
    # topic_leak_pass counts pass-type entries that did not leak; L-001 did.
    assert summary["pass_rates"]["topic_leak_pass"] == 0.0


@pytest.mark.asyncio
async def test_topic_leak_clean_answer_passes_dimension(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    _stub_judge(monkeypatch, FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ]))

    entry = GoldenEntry(**_entry(
        forbidden_topics=["Workforce & People Policies"],
    ))
    report = await run_evaluation([entry], session=BoomDB(), user_id=uuid.uuid4())

    assert report.questions[0].topic_leak is False
    assert report.summary()["pass_rates"]["topic_leak_pass"] == 1.0


# ---------------------------------------------------------------------------
# Step 5 - judge pipeline (stubbed LLMs; no network in the default suite)
# ---------------------------------------------------------------------------


class FakeJudgeLLM:
    """Scripted judge: returns queued responses in order, last one repeats."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        idx = min(self.calls - 1, len(self.responses) - 1)
        return SimpleNamespace(content=self.responses[idx])


class RaisingJudge:
    """Judge whose provider is down: every call raises."""

    async def ainvoke(self, messages):
        raise RuntimeError("provider down")


def _stub_stages(monkeypatch, chunks):
    """Stub Stage-1 retrieval to deterministic chunks + stubbed generation."""
    spy = StageSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)

    generated = []

    async def fake_generate(query, chunks, **kwargs):
        generated.append(query)
        return "The meal cap is $75."

    monkeypatch.setattr(generation, "generate_answer", fake_generate)
    return spy, generated


def _stub_judge(monkeypatch, judge):
    monkeypatch.setattr(generation, "get_llm", lambda **kwargs: judge)


@pytest.mark.asyncio
async def test_run_evaluation_success_path(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    spy, generated = _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ])
    _stub_judge(monkeypatch, judge)

    entry = GoldenEntry(**_entry())
    report = await run_evaluation([entry], session=BoomDB(), user_id=uuid.uuid4())

    q = report.questions[0]
    assert isinstance(q, QuestionResult)
    assert q.entry_id == entry.id
    assert q.marker_recall is True
    assert q.retrieval_pass is True
    assert q.groundedness_pass is True
    assert q.completeness_pass is True
    assert q.judge_error is False
    assert generated == [entry.question]
    assert report.llm_calls == 2  # 1 generation + 1 judge attempt

    summary = report.summary()
    assert summary["pass_rates"]["marker_recall"] == 1.0
    assert summary["pass_rates"]["retrieval_pass"] == 1.0
    assert summary["negative_controls"] == {}
    assert summary["negative_control_violations"] == []
    assert summary["judge_errors"] == []


@pytest.mark.asyncio
async def test_run_evaluation_judge_retries_on_malformed_then_parses(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM([
        "this is prose, not json",
        '{"retrieval_pass": false, "groundedness_pass": true, '
        '"completeness_pass": false}',
    ])
    _stub_judge(monkeypatch, judge)

    report = await run_evaluation(
        [GoldenEntry(**_entry())], session=BoomDB(), user_id=uuid.uuid4()
    )

    q = report.questions[0]
    assert q.retrieval_pass is False
    assert q.groundedness_pass is True
    assert q.completeness_pass is False
    assert q.judge_error is False
    assert judge.calls == 2
    assert report.llm_calls == 3  # generation + 2 judge attempts


@pytest.mark.asyncio
async def test_run_evaluation_fails_closed_on_malformed_twice(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM(["not json at all", "still not json"])
    _stub_judge(monkeypatch, judge)

    entry = GoldenEntry(**_entry())
    report = await run_evaluation([entry], session=BoomDB(), user_id=uuid.uuid4())

    q = report.questions[0]
    assert q.retrieval_pass is False
    assert q.groundedness_pass is False
    assert q.completeness_pass is False
    assert q.judge_error is True
    assert judge.calls == 2
    assert report.llm_calls == 3

    summary = report.summary()
    assert summary["judge_errors"] == [entry.id]
    assert summary["pass_rates"]["retrieval_pass"] == 0.0


@pytest.mark.asyncio
async def test_run_evaluation_fails_closed_when_judge_call_raises(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    _stub_judge(monkeypatch, RaisingJudge())

    report = await run_evaluation(
        [GoldenEntry(**_entry())], session=BoomDB(), user_id=uuid.uuid4()
    )

    q = report.questions[0]
    assert q.retrieval_pass is False
    assert q.groundedness_pass is False
    assert q.completeness_pass is False
    assert q.judge_error is True
    assert report.llm_calls == 3  # generation + 2 judge attempts, both raising


@pytest.mark.asyncio
async def test_negative_control_scoring_pass_is_flagged_as_violation(monkeypatch):
    chunks = [FakeChunk("The cap of $75 applies.")]
    _stub_stages(monkeypatch, chunks)
    # A "contaminated" judge that passes everything, including the negative
    # control whose fabricated facts are absent from the corpus. This is the
    # failure mode the harness must flag prominently, never count as pass.
    judge = FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ])
    _stub_judge(monkeypatch, judge)

    pass_entry = GoldenEntry(**_entry())
    neg_entry = GoldenEntry(**_entry(
        id="NEG-3",
        expect_verdict="fail",
        expected_chunk_markers=["fabricated quarterly figure"],
        answer_facts=["the fabricated quarterly figure"],
    ))
    report = await run_evaluation(
        [pass_entry, neg_entry], session=BoomDB(), user_id=uuid.uuid4()
    )

    summary = report.summary()
    assert summary["negative_control_violations"] == [neg_entry.id]
    assert summary["negative_controls"][neg_entry.id]["retrieval_pass"] is True
    assert summary["negative_controls"][neg_entry.id]["marker_recall"] is False
    # Pass-type rates exclude the control: only the single pass entry counts.
    assert summary["pass_rates"]["retrieval_pass"] == 1.0
    assert sum(1 for q in report.questions if not q.is_negative_control) == 1


@pytest.mark.asyncio
async def test_negative_control_only_run_reports_separately(monkeypatch):
    chunks = [FakeChunk("This corpus contains no fabricated facts.")]
    _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM([
        '{"retrieval_pass": false, "groundedness_pass": false, '
        '"completeness_pass": false}'
    ])
    _stub_judge(monkeypatch, judge)

    neg_entry = GoldenEntry(**_entry(id="NEG-002", expect_verdict="fail"))
    report = await run_evaluation(
        [neg_entry], session=BoomDB(), user_id=uuid.uuid4()
    )

    summary = report.summary()
    assert summary["negative_controls"]["NEG-002"]["retrieval_pass"] is False
    assert summary["negative_control_violations"] == []
    # No pass-type entries -> rates are None, not a distorted zero.
    assert summary["pass_rates"]["retrieval_pass"] is None


# ---------------------------------------------------------------------------
# Prerequisite - get_llm temperature/model pinning (no network in tests)
# ---------------------------------------------------------------------------


def test_get_llm_default_temperature_is_unchanged(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    llm = generation.get_llm()
    assert hasattr(llm, "runnable")  # cascade wrapper
    assert llm.runnable.temperature == 0.3
    assert all(fb.temperature == 0.3 for fb in llm.fallbacks)


def test_get_llm_temperature_override_applied_everywhere(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    llm = generation.get_llm(temperature=0.7)
    assert llm.runnable.temperature == 0.7
    assert all(fb.temperature == 0.7 for fb in llm.fallbacks)


def test_get_llm_pinned_model_bypasses_cascade(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    pinned = generation.get_llm(
        temperature=0.0, model_name=get_settings().EVAL_JUDGE_MODEL
    )
    # ChatGroq normalizes temperature 0 to ~1e-8 at construction time.
    assert pinned.temperature == pytest.approx(0.0, abs=1e-7)
    assert pinned.model_name == get_settings().EVAL_JUDGE_MODEL
    assert not hasattr(pinned, "runnable")  # single model, no fallbacks


def test_get_llm_pinned_requires_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    class GeminiOnlySettings:
        GROQ_API_KEY = None
        GEMINI_API_KEY = "gemini-test"

    # Pin the module-level settings so real .env keys can't leak in.
    monkeypatch.setattr(generation, "settings", GeminiOnlySettings())

    with pytest.raises(RuntimeError, match="GROQ_API_KEY is required"):
        generation.get_llm(temperature=0.0, model_name="qwen3-32b")




# ---------------------------------------------------------------------------
# Step 5 - negative-control violation semantics (fabrication-leak check)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_control_with_grounded_completeness_pass_is_not_a_violation(monkeypatch):
    """An honest-refusal answer is legitimately grounded in unrelated context:
    groundedness/completeness True on a control must NOT trip a violation;
    only retrievable fabricated info (marker_recall/retrieval_pass) does."""
    chunks = [FakeChunk("The corpus says full-time staff accrue 25 days of PTO.")]
    _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM([
        '{"retrieval_pass": false, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ])
    _stub_judge(monkeypatch, judge)

    neg_entry = GoldenEntry(**_entry(
        id="NEG-004",
        expect_verdict="fail",
        expected_chunk_markers=["contractors receive 40 days of leave"],
        answer_facts=["contractors accrue 40 days of PTO"],
    ))
    report = await run_evaluation([neg_entry], session=BoomDB(), user_id=uuid.uuid4())

    summary = report.summary()
    assert summary["negative_controls"]["NEG-004"]["groundedness_pass"] is True
    assert summary["negative_controls"]["NEG-004"]["completeness_pass"] is True
    assert summary["negative_control_violations"] == []
    assert summary["pass_rates"]["retrieval_pass"] is None


@pytest.mark.asyncio
async def test_control_with_retrievable_marker_is_a_violation(monkeypatch):
    """The real validity failure: fabricated marker shows up in retrieved text."""
    chunks = [FakeChunk("The contractors receive 40 days of leave per the policy.")]
    _stub_stages(monkeypatch, chunks)
    judge = FakeJudgeLLM([
        '{"retrieval_pass": true, "groundedness_pass": true, '
        '"completeness_pass": true}'
    ])
    _stub_judge(monkeypatch, judge)

    neg_entry = GoldenEntry(**_entry(
        id="NEG-005",
        expect_verdict="fail",
        expected_chunk_markers=["contractors receive 40 days of leave"],
        answer_facts=["contractors accrue 40 days of PTO"],
    ))
    report = await run_evaluation([neg_entry], session=BoomDB(), user_id=uuid.uuid4())

    summary = report.summary()
    assert summary["negative_control_violations"] == ["NEG-005"]
    assert summary["negative_controls"]["NEG-005"]["marker_recall"] is True

