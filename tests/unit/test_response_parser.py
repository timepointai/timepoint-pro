"""Tests for ResponseParser JSON extraction — especially bracket-depth matching."""

import pytest

from llm_service.response_parser import ParseError, ResponseParser


@pytest.fixture
def parser():
    return ResponseParser(strict=False)


class TestExtractJson:
    """Test extract_json with various LLM response formats."""

    def test_plain_json_object(self, parser):
        text = '{"entity_id": "hamilton", "score": 0.9}'
        assert parser.extract_json(text) == text

    def test_plain_json_array(self, parser):
        text = '[{"id": 1}, {"id": 2}]'
        assert parser.extract_json(text) == text

    def test_markdown_code_block(self, parser):
        text = '```json\n{"entity_id": "hamilton"}\n```'
        result = parser.extract_json(text)
        assert '"hamilton"' in result

    def test_text_before_json(self, parser):
        text = 'Here is the result:\n{"entity_id": "hamilton", "score": 0.9}'
        result = parser.extract_json(text)
        assert '"hamilton"' in result

    def test_text_after_json(self, parser):
        text = '{"entity_id": "hamilton", "score": 0.9}\n\nI hope this helps!'
        result = parser.extract_json(text)
        assert '"hamilton"' in result

    def test_text_wrapping_json(self, parser):
        text = (
            "Based on analysis:\n\n"
            '{"entity_id": "hamilton", "knowledge_state": ["fact1", "fact2"]}\n\n'
            "Explanation of the above..."
        )
        result = parser.extract_json(text)
        assert '"hamilton"' in result
        assert '"fact2"' in result

    def test_nested_objects(self, parser):
        text = '{"outer": {"inner": {"deep": true}}, "list": [1, 2, 3]}'
        result = parser.extract_json(text)
        assert '"deep"' in result

    def test_escaped_quotes_in_strings(self, parser):
        text = r'{"name": "Alexander \"The Treasury\" Hamilton", "id": 1}'
        result = parser.extract_json(text)
        assert '"id"' in result

    def test_brackets_inside_strings(self, parser):
        """Brackets inside string values should not confuse the parser."""
        text = '{"description": "array [1,2] and object {a:b}", "valid": true}'
        result = parser.extract_json(text)
        assert '"valid"' in result

    def test_no_json_raises_parse_error(self, parser):
        with pytest.raises(ParseError, match="No valid JSON found"):
            parser.extract_json("This is just plain text with no JSON at all.")

    def test_truncated_json_raises_parse_error(self, parser):
        """Truncated JSON (unbalanced brackets) should fail cleanly."""
        text = '{"entity_id": "hamilton", "knowledge_state": ['
        with pytest.raises(ParseError, match="No valid JSON found"):
            parser.extract_json(text)


class TestExtractByBracketMatching:
    """Direct tests for the bracket-depth matching method."""

    def test_hamilton_entity_response(self, parser):
        """Reproduce the exact failure from the jefferson_dinner run.

        The LLM returned a valid JSON object with text-wrapped content,
        which the old greedy regex failed to extract.
        """
        text = (
            "{\n"
            '  "entity_id": "alexander_hamilton",\n'
            '  "knowledge_state": [\n'
            '    "Served as first Secretary of the Treasury from 1789 to 1795",\n'
            '    "Played a key role in shaping the financial system",\n'
            '    "Advocated for a strong central government"\n'
            "  ],\n"
            '  "emotional_state": {\n'
            '    "valence": 0.3,\n'
            '    "arousal": 0.5\n'
            "  }\n"
            "}"
        )
        result = parser._extract_by_bracket_matching(text)
        assert result is not None
        import json

        parsed = json.loads(result)
        assert parsed["entity_id"] == "alexander_hamilton"
        assert len(parsed["knowledge_state"]) == 3

    def test_returns_none_for_no_brackets(self, parser):
        assert parser._extract_by_bracket_matching("no json here") is None

    def test_returns_none_for_unbalanced(self, parser):
        """Truncated response with unbalanced brackets returns None."""
        text = '{"entity_id": "hamilton", "data": ['
        assert parser._extract_by_bracket_matching(text) is None

    def test_first_balanced_object_returned(self, parser):
        """When multiple JSON objects exist, returns the first complete one."""
        text = '{"a": 1} then {"b": 2}'
        result = parser._extract_by_bracket_matching(text)
        import json

        assert json.loads(result) == {"a": 1}

    def test_array_extraction(self, parser):
        text = 'result: [1, 2, {"nested": true}]'
        result = parser._extract_by_bracket_matching(text)
        import json

        parsed = json.loads(result)
        assert len(parsed) == 3

    def test_newlines_in_strings(self, parser):
        """JSON with escaped newlines in string values."""
        text = r'{"text": "line1\nline2\nline3", "count": 3}'
        result = parser._extract_by_bracket_matching(text)
        assert result is not None
        import json

        assert json.loads(result)["count"] == 3
