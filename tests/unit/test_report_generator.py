"""
Tests for Report Generator (Sprint 2.2)
"""

import pytest
import json
from reporting.report_generator import ReportGenerator
from reporting.query_engine import EnhancedQueryEngine


@pytest.fixture
def query_engine():
    """Create query engine for testing"""
    return EnhancedQueryEngine(enable_cache=False)


@pytest.fixture
def report_generator(query_engine):
    """Create report generator for testing"""
    return ReportGenerator(query_engine)


class TestSummaryReport:
    """Tests for summary report generation"""

    def test_generate_summary_report_markdown(self, report_generator):
        """Test generating summary report in Markdown"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="markdown"
        )

        assert isinstance(report, str)
        assert "# Simulation Summary: test_world" in report
        assert "## Key Moments" in report
        assert "## Statistics" in report
        assert "## Metadata" in report

    def test_generate_summary_report_json(self, report_generator):
        """Test generating summary report in JSON"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="json"
        )

        assert isinstance(report, str)
        data = json.loads(report)
        assert data["title"] == "Simulation Summary: test_world"
        assert "metadata" in data
        assert data["metadata"]["world_id"] == "test_world"
        assert data["metadata"]["report_type"] == "summary"

    def test_generate_summary_report_without_stats(self, report_generator):
        """Test generating summary report without statistics"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="markdown",
            include_stats=False
        )

        assert "# Simulation Summary: test_world" in report
        # Statistics section should not be present
        # But other sections should be
        assert "## Key Moments" in report

    def test_summary_report_includes_timeline_table(self, report_generator):
        """Test that summary report includes timeline table"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="markdown"
        )

        assert "### Timeline Overview" in report
        assert "| Timepoint | Event Type | Description | Importance |" in report


class TestRelationshipReport:
    """Tests for relationship report generation"""

    def test_generate_relationship_report_markdown(self, report_generator):
        """Test generating relationship report in Markdown"""
        report = report_generator.generate_relationship_report(
            world_id="test_world",
            format="markdown"
        )

        assert isinstance(report, str)
        assert "# Relationship Analysis: test_world" in report
        assert "## Relationship Statistics" in report
        assert "### Entity Relationships" in report

    def test_generate_relationship_report_json(self, report_generator):
        """Test generating relationship report in JSON"""
        report = report_generator.generate_relationship_report(
            world_id="test_world",
            format="json"
        )

        data = json.loads(report)
        assert data["title"] == "Relationship Analysis: test_world"
        assert data["metadata"]["report_type"] == "relationships"

    def test_relationship_report_with_entity_filter(self, report_generator):
        """Test relationship report with entity filter"""
        report = report_generator.generate_relationship_report(
            world_id="test_world",
            entity_ids=["alice", "bob"],
            format="json"
        )

        data = json.loads(report)
        assert data["metadata"]["entity_filter"] == ["alice", "bob"]

    def test_relationship_report_includes_table(self, report_generator):
        """Test that relationship report includes entity table"""
        report = report_generator.generate_relationship_report(
            world_id="test_world",
            format="markdown"
        )

        assert "### Entity Relationships" in report
        assert "| Entity 1 | Entity 2 | Relationship Type | Strength |" in report


class TestKnowledgeReport:
    """Tests for knowledge flow report generation"""

    def test_generate_knowledge_report_markdown(self, report_generator):
        """Test generating knowledge report in Markdown"""
        report = report_generator.generate_knowledge_report(
            world_id="test_world",
            format="markdown"
        )

        assert isinstance(report, str)
        assert "# Knowledge Flow Analysis: test_world" in report
        assert "## Knowledge Flow Metrics" in report
        assert "### Knowledge Transfer Events" in report

    def test_generate_knowledge_report_json(self, report_generator):
        """Test generating knowledge report in JSON"""
        report = report_generator.generate_knowledge_report(
            world_id="test_world",
            format="json"
        )

        data = json.loads(report)
        assert data["title"] == "Knowledge Flow Analysis: test_world"
        assert data["metadata"]["report_type"] == "knowledge_flow"

    def test_knowledge_report_with_timepoint_range(self, report_generator):
        """Test knowledge report with timepoint range"""
        report = report_generator.generate_knowledge_report(
            world_id="test_world",
            timepoint_range=(0, 5),
            format="json"
        )

        data = json.loads(report)
        assert data["metadata"]["timepoint_range"] == [0, 5]

    def test_knowledge_report_includes_flow_table(self, report_generator):
        """Test that knowledge report includes flow table"""
        report = report_generator.generate_knowledge_report(
            world_id="test_world",
            format="markdown"
        )

        assert "### Knowledge Transfer Events" in report
        assert "| Source | Target | Knowledge Item | Timepoint |" in report


class TestEntityComparisonReport:
    """Tests for entity comparison report generation"""

    def test_generate_comparison_report_markdown(self, report_generator):
        """Test generating comparison report in Markdown"""
        report = report_generator.generate_entity_comparison_report(
            world_id="test_world",
            entity_ids=["alice", "bob"],
            format="markdown"
        )

        assert isinstance(report, str)
        assert "# Entity Comparison: test_world" in report
        assert "## Personality Comparison" in report
        assert "## Knowledge Comparison" in report

    def test_generate_comparison_report_json(self, report_generator):
        """Test generating comparison report in JSON"""
        report = report_generator.generate_entity_comparison_report(
            world_id="test_world",
            entity_ids=["alice", "bob"],
            format="json"
        )

        data = json.loads(report)
        assert data["title"] == "Entity Comparison: test_world"
        assert data["metadata"]["report_type"] == "entity_comparison"
        assert data["metadata"]["entities"] == ["alice", "bob"]

    def test_comparison_report_with_custom_aspects(self, report_generator):
        """Test comparison report with custom aspects"""
        report = report_generator.generate_entity_comparison_report(
            world_id="test_world",
            entity_ids=["alice", "bob"],
            aspects=["personality"],
            format="json"
        )

        data = json.loads(report)
        assert data["metadata"]["aspects"] == ["personality"]

    def test_comparison_report_includes_similarity_table(self, report_generator):
        """Test that comparison report includes similarity table"""
        report = report_generator.generate_entity_comparison_report(
            world_id="test_world",
            entity_ids=["alice", "bob"],
            format="markdown"
        )

        assert "### Entity Similarity Scores" in report
        assert "| Entity 1 | Entity 2 | Similarity |" in report


class TestReportFormatting:
    """Tests for report formatting options"""

    def test_json_report_with_custom_indent(self, report_generator):
        """Test JSON report with custom indentation"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="json",
            indent=4
        )

        # Should have 4-space indentation
        assert "    " in report

    def test_csv_format_for_relationship_report(self, report_generator):
        """Test CSV format for relationship report"""
        report = report_generator.generate_relationship_report(
            world_id="test_world",
            format="csv"
        )

        # CSV should have Key,Value format for dict-based data
        assert "Key,Value" in report or "Entity 1,Entity 2" in report

    def test_markdown_report_structure(self, report_generator):
        """Test Markdown report has proper structure"""
        report = report_generator.generate_summary_report(
            world_id="test_world",
            format="markdown"
        )

        # Check for proper heading hierarchy
        assert report.count("# ") >= 1  # Title
        assert report.count("## ") >= 2  # Sections
        assert report.count("### ") >= 1  # Tables


class TestReportMetadata:
    """Tests for report metadata"""

    def test_all_reports_include_generation_timestamp(self, report_generator):
        """Test that all reports include generation timestamp"""
        reports = [
            report_generator.generate_summary_report("test_world", format="json"),
            report_generator.generate_relationship_report("test_world", format="json"),
            report_generator.generate_knowledge_report("test_world", format="json"),
            report_generator.generate_entity_comparison_report(
                "test_world", ["alice", "bob"], format="json"
            )
        ]

        for report in reports:
            data = json.loads(report)
            assert "metadata" in data
            assert "generated_at" in data["metadata"]
            # Should be ISO format timestamp
            assert "T" in data["metadata"]["generated_at"]

    def test_all_reports_include_world_id(self, report_generator):
        """Test that all reports include world_id"""
        reports = [
            report_generator.generate_summary_report("test_world", format="json"),
            report_generator.generate_relationship_report("test_world", format="json"),
            report_generator.generate_knowledge_report("test_world", format="json"),
            report_generator.generate_entity_comparison_report(
                "test_world", ["alice", "bob"], format="json"
            )
        ]

        for report in reports:
            data = json.loads(report)
            assert data["metadata"]["world_id"] == "test_world"

    def test_all_reports_include_report_type(self, report_generator):
        """Test that all reports include report_type"""
        report_types = {
            "summary": report_generator.generate_summary_report("test_world", format="json"),
            "relationships": report_generator.generate_relationship_report("test_world", format="json"),
            "knowledge_flow": report_generator.generate_knowledge_report("test_world", format="json"),
            "entity_comparison": report_generator.generate_entity_comparison_report(
                "test_world", ["alice", "bob"], format="json"
            )
        }

        for expected_type, report in report_types.items():
            data = json.loads(report)
            assert data["metadata"]["report_type"] == expected_type
