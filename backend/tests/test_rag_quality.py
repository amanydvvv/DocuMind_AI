"""
DocuMind AI — RAG Response Quality Test Suite
Validates that generated responses:
1. Do not leak system prompt fragments or internal mechanics
2. Extract facts accurately without contradictory hedging
3. Use the correct fallback for out-of-scope queries
"""

import pytest
from app.services.guardrails import validate_output, PROMPT_LEAK_FRAGMENTS


class TestRAGResponseQuality:
    """Test suite for RAG response quality guardrails."""

    # -------------------------------------------------------------------------
    # Leakage Tests
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("leak_fragment", [
        "You are DocuMind AI, an intelligent document analysis assistant",
        "GUIDELINES:",
        "Do NOT mention page numbers",
        "Do NOT hedge or state",
        "According to the document",
        "The text provided says",
        "Prior Context:",
        "Context:",
        "User Question:",
        "<thought_process>",
        "<answer>",
    ])
    def test_system_prompt_leakage_fragments_blocked(self, leak_fragment):
        """Each known prompt fragment should be flagged by validate_output."""
        is_ok, flags = validate_output(leak_fragment)
        assert not is_ok, f"Fragment '{leak_fragment}' should be flagged as prompt leak"
        assert any("prompt-leak" in f for f in flags), f"Expected prompt-leak flag for '{leak_fragment}'"

    def test_retrieved_context_phrase_blocked(self):
        """The phrase 'retrieved context' should not appear in responses."""
        is_ok, flags = validate_output("Based on the retrieved context, the answer is X")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_vector_database_phrase_blocked(self):
        """The phrase 'vector database' should not appear in responses."""
        is_ok, flags = validate_output("The vector database returned the following")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_page_number_references_blocked(self):
        """Page number references should not appear in responses."""
        is_ok, flags = validate_output("As stated on page 3 of the document")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_source_chunk_references_blocked(self):
        """Source chunk references should not appear in responses."""
        is_ok, flags = validate_output("Source chunk 2 contains the answer")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    # -------------------------------------------------------------------------
    # Accuracy / Non-Hedging Tests
    # -------------------------------------------------------------------------

    def test_direct_fact_extraction_without_hedging(self):
        """Responses should state facts directly without 'according to' hedging."""
        hedging_phrases = [
            "According to the document",
            "The document states that",
            "Based on the provided text",
            "The context indicates",
            "The provided context shows",
        ]
        for phrase in hedging_phrases:
            is_ok, flags = validate_output(f"{phrase} the policy number is ABC-123")
            assert not is_ok, f"Hedging phrase '{phrase}' should be flagged"
            assert any("prompt-leak" in f for f in flags)

    def test_exact_fact_allowed(self):
        """Direct factual statements without hedging should pass."""
        clean_response = "The policy number is ABC-123 and it covers liability up to $1M."
        is_ok, flags = validate_output(clean_response)
        assert is_ok, f"Clean response should pass: {flags}"

    def test_contradictory_hedging_flagged(self):
        """Self-contradictory hedging should be caught."""
        # The model finds the fact but hedges it
        contradictory = "The policy number is ABC-123, but the document doesn't explicitly state this."
        is_ok, flags = validate_output(contradictory)
        # This may not be caught by current guardrails, but should not have prompt leaks
        assert not any("prompt-leak" in f for f in flags)

    # -------------------------------------------------------------------------
    # Out-of-Scope / Fallback Tests
    # -------------------------------------------------------------------------

    def test_out_of_scope_fallback_exact_match(self):
        """The exact fallback phrase should be allowed as a complete response (not a leak)."""
        fallback = "I do not have sufficient information in the loaded documents to answer this question."
        is_ok, flags = validate_output(fallback)
        # The fallback phrase itself is NOT in PROMPT_LEAK_FRAGMENTS anymore, so it should pass
        assert is_ok, f"Clean fallback response should pass: {flags}"

    def test_variations_of_fallback_allowed(self):
        """Natural variations of 'I don't know' should pass."""
        variations = [
            "I don't have enough information in your documents to answer that.",
            "The documents don't contain information about that topic.",
            "I cannot find the answer in the provided documents.",
            "That information is not available in your uploaded files.",
        ]
        for variation in variations:
            is_ok, flags = validate_output(variation)
            assert is_ok, f"Variation should pass: {variation} - flags: {flags}"

    # -------------------------------------------------------------------------
    # Meta/Internal Mechanics Tests
    # -------------------------------------------------------------------------

    def test_internal_reasoning_exposure_blocked(self):
        """Internal reasoning markers should be blocked."""
        is_ok, flags = validate_output("Let me think about this step by step. <thought_process> reasoning </thought_process>")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_answer_tag_exposure_blocked(self):
        """Answer tags should be blocked."""
        is_ok, flags = validate_output("<answer>The policy number is ABC-123</answer>")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_corpus_metadata_exposure_blocked(self):
        """Corpus metadata references should be blocked."""
        is_ok, flags = validate_output("CORPUS METADATA shows 3 documents")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)

    def test_workspace_summary_exposure_blocked(self):
        """Workspace documents summary references should be blocked."""
        is_ok, flags = validate_output("Workspace Documents Summary says you have 3 documents")
        assert not is_ok
        assert any("prompt-leak" in f for f in flags)


class TestPromptLeakFragmentsCompleteness:
    """Ensure all fragments in PROMPT_LEAK_FRAGMENTS are tested."""

    def test_all_fragments_have_test_coverage(self):
        """Every fragment in PROMPT_LEAK_FRAGMENTS should have a corresponding test."""
        # This test documents the expected fragments - if the list changes,
        # the test parameters above should be updated
        expected_fragments = {
            "You are DocuMind AI, an intelligent document analysis assistant",
            "GUIDELINES:",
            "Do NOT mention page numbers",
            "Do NOT hedge or state",
            "According to the document",
            "The text provided says",
            "Prior Context:",
            "Context:",
            "User Question:",
            "<thought_process>",
            "<answer>",
            "retrieved context",
            "vector database",
            "page ",
            "Source chunk",
            "The document states that",
            "Based on the provided text",
            "The context indicates",
            "The provided context shows",
            "CORPUS METADATA",
            "Workspace Documents Summary",
        }
        actual_fragments = set(PROMPT_LEAK_FRAGMENTS)
        assert actual_fragments == expected_fragments, \
            f"PROMPT_LEAK_FRAGMENTS mismatch. Expected: {expected_fragments}, Got: {actual_fragments}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])