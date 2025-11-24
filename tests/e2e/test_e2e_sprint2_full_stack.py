"""
End-to-End Tests for Sprint 2 Full Stack (Integration)

Tests the complete Sprint 2 reporting infrastructure:
- Query Engine with batch execution and caching
- Report Generation (summary, relationships, knowledge, entity_comparison)
- Multi-format export (JSON, Markdown, CSV, JSONL, SQLite)
- Export Pipeline with compression
"""

import pytest
import json
import gzip
import sqlite3
from pathlib import Path
from reporting import (
    EnhancedQueryEngine,
    ReportGenerator,
    ExportPipeline,
    FormatterFactory,
    ExportFormatFactory
)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory"""
    output_dir = tmp_path / "sprint2_outputs"
    output_dir.mkdir()
    return output_dir


class TestQueryEngineIntegration:
    """Integration tests for Query Engine"""

    def test_batch_query_with_caching(self):
        """Test batch query execution with caching"""
        engine = EnhancedQueryEngine(enable_cache=True, cache_ttl=300)

        queries = [
            "What happened at the meeting?",
            "Who was involved?",
            "What happened at the meeting?"  # Duplicate for cache hit
        ]

        results = engine.execute_batch(queries, world_id="test_world")

        assert len(results) == 3
        assert all("query" in r for r in results)

        # Check cache stats
        stats = engine.get_batch_stats()
        assert stats["queries_executed"] == 3
        assert stats["cache_hits"] == 1  # Third query should hit cache
        assert stats["cache_misses"] == 2
        assert stats["cache_hit_rate"] > 0

    def test_aggregation_queries(self):
        """Test all aggregation query methods"""
        engine = EnhancedQueryEngine(enable_cache=False)

        # Test relationship summary
        relationships = engine.summarize_relationships("test_world")
        assert "entity_pairs" in relationships
        assert "summary_stats" in relationships

        # Test knowledge flow
        knowledge = engine.knowledge_flow_graph("test_world", timepoint_range=(0, 10))
        assert "nodes" in knowledge
        assert "edges" in knowledge
        assert "flow_metrics" in knowledge

        # Test timeline summary
        timeline = engine.timeline_summary("test_world")
        assert "events" in timeline
        assert "key_moments" in timeline
        assert "narrative_arc" in timeline

        # Test entity comparison
        comparison = engine.entity_comparison("test_world", ["alice", "bob"])
        assert "comparison_table" in comparison
        assert "similarity_scores" in comparison


class TestReportGenerationIntegration:
    """Integration tests for Report Generation"""

    def test_all_report_types_markdown(self):
        """Test generating all report types as Markdown"""
        engine = EnhancedQueryEngine(enable_cache=False)
        generator = ReportGenerator(engine)

        # Summary report
        summary = generator.generate_summary_report("test_world", format="markdown")
        assert "# Simulation Summary: test_world" in summary
        assert "## Key Moments" in summary

        # Relationship report
        relationships = generator.generate_relationship_report("test_world", format="markdown")
        assert "# Relationship Analysis: test_world" in relationships
        assert "### Entity Relationships" in relationships

        # Knowledge report
        knowledge = generator.generate_knowledge_report("test_world", format="markdown")
        assert "# Knowledge Flow Analysis: test_world" in knowledge
        assert "### Knowledge Transfer Events" in knowledge

        # Entity comparison
        comparison = generator.generate_entity_comparison_report(
            "test_world",
            entity_ids=["alice", "bob"],
            format="markdown"
        )
        assert "# Entity Comparison: test_world" in comparison
        assert "## Personality Comparison" in comparison

    def test_all_report_types_json(self):
        """Test generating all report types as JSON"""
        engine = EnhancedQueryEngine(enable_cache=False)
        generator = ReportGenerator(engine)

        report_types = [
            ("summary", {}),
            ("relationships", {}),
            ("knowledge", {}),
            ("entity_comparison", {"entity_ids": ["alice", "bob"]})
        ]

        for report_type, kwargs in report_types:
            if report_type == "summary":
                report = generator.generate_summary_report("test_world", format="json", **kwargs)
            elif report_type == "relationships":
                report = generator.generate_relationship_report("test_world", format="json", **kwargs)
            elif report_type == "knowledge":
                report = generator.generate_knowledge_report("test_world", format="json", **kwargs)
            elif report_type == "entity_comparison":
                report = generator.generate_entity_comparison_report("test_world", format="json", **kwargs)

            # Validate JSON structure
            data = json.loads(report)
            assert "title" in data
            assert "metadata" in data
            assert data["metadata"]["world_id"] == "test_world"


class TestExportPipelineIntegration:
    """Integration tests for Export Pipeline"""

    def test_complete_export_workflow(self, temp_output_dir):
        """Test complete export workflow from query to file"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        # Export summary report as JSON
        result = pipeline.export_report(
            world_id="integration_test",
            report_type="summary",
            export_format="json",
            output_path=str(temp_output_dir / "summary.json")
        )

        assert Path(result["output_path"]).exists()
        assert result["file_size_bytes"] > 0

        # Verify content
        content = Path(result["output_path"]).read_text()
        data = json.loads(content)
        assert data["title"] == "Simulation Summary: integration_test"

    def test_batch_export_workflow(self, temp_output_dir):
        """Test batch export of multiple reports"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        results = pipeline.export_batch(
            world_id="batch_test",
            report_types=["summary", "relationships", "knowledge"],
            export_formats=["json", "markdown"],
            output_dir=str(temp_output_dir)
        )

        # Should create 6 files (3 types × 2 formats)
        assert len(results) == 6
        assert all(Path(r["output_path"]).exists() for r in results)

        # Verify filenames
        filenames = [Path(r["output_path"]).name for r in results]
        assert "batch_test_summary.json" in filenames
        assert "batch_test_summary.md" in filenames
        assert "batch_test_relationships.json" in filenames
        assert "batch_test_relationships.md" in filenames
        assert "batch_test_knowledge.json" in filenames
        assert "batch_test_knowledge.md" in filenames

    def test_world_package_export(self, temp_output_dir):
        """Test exporting complete world package"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        package = pipeline.export_world_package(
            world_id="package_test",
            output_dir=str(temp_output_dir),
            formats=["json", "markdown"]
        )

        # Verify package metadata
        assert package["world_id"] == "package_test"
        assert package["report_count"] == 6  # 3 types × 2 formats
        assert len(package["files"]) == 6
        assert package["total_size_bytes"] > 0

        # Verify metadata file
        metadata_path = temp_output_dir / "package_test_package_metadata.json"
        assert metadata_path.exists()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["world_id"] == "package_test"

    def test_export_with_compression(self, temp_output_dir):
        """Test export pipeline with compression"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        # Export with gzip compression
        result = pipeline.export_report(
            world_id="compressed_test",
            report_type="summary",
            export_format="json",
            output_path=str(temp_output_dir / "summary.json"),
            compression="gzip"
        )

        assert result["compression"] == "gzip"
        assert result["output_path"].endswith(".gz")
        assert Path(result["output_path"]).exists()

        # Verify compressed content
        with gzip.open(result["output_path"], 'rt', encoding='utf-8') as f:
            data = json.load(f)
            assert data["title"] == "Simulation Summary: compressed_test"


class TestMultiFormatExport:
    """Test exporting in all supported formats"""

    def test_export_all_formats(self, temp_output_dir):
        """Test exporting in all supported formats"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        formats = ["json", "markdown"]  # Core formats
        results = []

        for fmt in formats:
            result = pipeline.export_report(
                world_id="multiformat_test",
                report_type="summary",
                export_format=fmt,
                output_path=str(temp_output_dir / f"summary.{fmt}")
            )
            results.append(result)

        assert len(results) == len(formats)
        assert all(Path(r["output_path"]).exists() for r in results)

    def test_jsonl_export(self, temp_output_dir):
        """Test JSONL export format"""
        from reporting.export_formats import JSONLExporter

        exporter = JSONLExporter()
        data = [
            {"id": 1, "event": "Meeting started"},
            {"id": 2, "event": "Proposal made"},
            {"id": 3, "event": "Vote taken"}
        ]

        output_path = temp_output_dir / "events.jsonl"
        exporter.export(data, str(output_path))

        assert output_path.exists()

        # Verify content
        lines = output_path.read_text().strip().split('\n')
        assert len(lines) == 3

        for i, line in enumerate(lines):
            parsed = json.loads(line)
            assert parsed["id"] == data[i]["id"]

    def test_sqlite_export(self, temp_output_dir):
        """Test SQLite export format"""
        from reporting.export_formats import SQLiteExporter

        exporter = SQLiteExporter()
        data = {
            "entities": [
                {"id": 1, "name": "Alice", "role": "CEO"},
                {"id": 2, "name": "Bob", "role": "CFO"}
            ],
            "events": [
                {"id": 1, "type": "meeting", "description": "Board meeting"},
                {"id": 2, "type": "decision", "description": "Approved budget"}
            ]
        }

        output_path = temp_output_dir / "simulation.db"
        exporter.export(data, str(output_path))

        assert output_path.exists()

        # Verify database
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "entities" in tables
        assert "events" in tables

        # Check data
        cursor.execute("SELECT COUNT(*) FROM entities")
        assert cursor.fetchone()[0] == 2

        cursor.execute("SELECT COUNT(*) FROM events")
        assert cursor.fetchone()[0] == 2

        conn.close()


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    def test_complete_reporting_workflow(self, temp_output_dir):
        """Test complete workflow: query → report → export"""
        # 1. Setup query engine
        engine = EnhancedQueryEngine(enable_cache=True)

        # 2. Execute batch queries
        queries = [
            "What happened?",
            "Who was involved?",
            "What was the outcome?"
        ]
        query_results = engine.execute_batch(queries, world_id="workflow_test")
        assert len(query_results) == 3

        # 3. Generate reports
        generator = ReportGenerator(engine)
        summary = generator.generate_summary_report("workflow_test", format="markdown")
        assert "# Simulation Summary: workflow_test" in summary

        # 4. Export via pipeline
        pipeline = ExportPipeline(engine)
        export_result = pipeline.export_report(
            world_id="workflow_test",
            report_type="summary",
            export_format="json",
            output_path=str(temp_output_dir / "summary.json")
        )

        assert Path(export_result["output_path"]).exists()

        # 5. Verify statistics
        query_stats = engine.get_batch_stats()
        assert query_stats["queries_executed"] == 3

        export_stats = pipeline.get_export_stats()
        assert export_stats["reports_generated"] == 1
        assert export_stats["files_exported"] == 1

    def test_large_batch_export_with_caching(self, temp_output_dir):
        """Test large batch export with caching benefits"""
        engine = EnhancedQueryEngine(enable_cache=True)
        pipeline = ExportPipeline(engine)

        # First batch export
        results1 = pipeline.export_batch(
            world_id="cache_test",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_output_dir / "batch1")
        )

        # Second batch export (should benefit from cache)
        results2 = pipeline.export_batch(
            world_id="cache_test",
            report_types=["summary", "relationships"],
            export_formats=["json"],
            output_dir=str(temp_output_dir / "batch2")
        )

        # Verify both batches created files
        batch1_dir = temp_output_dir / "batch1"
        batch2_dir = temp_output_dir / "batch2"

        assert (batch1_dir / "cache_test_summary.json").exists()
        assert (batch2_dir / "cache_test_summary.json").exists()

        # Check export stats
        export_stats = pipeline.get_export_stats()
        assert export_stats["reports_generated"] == 4  # 2 reports × 2 batches
        assert export_stats["files_exported"] == 4

    def test_mixed_format_export_package(self, temp_output_dir):
        """Test exporting package with mixed formats and compression"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        # Export package with compression
        package = pipeline.export_world_package(
            world_id="mixed_test",
            output_dir=str(temp_output_dir),
            formats=["json", "markdown"],
            compression="gzip"
        )

        # All files should be compressed
        assert all(f["compression"] == "gzip" for f in package["files"])
        assert all(f["output_path"].endswith(".gz") for f in package["files"])
        assert all(Path(f["output_path"]).exists() for f in package["files"])

        # Verify at least one compressed JSON file
        json_files = [f for f in package["files"] if ".json" in f["output_path"]]
        assert len(json_files) > 0

        # Verify we can read compressed content
        with gzip.open(json_files[0]["output_path"], 'rt', encoding='utf-8') as f:
            data = json.load(f)
            assert data["metadata"]["world_id"] == "mixed_test"


class TestErrorHandlingIntegration:
    """Test error handling across components"""

    def test_invalid_report_type_handling(self, temp_output_dir):
        """Test handling of invalid report types"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        with pytest.raises(ValueError) as exc_info:
            pipeline.export_report(
                world_id="error_test",
                report_type="invalid_type",
                export_format="json",
                output_path=str(temp_output_dir / "output.json")
            )

        assert "Unsupported report type" in str(exc_info.value)

    def test_missing_required_parameters(self, temp_output_dir):
        """Test handling of missing required parameters"""
        engine = EnhancedQueryEngine(enable_cache=False)
        pipeline = ExportPipeline(engine)

        # entity_comparison requires entity_ids
        with pytest.raises(ValueError) as exc_info:
            pipeline.export_report(
                world_id="error_test",
                report_type="entity_comparison",
                export_format="json",
                output_path=str(temp_output_dir / "output.json")
            )

        assert "entity_comparison report requires 'entity_ids'" in str(exc_info.value)
