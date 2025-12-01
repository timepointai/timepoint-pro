"""
Unit tests for dialog synthesis functions.

Tests the core dialog synthesis utilities:
- extract_knowledge_references: Extract capitalized words from dialog content
"""

import pytest
from workflows.dialog_synthesis import extract_knowledge_references


class TestExtractKnowledgeReferences:
    """Tests for extract_knowledge_references function."""

    def test_extracts_capitalized_words(self):
        """Should extract capitalized words as knowledge references."""
        content = "I spoke with President Lincoln about the Constitution."

        result = extract_knowledge_references(content)

        assert "president" in result
        assert "lincoln" in result
        assert "constitution" in result

    def test_ignores_short_words(self):
        """Should ignore words <= 3 characters even if capitalized."""
        content = "The CEO of the USA met with IBM."

        result = extract_knowledge_references(content)

        # "The", "CEO", "USA", "IBM" are all <= 3 chars, should be ignored
        assert len(result) == 0

    def test_strips_punctuation(self):
        """Should strip punctuation before checking capitalization."""
        content = "Washington, Jefferson, and Lincoln."

        result = extract_knowledge_references(content)

        assert "washington" in result
        assert "jefferson" in result
        assert "lincoln" in result

    def test_returns_lowercase(self):
        """Should return lowercase versions for consistent comparison."""
        content = "PRESIDENT Lincoln met GENERAL Grant."

        result = extract_knowledge_references(content)

        # All should be lowercase
        for item in result:
            assert item == item.lower()

    def test_returns_unique_items(self):
        """Should return unique items only."""
        content = "Lincoln met Lincoln and Lincoln again."

        result = extract_knowledge_references(content)

        assert result.count("lincoln") == 1

    def test_empty_string(self):
        """Should handle empty string gracefully."""
        content = ""

        result = extract_knowledge_references(content)

        assert result == []

    def test_no_capitalized_words(self):
        """Should return empty list if no capitalized words found."""
        content = "this is all lowercase text without proper nouns"

        result = extract_knowledge_references(content)

        assert result == []

    def test_mixed_content(self):
        """Should work with mixed content."""
        content = "The meeting included Secretary Hamilton, Mr. Adams, and the young officer."

        result = extract_knowledge_references(content)

        # Should find: Secretary, Hamilton, Adams (but not "The", "Mr." since <= 3 chars)
        assert "secretary" in result
        assert "hamilton" in result
        assert "adams" in result

    def test_handles_various_punctuation(self):
        """Should handle various punctuation marks."""
        content = '"Jefferson!" exclaimed Washington. (Adams) was [present].'

        result = extract_knowledge_references(content)

        assert "jefferson" in result
        assert "washington" in result
        assert "adams" in result
        # "present" is not capitalized

    def test_sentence_start_words_included(self):
        """Words at sentence start are capitalized and should be included if > 3 chars."""
        content = "Regarding the matter. Concerning the issue."

        result = extract_knowledge_references(content)

        # "Regarding" and "Concerning" are capitalized at sentence start and > 3 chars
        assert "regarding" in result
        assert "concerning" in result
