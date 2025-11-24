"""
Tests for Export Pipeline (Sprint 2.3)
"""

import pytest
import json
from pathlib import Path
from reporting.export_pipeline import ExportPipeline
from reporting.query_engine import EnhancedQueryEngine


@pytest.fixture
def query_engine():
    """Create query engine for testing"""
    return EnhancedQueryEngine(enable_cache=False)


@pytest.fixture
def export_pipeline(query_engine):
    """Create export pipeline for testing"""
    return ExportPipeline(query_engine)


@pytest.fixture
def temp_export_dir(tmp_path):
    """Create temporary directory for exports"""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return export_dir


class TestSingleReportExport:
    """Tests for single report export"""

    def test_export_summary_report_json(self, export_pipeline, temp_export_dir):
        """Test exporting summary report as JSON"""
        output_path = temp_export_dir / "summary"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="json",
            output_path=str(output_path)
        )

        assert result["world_id"] == "test_world"
        assert result["report_type"] == "summary"
        assert result["export_format"] == "json"
        assert "output_path" in result
        assert Path(result["output_path"]).exists()

        # Verify content
        content = Path(result["output_path"]).read_text()
        data = json.loads(content)
        assert data["title"] == "Simulation Summary: test_world"

    def test_export_summary_report_markdown(self, export_pipeline, temp_export_dir):
        """Test exporting summary report as Markdown"""
        output_path = temp_export_dir / "summary"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="markdown",
            output_path=str(output_path)
        )

        assert Path(result["output_path"]).exists()

        # Verify content
        content = Path(result["output_path"]).read_text()
        assert "# Simulation Summary: test_world" in content

    def test_export_relationship_report(self, export_pipeline, temp_export_dir):
        """Test exporting relationship report"""
        output_path = temp_export_dir / "relationships.json"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="relationships",
            export_format="json",
            output_path=str(output_path)
        )

        content = Path(result["output_path"]).read_text()
        data = json.loads(content)
        assert data["metadata"]["report_type"] == "relationships"

    def test_export_knowledge_report(self, export_pipeline, temp_export_dir):
        """Test exporting knowledge report"""
        output_path = temp_export_dir / "knowledge.json"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="knowledge",
            export_format="json",
            output_path=str(output_path)
        )

        content = Path(result["output_path"]).read_text()
        data = json.loads(content)
        assert data["metadata"]["report_type"] == "knowledge_flow"

    def test_export_with_compression(self, export_pipeline, temp_export_dir):
        """Test exporting with gzip compression"""
        output_path = temp_export_dir / "summary.json"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="json",
            output_path=str(output_path),
            compression="gzip"
        )

        # Should create .gz file
        assert result["compression"] == "gzip"
        assert result["output_path"].endswith(".json.gz")
        assert Path(result["output_path"]).exists()

    def test_export_result_includes_metadata(self, export_pipeline, temp_export_dir):
        """Test export result includes all metadata"""
        output_path = temp_export_dir / "summary.json"

        result = export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="json",
            output_path=str(output_path)
        )

        assert "world_id" in result
        assert "report_type" in result
        assert "export_format" in result
        assert "output_path" in result
        assert "file_size_bytes" in result
        assert "exported_at" in result
        assert result["file_size_bytes"] > 0


class TestBatchReportExport:
    """Tests for batch report export"""

    def test_export_batch_multiple_types(self, export_pipeline, temp_export_dir):
        """Test exporting multiple report types"""
        results = export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_export_dir)
        )

        assert len(results) == 2
        assert all(Path(r["output_path"]).exists() for r in results)

        # Check filenames
        paths = [Path(r["output_path"]).name for r in results]
        assert "test_world_summary.json" in paths
        assert "test_world_relationships.json" in paths

    def test_export_batch_multiple_formats(self, export_pipeline, temp_export_dir):
        """Test exporting in multiple formats"""
        results = export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary"],
            export_formats=["json", "markdown"],
            output_dir=str(temp_export_dir)
        )

        assert len(results) == 2
        paths = [Path(r["output_path"]).name for r in results]
        assert "test_world_summary.json" in paths
        assert "test_world_summary.md" in paths

    def test_export_batch_creates_directory(self, export_pipeline, tmp_path):
        """Test batch export creates output directory if missing"""
        output_dir = tmp_path / "new_exports" / "nested"

        results = export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary"],
            export_formats=["json"],
            output_dir=str(output_dir)
        )

        assert output_dir.exists()
        assert len(results) == 1

    def test_export_batch_with_compression(self, export_pipeline, temp_export_dir):
        """Test batch export with compression"""
        results = export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_export_dir),
            compression="gzip"
        )

        assert all(r["compression"] == "gzip" for r in results)
        assert all(r["output_path"].endswith(".gz") for r in results)


class TestWorldPackageExport:
    """Tests for complete world package export"""

    def test_export_world_package(self, export_pipeline, temp_export_dir):
        """Test exporting complete world package"""
        package = export_pipeline.export_world_package(
            world_id="test_world",
            output_dir=str(temp_export_dir)
        )

        assert package["world_id"] == "test_world"
        assert "exported_at" in package
        assert "report_count" in package
        assert "files" in package
        assert len(package["files"]) > 0

        # Check metadata file exists
        metadata_path = temp_export_dir / "test_world_package_metadata.json"
        assert metadata_path.exists()

    def test_export_world_package_default_formats(self, export_pipeline, temp_export_dir):
        """Test world package uses default formats"""
        package = export_pipeline.export_world_package(
            world_id="test_world",
            output_dir=str(temp_export_dir)
        )

        assert "json" in package["formats"]
        assert "markdown" in package["formats"]

        # Should have multiple files (3 report types × 2 formats)
        assert package["report_count"] == 6

    def test_export_world_package_custom_formats(self, export_pipeline, temp_export_dir):
        """Test world package with custom formats"""
        package = export_pipeline.export_world_package(
            world_id="test_world",
            output_dir=str(temp_export_dir),
            formats=["json"]
        )

        assert package["formats"] == ["json"]
        # Should have 3 files (3 report types × 1 format)
        assert package["report_count"] == 3

    def test_export_world_package_with_compression(self, export_pipeline, temp_export_dir):
        """Test world package with compression"""
        package = export_pipeline.export_world_package(
            world_id="test_world",
            output_dir=str(temp_export_dir),
            compression="gzip"
        )

        assert package["compression"] == "gzip"
        assert all(f["compression"] == "gzip" for f in package["files"])

    def test_export_world_package_includes_size(self, export_pipeline, temp_export_dir):
        """Test world package includes total size"""
        package = export_pipeline.export_world_package(
            world_id="test_world",
            output_dir=str(temp_export_dir)
        )

        assert "total_size_bytes" in package
        assert package["total_size_bytes"] > 0
        assert package["total_size_bytes"] == sum(f["file_size_bytes"] for f in package["files"])


class TestExportStatistics:
    """Tests for export statistics tracking"""

    def test_export_updates_stats(self, export_pipeline, temp_export_dir):
        """Test export updates statistics"""
        export_pipeline.clear_stats()

        export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="json",
            output_path=str(temp_export_dir / "summary.json")
        )

        stats = export_pipeline.get_export_stats()
        assert stats["reports_generated"] == 1
        assert stats["files_exported"] == 1
        assert stats["total_size_bytes"] > 0

    def test_batch_export_updates_stats(self, export_pipeline, temp_export_dir):
        """Test batch export updates statistics"""
        export_pipeline.clear_stats()

        export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_export_dir)
        )

        stats = export_pipeline.get_export_stats()
        assert stats["reports_generated"] == 2
        assert stats["files_exported"] == 2

    def test_stats_include_averages(self, export_pipeline, temp_export_dir):
        """Test statistics include average file size"""
        export_pipeline.clear_stats()

        export_pipeline.export_batch(
            world_id="test_world",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_export_dir)
        )

        stats = export_pipeline.get_export_stats()
        assert "avg_file_size_bytes" in stats
        assert stats["avg_file_size_bytes"] > 0

    def test_clear_stats(self, export_pipeline, temp_export_dir):
        """Test clearing statistics"""
        export_pipeline.export_report(
            world_id="test_world",
            report_type="summary",
            export_format="json",
            output_path=str(temp_export_dir / "summary.json")
        )

        export_pipeline.clear_stats()
        stats = export_pipeline.get_export_stats()

        assert stats["reports_generated"] == 0
        assert stats["files_exported"] == 0
        assert stats["total_size_bytes"] == 0


class TestErrorHandling:
    """Tests for error handling"""

    def test_unsupported_report_type_raises_error(self, export_pipeline, temp_export_dir):
        """Test unsupported report type raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            export_pipeline.export_report(
                world_id="test_world",
                report_type="invalid_type",
                export_format="json",
                output_path=str(temp_export_dir / "output.json")
            )
        assert "Unsupported report type" in str(exc_info.value)

    def test_entity_comparison_without_entities_raises_error(self, export_pipeline, temp_export_dir):
        """Test entity_comparison without entity_ids raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            export_pipeline.export_report(
                world_id="test_world",
                report_type="entity_comparison",
                export_format="json",
                output_path=str(temp_export_dir / "output.json")
            )
        assert "entity_comparison report requires 'entity_ids'" in str(exc_info.value)
