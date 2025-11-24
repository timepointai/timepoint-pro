#!/usr/bin/env python3
"""
Unit tests for JSON extraction from LLM responses.

Tests the robust _extract_json_from_response() function that handles:
- Plain JSON
- JSON with preambles
- JSON with markdown fences
- JSON with both preambles and fences
- Nested objects and arrays
"""
import pytest
from tensor_initialization import _extract_json_from_response
import json


def test_plain_json():
    """Test extraction of plain JSON object"""
    content = '{"key": "value", "number": 42}'
    result = _extract_json_from_response(content)
    assert result == '{"key": "value", "number": 42}'
    # Verify it's valid JSON
    parsed = json.loads(result)
    assert parsed["key"] == "value"
    assert parsed["number"] == 42


def test_json_with_preamble():
    """Test extraction when LLM adds explanatory text before JSON"""
    content = '''Here is the suggested fix:

{"fixes": {"context": [0.1], "biology": [], "behavior": []}}

Explanation: I set context[0] to 0.1 as a reasonable baseline.'''
    result = _extract_json_from_response(content)
    # Should extract just the JSON part
    parsed = json.loads(result)
    assert "fixes" in parsed
    assert parsed["fixes"]["context"] == [0.1]


def test_json_with_markdown_fences():
    """Test extraction from markdown code blocks"""
    content = '''```json
{
  "fixes": {
    "context": [0.05, 0.5, 0.3, 1.0],
    "biology": [],
    "behavior": []
  }
}
```'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed["fixes"]["context"] == [0.05, 0.5, 0.3, 1.0]


def test_json_with_preamble_and_fences():
    """Test extraction with both preamble and markdown fences"""
    content = '''Based on the provided information, I'll suggest non-zero values:

```json
{"fixes": {"context": [0.1], "biology": [], "behavior": []}}
```

This sets a reasonable baseline.'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert "fixes" in parsed


def test_nested_json_objects():
    """Test extraction of deeply nested JSON structures"""
    content = '''Here's the analysis:

{"context_adjustments": [0.5, 0.6, 0.7], "metadata": {"nested": {"deeply": {"key": "value"}}}}'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed["metadata"]["nested"]["deeply"]["key"] == "value"


def test_json_array():
    """Test extraction of JSON arrays"""
    content = '''The refinements are: [0.1, 0.2, 0.3, 0.4, 0.5]'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed == [0.1, 0.2, 0.3, 0.4, 0.5]


def test_json_with_escaped_quotes():
    """Test extraction of JSON with escaped quotes in strings"""
    content = '''{"message": "He said \\"hello\\"", "value": 42}'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed["message"] == 'He said "hello"'


def test_actual_log_sample_1():
    """Test with actual response from logs (line 7)"""
    content = '''Here is the suggested fix:

{"fixes": {"context": [0.1], "biology": [], "behavior": []}}

Explanation: context[0] represents knowledge count, setting to 0.1 provides a minimal baseline.'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed["fixes"]["context"] == [0.1]


def test_actual_log_sample_2():
    """Test with actual response from logs (line 8)"""
    content = '''Here is the JSON output with suggested non-zero values for the zero indices:

```
{
  "fixes": {
    "context": [0.1, 0.5, 0.3, 1.0, 0.5, 0.5, 0.5, 0.5],
    "biology": [],
    "behavior": []
  }
}
```'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert len(parsed["fixes"]["context"]) == 8


def test_actual_log_sample_3():
    """Test with actual response from logs (line 9)"""
    content = '''Here is the suggested fix in JSON format:

```json
{
  "fixes": {
    "context": [0.05, 0.5, 0.3, 1.0, 0.5, 0.5, 0.5, 0.5],
    "biology": [0.35, 0.8, 1.0, 0.8],
    "behavior": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
  }
}
```

Explanation: The suggested values maintain the structure while filling zeros with reasonable defaults.'''
    result = _extract_json_from_response(content)
    parsed = json.loads(result)
    assert parsed["fixes"]["context"][0] == 0.05
    assert len(parsed["fixes"]["biology"]) == 4
    assert len(parsed["fixes"]["behavior"]) == 8


def test_no_json_found():
    """Test error handling when no JSON structure exists"""
    content = "This is just plain text with no JSON at all."
    with pytest.raises(ValueError, match="No JSON structure found"):
        _extract_json_from_response(content)


def test_unbalanced_brackets():
    """Test error handling for unbalanced brackets"""
    content = '{"key": "value"'  # Missing closing brace
    with pytest.raises(ValueError, match="Unbalanced brackets"):
        _extract_json_from_response(content)


def test_empty_content():
    """Test error handling for empty content"""
    with pytest.raises(ValueError, match="No JSON structure found"):
        _extract_json_from_response("")


def test_whitespace_only():
    """Test error handling for whitespace-only content"""
    with pytest.raises(ValueError, match="No JSON structure found"):
        _extract_json_from_response("   \n\t  ")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
