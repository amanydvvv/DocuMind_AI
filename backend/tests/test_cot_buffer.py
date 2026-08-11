"""
DocuMind AI — CoT Streaming Buffer & Prompt Leakage Prevention Tests
Verifies server-side StreamCoTBuffer state machine and CoT extraction logic.
"""

import pytest
from app.services.generation import (
    StreamCoTBuffer,
    extract_answer_from_cot,
    _build_resolved_query_section,
    _format_context_text,
)
from app.models import Chunk


def test_cot_buffer_standard_flow():
    buffer = StreamCoTBuffer()
    tokens = [
        "<thought_process>\nEvaluating query for two-wheeler policy...",
        "\nFound policy number D277856892 in chunk.\n",
        "</thought_process>\n",
        "<answer>",
        "\nThe policy number for your two-wheeler insurance is D277856892.",
        "\n</answer>",
    ]

    output_deltas = []
    for token in tokens:
        output_deltas.extend(buffer.process_token(token))
    output_deltas.extend(buffer.finalize())

    result_text = "".join(output_deltas)
    assert "D277856892" in result_text
    assert "<thought_process>" not in result_text
    assert "Evaluating query" not in result_text
    assert "<answer>" not in result_text
    assert "</answer>" not in result_text


def test_cot_buffer_split_tag_tokens():
    buffer = StreamCoTBuffer()
    tokens = [
        "<thought_process>Hidden reasoning</thought_process><ans",
        "wer>Direct answer text</ans",
        "wer>",
    ]

    output_deltas = []
    for token in tokens:
        output_deltas.extend(buffer.process_token(token))
    output_deltas.extend(buffer.finalize())

    result_text = "".join(output_deltas)
    assert result_text == "Direct answer text"


def test_cot_buffer_no_cot_fallback():
    buffer = StreamCoTBuffer()
    tokens = ["Direct response without ", "any CoT tags."]

    output_deltas = []
    for token in tokens:
        output_deltas.extend(buffer.process_token(token))
    output_deltas.extend(buffer.finalize())

    result_text = "".join(output_deltas)
    assert result_text == "Direct response without any CoT tags."


def test_extract_answer_from_cot():
    raw_cot = (
        "<thought_process>\n"
        "Analyzing retrieved context...\n"
        "Notice CORPUS METADATA says 1 document.\n"
        "</thought_process>\n"
        "<answer>\n"
        "Your policy number is D277856892.\n"
        "</answer>"
    )
    cleaned = extract_answer_from_cot(raw_cot)
    assert cleaned == "Your policy number is D277856892."
    assert "CORPUS METADATA" not in cleaned
    assert "thought_process" not in cleaned


def test_format_context_text_uses_display_title():
    chunk = Chunk(
        content="Policy D277856892 covers two-wheelers.",
        page_number=1,
        metadata_={"filename": "DG_20201AGENT_SCHEDULESC...pdf", "display_title": "Two-Wheeler Insurance Policy"},
    )
    context_str = _format_context_text([chunk])
    assert "Two-Wheeler Insurance Policy" in context_str
    assert "DG_20201AGENT_SCHEDULESC" not in context_str


def test_format_context_text_surfaces_raw_relevance_when_present():
    """Test that the new context format includes the display title and content."""
    chunk = Chunk(
        content="Policy D277856892 covers two-wheelers.",
        page_number=1,
        metadata_={"display_title": "Two-Wheeler Insurance Policy", "raw_similarity": 0.7317},
    )
    context_str = _format_context_text([chunk])
    # New format: [Title]\nContent
    assert "Two-Wheeler Insurance Policy" in context_str
    assert "Policy D277856892 covers two-wheelers." in context_str
    # Raw relevance is no longer included in the context (prevents leakage)
    assert "Raw relevance" not in context_str


def test_format_context_text_omits_raw_relevance_when_absent():
    """Test that the new context format works without raw_similarity."""
    chunk = Chunk(
        content="Policy D277856892 covers two-wheelers.",
        page_number=1,
        metadata_={"display_title": "Two-Wheeler Insurance Policy"},
    )
    context_str = _format_context_text([chunk])
    assert "Two-Wheeler Insurance Policy" in context_str
    assert "Policy D277856892 covers two-wheelers." in context_str
    assert "Raw relevance" not in context_str


def test_build_resolved_query_section_only_when_different():
    assert _build_resolved_query_section("Where is it?", "") == ""
    assert _build_resolved_query_section("Where is it?", None) == ""
    assert (
        _build_resolved_query_section(
            "Where is it?", "Where does the replica for us-east-1 run?"
        )
        == "Resolved Query: Where does the replica for us-east-1 run?"
    )
    # Same as the raw query: no rewrite happened, no section.
    assert _build_resolved_query_section("Where is it?", "Where is it?") == ""
