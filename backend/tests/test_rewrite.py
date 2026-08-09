"""
DocuMind AI - follow-up rewrite_followup() unit tests.

Pure offline tests: get_llm() is stubbed, no network. Proves the
fail-closed contract of app.services.rewrite: the raw question is the
default on every trigger miss, timeout, LLM/parse error, low-confidence
output, and sanity-cap breach, and a successful rewrite carries the
conversation history into the prompt.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

import app.services.rewrite as rewrite
from app.services.rewrite import (
    REWRITE_MAX_QUERY_CHARS,
    rewrite_followup,
)


def _user(content):
    return SimpleNamespace(role="user", content=content)


def _assistant(content):
    return SimpleNamespace(role="assistant", content=content)


class FakeRewriteLLM:
    """Scripted rewrite LLM: records the prompt, returns queued raw texts."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.prompts = []

    async def ainvoke(self, messages):
        self.calls += 1
        self.prompts.append(messages)
        idx = min(self.calls - 1, len(self.responses) - 1)
        text = self.responses[idx] if idx < len(self.responses) else "{}"
        if isinstance(text, Exception):
            raise text
        if isinstance(text, str) and text.startswith("SLOW:"):
            await asyncio.sleep(300)
            raise AssertionError("should have timed out")
        return SimpleNamespace(content=text)


def _stub_llm(monkeypatch, fake):
    monkeypatch.setattr(
        rewrite, "get_llm", lambda temperature=0.0: fake
    )


def _json_response(rewritten, confident=True):
    return json.dumps({"rewritten": rewritten, "confident": confident})


@pytest.mark.asyncio
async def test_raw_question_without_prior_user_turn(monkeypatch):
    called = []

    def boom_get_llm(**kwargs):
        called.append(True)
        raise AssertionError("rewrite must not call the LLM without history")

    monkeypatch.setattr(rewrite, "get_llm", boom_get_llm)

    result = await rewrite_followup("Where does the replica run?", [])
    assert result == "Where does the replica run?"

    result = await rewrite_followup("Any updates?", [_assistant("No.")])
    assert result == "Any updates?"
    assert not called


@pytest.mark.asyncio
async def test_rewrite_carries_history_into_prompt_and_returns_query(monkeypatch):
    fake = FakeRewriteLLM([
        _json_response(
            "Where does the disaster-recovery replica for the "
            "us-east-1 control plane run?"
        )
    ])
    _stub_llm(monkeypatch, fake)

    result = await rewrite_followup(
        "Where does the replica for that region run?",
        [
            _user("Which AWS region hosts the primary control plane?"),
            _assistant("The primary region is us-east-1."),
        ],
    )

    assert (
        result
        == "Where does the disaster-recovery replica for the "
        "us-east-1 control plane run?"
    )
    prompt_text = fake.prompts[0][0]["content"]
    assert "Which AWS region hosts the primary control plane?" in prompt_text
    assert "The primary region is us-east-1." in prompt_text
    assert "Where does the replica for that region run?" in prompt_text


@pytest.mark.asyncio
async def test_raw_question_when_llm_low_confidence(monkeypatch):
    fake = FakeRewriteLLM([
        _json_response(
            "How many times does Kestrel retry a failed batch step?",
            confident=False,
        )
    ])
    _stub_llm(monkeypatch, fake)

    result = await rewrite_followup(
        "How many times does it retie a failed batch step?",
        [_user("How many times does Kestrel retry a failed batch step?")],
    )
    assert result == "How many times does it retie a failed batch step?"


@pytest.mark.asyncio
async def test_raw_question_on_malformed_output(monkeypatch):
    for bad in ("this is prose", "[1, 2, 3]", '{"rewritten": "x"}', ""):
        fake = FakeRewriteLLM([bad])
        _stub_llm(monkeypatch, fake)
        result = await rewrite_followup(
            "Follow up?", [_user("Prior question?")]
        )
        assert result == "Follow up?"


@pytest.mark.asyncio
async def test_raw_question_when_llm_raises(monkeypatch):
    fake = FakeRewriteLLM([RuntimeError("provider down")])
    _stub_llm(monkeypatch, fake)

    result = await rewrite_followup("Follow up?", [_user("Prior question?")])
    assert result == "Follow up?"


@pytest.mark.asyncio
async def test_raw_question_when_rewrite_times_out(monkeypatch):
    fake = FakeRewriteLLM(["SLOW:garbage"])
    _stub_llm(monkeypatch, fake)
    monkeypatch.setattr(rewrite, "REWRITE_TIMEOUT_SECONDS", 0.05)

    result = await rewrite_followup("Follow up?", [_user("Prior question?")])
    assert result == "Follow up?"


@pytest.mark.asyncio
async def test_raw_question_when_rewritten_breaches_sanity_caps(monkeypatch):
    fake = FakeRewriteLLM([
        _json_response("x" * (REWRITE_MAX_QUERY_CHARS + 1)),
        _json_response(""),
    ])
    _stub_llm(monkeypatch, fake)

    result = await rewrite_followup("Follow up?", [_user("Prior question?")])
    assert result == "Follow up?"

    result = await rewrite_followup("Follow up?", [_user("Prior question?")])
    assert result == "Follow up?"


@pytest.mark.asyncio
async def test_rewritten_identical_to_raw_returns_raw(monkeypatch):
    fake = FakeRewriteLLM([_json_response("Follow up?")])
    _stub_llm(monkeypatch, fake)

    result = await rewrite_followup("Follow up?", [_user("Prior question?")])
    assert result == "Follow up?"


def test_history_turns_excludes_blanks_and_caps_tail():
    turns = rewrite._history_turns([
        _user("one"),
        _assistant("  "),
        _user("two"),
        SimpleNamespace(role="user", content=None),
        _user("three"),
    ])
    assert turns == ["User: three", "User: two", "User: one"]