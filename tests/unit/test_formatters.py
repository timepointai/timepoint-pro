"""
Tests for Output Formatters (Sprint 2.2)
"""

import pytest
import json
import csv
from io import StringIO
from reporting.formatters import (
    MarkdownFormatter,
    JSONFormatter,
    CSVFormatter,
    FormatterFactory
)


class TestMarkdownFormatter:
    """Tests for Markdown formatting"""

    def test_format_title(self):
        """Test title formatting"""
        formatter = MarkdownFormatter()
        data = {"title": "Test Report"}
        result = formatter.format(data)
        assert "# Test Report" in result

    def test_format_metadata(self):
        """Test metadata section formatting"""
        formatter = MarkdownFormatter()
        data = {
            "title": "Test Report",
            "metadata": {
                "world_id": "test_world",
                "generated_at": "2025-10-21"
            }
        }
        result = formatter.format(data)
        assert "## Metadata" in result
        assert "- **world_id**: test_world" in result
        assert "- **generated_at**: 2025-10-21" in result

    def test_format_summary(self):
        """Test summary section formatting"""
        formatter = MarkdownFormatter()
        data = {
            "title": "Test Report",
            "summary": "This is a test summary."
        }
        result = formatter.format(data)
        assert "## Summary" in result
        assert "This is a test summary." in result

    def test_format_sections(self):
        """Test sections formatting"""
        formatter = MarkdownFormatter()
        data = {
            "title": "Test Report",
            "sections": [
                {
                    "title": "Section 1",
                    "content": "Content for section 1"
                },
                {
                    "title": "Section 2",
                    "items": ["Item 1", "Item 2", "Item 3"]
                }
            ]
        }
        result = formatter.format(data)
        assert "## Section 1" in result
        assert "Content for section 1" in result
        assert "## Section 2" in result
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_format_table(self):
        """Test table formatting"""
        formatter = MarkdownFormatter()
        data = {
            "title": "Test Report",
            "tables": [
                {
                    "title": "Test Table",
                    "headers": ["Name", "Age", "City"],
                    "rows": [
                        ["Alice", 30, "NYC"],
                        ["Bob", 25, "LA"],
                        ["Charlie", 35, "Chicago"]
                    ]
                }
            ]
        }
        result = formatter.format(data)
        assert "### Test Table" in result
        assert "| Name | Age | City |" in result
        assert "| --- | --- | --- |" in result
        assert "| Alice | 30 | NYC |" in result
        assert "| Bob | 25 | LA |" in result
        assert "| Charlie | 35 | Chicago |" in result

    def test_format_table_without_headers(self):
        """Test table formatting handles missing headers gracefully"""
        formatter = MarkdownFormatter()
        data = {
            "tables": [
                {
                    "title": "Incomplete Table",
                    "rows": [["data1", "data2"]]
                }
            ]
        }
        result = formatter.format(data)
        # Should not crash, but table won't be formatted
        assert "### Incomplete Table" in result

    def test_format_complete_report(self):
        """Test complete report with all sections"""
        formatter = MarkdownFormatter()
        data = {
            "title": "Complete Report",
            "metadata": {
                "world_id": "test_world",
                "entity_count": 10
            },
            "summary": "Full simulation summary",
            "sections": [
                {
                    "title": "Key Events",
                    "items": ["Event 1", "Event 2"]
                }
            ],
            "tables": [
                {
                    "title": "Entity Stats",
                    "headers": ["Entity", "Actions"],
                    "rows": [["Alice", 5], ["Bob", 3]]
                }
            ]
        }
        result = formatter.format(data)
        assert "# Complete Report" in result
        assert "## Metadata" in result
        assert "## Summary" in result
        assert "## Key Events" in result
        assert "### Entity Stats" in result


class TestJSONFormatter:
    """Tests for JSON formatting"""

    def test_format_simple_data(self):
        """Test simple data formatting"""
        formatter = JSONFormatter(indent=2)
        data = {"key": "value", "number": 42}
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["number"] == 42

    def test_format_nested_data(self):
        """Test nested data formatting"""
        formatter = JSONFormatter(indent=2)
        data = {
            "title": "Test Report",
            "metadata": {
                "world_id": "test_world",
                "stats": {
                    "entities": 10,
                    "timepoints": 5
                }
            }
        }
        result = formatter.format(data)
        parsed = json.loads(result)
        assert parsed["metadata"]["stats"]["entities"] == 10

    def test_format_with_lists(self):
        """Test formatting with lists"""
        formatter = JSONFormatter()
        data = {
            "entities": ["alice", "bob", "charlie"],
            "events": [
                {"type": "action", "actor": "alice"},
                {"type": "speech", "actor": "bob"}
            ]
        }
        result = formatter.format(data)
        parsed = json.loads(result)
        assert len(parsed["entities"]) == 3
        assert len(parsed["events"]) == 2

    def test_custom_indent(self):
        """Test custom indentation"""
        formatter = JSONFormatter(indent=4)
        data = {"key": "value"}
        result = formatter.format(data)
        # Should have 4-space indentation
        assert "    " in result

    def test_default_str_conversion(self):
        """Test default=str for non-serializable objects"""
        from datetime import datetime
        formatter = JSONFormatter()
        data = {"timestamp": datetime(2025, 10, 21, 12, 0, 0)}
        result = formatter.format(data)
        parsed = json.loads(result)
        # Should convert datetime to string
        assert "2025" in parsed["timestamp"]


class TestCSVFormatter:
    """Tests for CSV formatting"""

    def test_format_table(self):
        """Test table formatting"""
        formatter = CSVFormatter()
        data = {
            "table": {
                "headers": ["Name", "Age", "City"],
                "rows": [
                    ["Alice", 30, "NYC"],
                    ["Bob", 25, "LA"]
                ]
            }
        }
        result = formatter.format(data)
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        assert rows[0] == ["Name", "Age", "City"]
        assert rows[1] == ["Alice", "30", "NYC"]
        assert rows[2] == ["Bob", "25", "LA"]

    def test_format_dict_as_csv(self):
        """Test dictionary to CSV conversion"""
        formatter = CSVFormatter()
        data = {
            "world_id": "test_world",
            "entity_count": 10,
            "status": "complete"
        }
        result = formatter.format(data)
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        assert rows[0] == ["Key", "Value"]
        # Check that all keys are present (order may vary)
        keys = [row[0] for row in rows[1:]]
        assert "world_id" in keys
        assert "entity_count" in keys
        assert "status" in keys

    def test_format_dict_with_nested_structures(self):
        """Test dictionary with nested structures"""
        formatter = CSVFormatter()
        data = {
            "simple": "value",
            "nested": {"key": "value"},
            "list": [1, 2, 3]
        }
        result = formatter.format(data)
        # Nested structures should be JSON-encoded
        assert "simple,value" in result or "simple\r\nvalue" in result.replace(",", "\r\n")
        # CSV escapes quotes by doubling them, so check for the escaped version or unescaped
        assert '"key"' in result or "'key'" in result  # Just check key is present in some form
        assert "[1, 2, 3]" in result  # List should be JSON-encoded

    def test_format_empty_table(self):
        """Test handling of empty table"""
        formatter = CSVFormatter()
        data = {"table": {}}
        result = formatter.format(data)
        assert result == ""

    def test_format_table_with_special_chars(self):
        """Test CSV formatting with special characters"""
        formatter = CSVFormatter()
        data = {
            "table": {
                "headers": ["Name", "Description"],
                "rows": [
                    ["Alice", "Has, comma"],
                    ["Bob", 'Has "quotes"']
                ]
            }
        }
        result = formatter.format(data)
        # CSV writer should properly escape special characters
        assert "Has, comma" in result or '"Has, comma"' in result
        assert 'Has "quotes"' in result or 'Has ""quotes""' in result


class TestFormatterFactory:
    """Tests for FormatterFactory"""

    def test_create_markdown_formatter(self):
        """Test creating markdown formatter"""
        formatter = FormatterFactory.create("markdown")
        assert isinstance(formatter, MarkdownFormatter)

    def test_create_markdown_formatter_short_name(self):
        """Test creating markdown formatter with short name"""
        formatter = FormatterFactory.create("md")
        assert isinstance(formatter, MarkdownFormatter)

    def test_create_json_formatter(self):
        """Test creating JSON formatter"""
        formatter = FormatterFactory.create("json")
        assert isinstance(formatter, JSONFormatter)

    def test_create_json_formatter_with_kwargs(self):
        """Test creating JSON formatter with custom indent"""
        formatter = FormatterFactory.create("json", indent=4)
        assert formatter.indent == 4

    def test_create_csv_formatter(self):
        """Test creating CSV formatter"""
        formatter = FormatterFactory.create("csv")
        assert isinstance(formatter, CSVFormatter)

    def test_case_insensitive_format_names(self):
        """Test format names are case insensitive"""
        formatter1 = FormatterFactory.create("MARKDOWN")
        formatter2 = FormatterFactory.create("Markdown")
        formatter3 = FormatterFactory.create("markdown")
        assert isinstance(formatter1, MarkdownFormatter)
        assert isinstance(formatter2, MarkdownFormatter)
        assert isinstance(formatter3, MarkdownFormatter)

    def test_unsupported_format_raises_error(self):
        """Test unsupported format raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            FormatterFactory.create("xml")
        assert "Unsupported format: xml" in str(exc_info.value)

    def test_get_supported_formats(self):
        """Test getting list of supported formats"""
        formats = FormatterFactory.get_supported_formats()
        assert "markdown" in formats
        assert "md" in formats
        assert "json" in formats
        assert "csv" in formats
        assert len(formats) == 4
