"""
Tests for Export Formats (Sprint 2.3)
"""

import pytest
import json
import csv
import gzip
import bz2
import sqlite3
from pathlib import Path
from reporting.export_formats import (
    JSONLExporter,
    JSONExporter,
    CSVExporter,
    SQLiteExporter,
    ExportFormatFactory
)


@pytest.fixture
def temp_export_dir(tmp_path):
    """Create temporary directory for exports"""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


@pytest.fixture
def sample_data():
    """Sample data for testing"""
    return [
        {"id": 1, "name": "Alice", "age": 30, "city": "NYC"},
        {"id": 2, "name": "Bob", "age": 25, "city": "LA"},
        {"id": 3, "name": "Charlie", "age": 35, "city": "Chicago"}
    ]


class TestJSONLExporter:
    """Tests for JSONL export format"""

    def test_export_jsonl(self, temp_export_dir, sample_data):
        """Test basic JSONL export"""
        exporter = JSONLExporter()
        output_path = temp_export_dir / "output.jsonl"

        exporter.export(sample_data, str(output_path))

        assert output_path.exists()
        lines = output_path.read_text().strip().split('\n')
        assert len(lines) == 3

        # Each line should be valid JSON
        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["id"] == sample_data[i]["id"]
            assert parsed["name"] == sample_data[i]["name"]

    def test_export_jsonl_gzip(self, temp_export_dir, sample_data):
        """Test JSONL export with gzip compression"""
        exporter = JSONLExporter(compression='gzip')
        output_path = temp_export_dir / "output.jsonl"

        exporter.export(sample_data, str(output_path))

        # Should create .gz file
        gz_path = Path(str(output_path) + '.gz')
        assert gz_path.exists()

        # Verify content
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            assert len(lines) == 3

    def test_export_jsonl_bz2(self, temp_export_dir, sample_data):
        """Test JSONL export with bz2 compression"""
        exporter = JSONLExporter(compression='bz2')
        output_path = temp_export_dir / "output.jsonl"

        exporter.export(sample_data, str(output_path))

        # Should create .bz2 file
        bz2_path = Path(str(output_path) + '.bz2')
        assert bz2_path.exists()

        # Verify content
        with bz2.open(bz2_path, 'rt', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            assert len(lines) == 3

    def test_export_jsonl_empty(self, temp_export_dir):
        """Test JSONL export with empty data"""
        exporter = JSONLExporter()
        output_path = temp_export_dir / "empty.jsonl"

        exporter.export([], str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert content == ""


class TestJSONExporter:
    """Tests for JSON export format"""

    def test_export_json(self, temp_export_dir, sample_data):
        """Test basic JSON export"""
        exporter = JSONExporter()
        output_path = temp_export_dir / "output.json"

        exporter.export(sample_data, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        parsed = json.loads(content)
        assert len(parsed) == 3
        assert parsed[0]["name"] == "Alice"

    def test_export_json_custom_indent(self, temp_export_dir, sample_data):
        """Test JSON export with custom indentation"""
        exporter = JSONExporter(indent=4)
        output_path = temp_export_dir / "output.json"

        exporter.export(sample_data, str(output_path))

        content = output_path.read_text()
        # Should have 4-space indentation
        assert "    " in content

    def test_export_json_gzip(self, temp_export_dir, sample_data):
        """Test JSON export with gzip compression"""
        exporter = JSONExporter(compression='gzip')
        output_path = temp_export_dir / "output.json"

        exporter.export(sample_data, str(output_path))

        gz_path = Path(str(output_path) + '.gz')
        assert gz_path.exists()

        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            parsed = json.load(f)
            assert len(parsed) == 3

    def test_export_json_dict(self, temp_export_dir):
        """Test JSON export with dictionary"""
        exporter = JSONExporter()
        output_path = temp_export_dir / "output.json"

        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        exporter.export(data, str(output_path))

        content = output_path.read_text()
        parsed = json.loads(content)
        assert parsed["key"] == "value"
        assert parsed["nested"]["a"] == 1


class TestCSVExporter:
    """Tests for CSV export format"""

    def test_export_csv(self, temp_export_dir, sample_data):
        """Test basic CSV export"""
        exporter = CSVExporter()
        output_path = temp_export_dir / "output.csv"

        exporter.export(sample_data, str(output_path))

        assert output_path.exists()

        # Read and verify
        with open(output_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert rows[0]["name"] == "Alice"
            assert rows[1]["name"] == "Bob"

    def test_export_csv_custom_delimiter(self, temp_export_dir, sample_data):
        """Test CSV export with custom delimiter"""
        exporter = CSVExporter(delimiter='|')
        output_path = temp_export_dir / "output.csv"

        exporter.export(sample_data, str(output_path))

        content = output_path.read_text()
        assert "|" in content

    def test_export_csv_gzip(self, temp_export_dir, sample_data):
        """Test CSV export with gzip compression"""
        exporter = CSVExporter(compression='gzip')
        output_path = temp_export_dir / "output.csv"

        exporter.export(sample_data, str(output_path))

        gz_path = Path(str(output_path) + '.gz')
        assert gz_path.exists()

        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3

    def test_export_csv_empty(self, temp_export_dir):
        """Test CSV export with empty data"""
        exporter = CSVExporter()
        output_path = temp_export_dir / "empty.csv"

        exporter.export([], str(output_path))

        assert output_path.exists()
        # Empty file
        assert output_path.stat().st_size == 0

    def test_export_csv_nested_data(self, temp_export_dir):
        """Test CSV export with nested structures"""
        exporter = CSVExporter()
        output_path = temp_export_dir / "nested.csv"

        data = [
            {"id": 1, "name": "Alice", "metadata": {"age": 30}},
            {"id": 2, "name": "Bob", "metadata": {"age": 25}}
        ]
        exporter.export(data, str(output_path))

        with open(output_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            # Nested dict should be JSON-encoded
            metadata = json.loads(rows[0]["metadata"])
            assert metadata["age"] == 30


class TestSQLiteExporter:
    """Tests for SQLite export format"""

    def test_export_sqlite(self, temp_export_dir, sample_data):
        """Test basic SQLite export"""
        exporter = SQLiteExporter()
        output_path = temp_export_dir / "output.db"

        data = {"people": sample_data}
        exporter.export(data, str(output_path))

        assert output_path.exists()

        # Verify database
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "people" in tables

        cursor.execute("SELECT * FROM people")
        rows = cursor.fetchall()
        assert len(rows) == 3

        conn.close()

    def test_export_sqlite_multiple_tables(self, temp_export_dir, sample_data):
        """Test SQLite export with multiple tables"""
        exporter = SQLiteExporter()
        output_path = temp_export_dir / "output.db"

        data = {
            "people": sample_data,
            "cities": [
                {"id": 1, "name": "NYC", "population": 8000000},
                {"id": 2, "name": "LA", "population": 4000000}
            ]
        }
        exporter.export(data, str(output_path))

        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        # Verify both tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "people" in tables
        assert "cities" in tables

        # Verify data
        cursor.execute("SELECT COUNT(*) FROM people")
        assert cursor.fetchone()[0] == 3

        cursor.execute("SELECT COUNT(*) FROM cities")
        assert cursor.fetchone()[0] == 2

        conn.close()

    def test_export_sqlite_overwrite(self, temp_export_dir, sample_data):
        """Test SQLite export with overwrite"""
        exporter = SQLiteExporter()
        output_path = temp_export_dir / "output.db"

        # First export
        data = {"people": sample_data}
        exporter.export(data, str(output_path))

        # Try to export again without overwrite - should fail
        with pytest.raises(FileExistsError):
            exporter.export(data, str(output_path), overwrite=False)

        # Export with overwrite - should succeed
        exporter.export(data, str(output_path), overwrite=True)
        assert output_path.exists()

    def test_export_sqlite_empty_tables(self, temp_export_dir):
        """Test SQLite export with empty tables"""
        exporter = SQLiteExporter()
        output_path = temp_export_dir / "output.db"

        data = {"people": [], "cities": [{"id": 1, "name": "NYC"}]}
        exporter.export(data, str(output_path))

        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        # Empty table shouldn't be created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "people" not in tables
        assert "cities" in tables

        conn.close()

    def test_export_sqlite_nested_data(self, temp_export_dir):
        """Test SQLite export with nested structures"""
        exporter = SQLiteExporter()
        output_path = temp_export_dir / "output.db"

        data = {
            "entities": [
                {"id": 1, "name": "Alice", "metadata": {"age": 30, "city": "NYC"}},
                {"id": 2, "name": "Bob", "metadata": {"age": 25, "city": "LA"}}
            ]
        }
        exporter.export(data, str(output_path))

        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        cursor.execute("SELECT metadata FROM entities WHERE id=1")
        metadata_json = cursor.fetchone()[0]
        metadata = json.loads(metadata_json)
        assert metadata["age"] == 30

        conn.close()


class TestExportFormatFactory:
    """Tests for ExportFormatFactory"""

    def test_create_jsonl_exporter(self):
        """Test creating JSONL exporter"""
        exporter = ExportFormatFactory.create("jsonl")
        assert isinstance(exporter, JSONLExporter)

    def test_create_json_exporter(self):
        """Test creating JSON exporter"""
        exporter = ExportFormatFactory.create("json")
        assert isinstance(exporter, JSONExporter)

    def test_create_csv_exporter(self):
        """Test creating CSV exporter"""
        exporter = ExportFormatFactory.create("csv")
        assert isinstance(exporter, CSVExporter)

    def test_create_sqlite_exporter(self):
        """Test creating SQLite exporter"""
        exporter = ExportFormatFactory.create("sqlite")
        assert isinstance(exporter, SQLiteExporter)

    def test_create_sqlite_exporter_alias(self):
        """Test creating SQLite exporter with 'db' alias"""
        exporter = ExportFormatFactory.create("db")
        assert isinstance(exporter, SQLiteExporter)

    def test_create_with_compression(self):
        """Test creating exporter with compression"""
        exporter = ExportFormatFactory.create("jsonl", compression="gzip")
        assert exporter.compression == "gzip"

    def test_create_json_with_indent(self):
        """Test creating JSON exporter with custom indent"""
        exporter = ExportFormatFactory.create("json", indent=4)
        assert exporter.indent == 4

    def test_case_insensitive_formats(self):
        """Test format names are case insensitive"""
        exporter1 = ExportFormatFactory.create("JSONL")
        exporter2 = ExportFormatFactory.create("Jsonl")
        assert isinstance(exporter1, JSONLExporter)
        assert isinstance(exporter2, JSONLExporter)

    def test_unsupported_format_raises_error(self):
        """Test unsupported format raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            ExportFormatFactory.create("xml")
        assert "Unsupported format: xml" in str(exc_info.value)

    def test_get_supported_formats(self):
        """Test getting list of supported formats"""
        formats = ExportFormatFactory.get_supported_formats()
        assert "jsonl" in formats
        assert "json" in formats
        assert "csv" in formats
        assert "sqlite" in formats
        assert "db" in formats
