"""
Complete E2E Pipeline Test: All Sprints Integrated

Tests the COMPLETE Timepoint-Daedalus pipeline:
- Sprint 3: Natural Language → Config
- Orchestrator: Config → Simulation
- Sprint 1: Query Interface (query simulation data)
- Sprint 2: Reporting & Export (generate reports and export data)

This is the ultimate integration test showing all sprints working together.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path

# Sprint 3: NL Interface
from nl_interface import NLConfigGenerator

# Orchestrator
from orchestrator import simulate_event
from storage import GraphStore

# Sprint 1 & 2: Query, Reporting & Export
from reporting.query_engine import EnhancedQueryEngine
from reporting.report_generator import ReportGenerator
from reporting.export_pipeline import ExportPipeline


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteE2EPipeline:
    """Complete E2E test: Sprints 1, 2, 3 + Orchestrator"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = GraphStore(f"sqlite:///{db_path}")

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.llm
    def test_complete_pipeline_all_sprints(self, llm_client):
        """
        ULTIMATE E2E TEST: All Sprints Integrated

        Pipeline:
        1. Sprint 3: NL → Config
        2. Orchestrator: Execute simulation
        3. Sprint 1: Query simulation data
        4. Sprint 2: Generate reports and export

        This demonstrates the complete user workflow from natural language
        to exported data.
        """
        print("\n" + "="*70)
        print("COMPLETE PIPELINE TEST: All Sprints Integrated")
        print("="*70)

        # ================================================================
        # PHASE 1: Natural Language to Config (Sprint 3)
        # ================================================================
        print("\n[PHASE 1: SPRINT 3] Natural Language → Config")
        print("-" * 70)

        description = (
            "Simulate a crisis meeting with 3 astronauts making a critical decision. "
            "Focus on decision making and dialog."
        )

        # Generate config from NL
        generator = NLConfigGenerator()  # Mock mode

        print(f"Input: \"{description}\"")

        config, confidence = generator.generate_config(description)

        print(f"✅ Config generated")
        print(f"   Scenario: {config['scenario'][:60]}...")
        print(f"   Entities: {len(config['entities'])}")
        print(f"   Timepoints: {config['timepoint_count']}")
        print(f"   Confidence: {confidence:.1%}")

        # Validate
        validation = generator.validate_config(config)
        assert validation.is_valid, f"Config validation failed: {validation.errors}"

        print(f"✅ Config validated (confidence: {validation.confidence_score:.1%})")

        # ================================================================
        # PHASE 2: Execute Simulation (Orchestrator)
        # ================================================================
        print("\n[PHASE 2: ORCHESTRATOR] Execute Simulation")
        print("-" * 70)

        result = simulate_event(
            config['scenario'],
            llm_client,
            self.storage,
            context={
                "max_entities": len(config['entities']),
                "max_timepoints": min(config['timepoint_count'], 3),
                "temporal_mode": config.get('temporal_mode', 'pearl')
            },
            save_to_db=True
        )

        print(f"✅ Simulation executed")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")
        print(f"   Graph nodes: {result['graph'].number_of_nodes()}")

        # Store simulation ID for later queries
        simulation_id = result['timepoints'][0].timepoint_id if result['timepoints'] else "sim_001"

        # ================================================================
        # PHASE 3: Query Simulation Data (Sprint 1)
        # ================================================================
        print("\n[PHASE 3: SPRINT 1] Query Simulation Data")
        print("-" * 70)

        # Initialize query engine
        query_engine = EnhancedQueryEngine()

        # Store world_id for queries
        world_id = f"simulation_{simulation_id}"

        # Query 1: Relationship summarization
        print("\nQuery 1: Summarize relationships")
        relationships = query_engine.summarize_relationships(world_id)

        print(f"✅ Relationship summary generated")
        print(f"   World ID: {relationships.get('world_id')}")
        print(f"   Entity pairs: {len(relationships.get('entity_pairs', []))}")

        # Query 2: Knowledge flow graph
        print("\nQuery 2: Knowledge flow graph")
        knowledge_flow = query_engine.knowledge_flow_graph(world_id)

        print(f"✅ Knowledge flow graph generated")
        print(f"   Nodes: {len(knowledge_flow.get('nodes', []))}")
        print(f"   Edges: {len(knowledge_flow.get('edges', []))}")

        # Query 3: Timeline summary
        print("\nQuery 3: Timeline summary")
        timeline = query_engine.timeline_summary(world_id)

        print(f"✅ Timeline summary generated")
        print(f"   Events: {len(timeline.get('events', []))}")
        print(f"   Key moments: {len(timeline.get('key_moments', []))}")

        # Query 4: Execute batch queries
        print("\nQuery 4: Execute batch queries")

        batch_queries = [
            "What happened in the simulation?",
            "Who were the main entities?",
            "What was the outcome?"
        ]

        batch_results = query_engine.execute_batch(batch_queries, world_id=world_id)

        print(f"✅ Executed {len(batch_results)} batch queries")

        # Query 5: Get batch stats
        stats = query_engine.get_batch_stats()
        print(f"\nQuery Stats:")
        print(f"   Queries executed: {stats.get('queries_executed', 0)}")
        print(f"   Cache hits: {stats.get('cache_hits', 0)}")
        print(f"   Cache misses: {stats.get('cache_misses', 0)}")

        # ================================================================
        # PHASE 4: Generate Reports (Sprint 2)
        # ================================================================
        print("\n[PHASE 4: SPRINT 2] Generate Reports")
        print("-" * 70)

        # Initialize report generator with query engine
        report_generator = ReportGenerator(query_engine)

        # Report 1: Markdown summary report
        print("\nReport 1: Generating Markdown summary report...")

        md_report = report_generator.generate_summary_report(
            world_id=world_id,
            format="markdown"
        )

        print(f"✅ Markdown report generated ({len(md_report)} chars)")
        print(f"   Preview: {md_report[:100]}...")

        # Report 2: JSON relationship report
        print("\nReport 2: Generating JSON relationship report...")

        json_report = report_generator.generate_relationship_report(
            world_id=world_id,
            format="json"
        )

        print(f"✅ JSON report generated")
        print(f"   Type: {type(json_report)}")

        # Report 3: CSV knowledge report
        print("\nReport 3: Generating knowledge flow report...")

        knowledge_report = report_generator.generate_knowledge_report(
            world_id=world_id,
            format="markdown"
        )

        print(f"✅ Knowledge report generated ({len(knowledge_report)} chars)")

        # Report 4: Summary statistics
        print("\nReport 4: Summary statistics...")

        report_stats = {
            "markdown_length": len(md_report),
            "json_length": len(json_report),
            "knowledge_length": len(knowledge_report),
            "formats_generated": 3
        }

        print(f"✅ Report statistics")
        print(f"   Formats generated: {report_stats['formats_generated']}")

        # ================================================================
        # PHASE 5: Export Data (Sprint 2)
        # ================================================================
        print("\n[PHASE 5: SPRINT 2] Export Data")
        print("-" * 70)

        # Initialize export pipeline with query engine
        export_pipeline = ExportPipeline(query_engine)

        # Create output directory
        export_dir = os.path.join(self.temp_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Export 1: JSON export
        print("\nExport 1: Exporting summary report to JSON...")

        json_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="summary",
            export_format="json",
            output_path=os.path.join(export_dir, "summary")
        )

        json_path = json_result['output_path']
        assert os.path.exists(json_path), "JSON export file not created"
        json_size = json_result['file_size_bytes']

        print(f"✅ JSON export created")
        print(f"   Path: {json_path}")
        print(f"   Size: {json_size} bytes")

        # Export 2: Markdown export
        print("\nExport 2: Exporting relationships report to Markdown...")

        md_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="relationships",
            export_format="markdown",
            output_path=os.path.join(export_dir, "relationships")
        )

        md_path = md_result['output_path']
        assert os.path.exists(md_path), "Markdown export file not created"
        md_size = md_result['file_size_bytes']

        print(f"✅ Markdown export created")
        print(f"   Path: {md_path}")
        print(f"   Size: {md_size} bytes")

        # Export 3: Compressed export
        print("\nExport 3: Exporting with compression...")

        compressed_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="knowledge",
            export_format="json",
            output_path=os.path.join(export_dir, "knowledge"),
            compression="gzip"
        )

        compressed_path = compressed_result['output_path']
        assert os.path.exists(compressed_path), "Compressed export not created"
        compressed_size = compressed_result['file_size_bytes']
        compression_ratio = (1 - compressed_size / json_size) * 100 if json_size > 0 else 0

        print(f"✅ Compressed export created")
        print(f"   Path: {compressed_path}")
        print(f"   Size: {compressed_size} bytes")
        print(f"   Compression: {compression_ratio:.1f}% reduction")

        # Export 4: Fountain Script export
        print("\nExport 4: Exporting screenplay in Fountain format...")

        # Attach store to query engine for script generation
        query_engine.store = self.storage

        fountain_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="script",
            export_format="fountain",
            output_path=os.path.join(export_dir, "screenplay"),
            title=f"Simulation: {simulation_id}"
        )

        fountain_path = fountain_result['output_path']
        assert os.path.exists(fountain_path), "Fountain script export not created"
        fountain_size = fountain_result['file_size_bytes']

        print(f"✅ Fountain script export created")
        print(f"   Path: {fountain_path}")
        print(f"   Size: {fountain_size} bytes")

        # Export 5: Storyboard JSON export
        print("\nExport 5: Exporting storyboard in JSON format...")

        storyboard_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="script",
            export_format="storyboard",
            output_path=os.path.join(export_dir, "storyboard"),
            title=f"Simulation: {simulation_id}"
        )

        storyboard_path = storyboard_result['output_path']
        assert os.path.exists(storyboard_path), "Storyboard JSON export not created"
        storyboard_size = storyboard_result['file_size_bytes']

        print(f"✅ Storyboard JSON export created")
        print(f"   Path: {storyboard_path}")
        print(f"   Size: {storyboard_size} bytes")

        # Export 6: PDF screenplay export
        print("\nExport 6: Exporting screenplay in PDF format...")

        pdf_result = export_pipeline.export_report(
            world_id=world_id,
            report_type="script",
            export_format="pdf",
            output_path=os.path.join(export_dir, "screenplay"),
            title=f"Simulation: {simulation_id}"
        )

        pdf_path = pdf_result['output_path']
        assert os.path.exists(pdf_path), "PDF screenplay export not created"
        pdf_size = pdf_result['file_size_bytes']

        # Verify it's a valid PDF
        with open(pdf_path, 'rb') as f:
            pdf_header = f.read(4)
            assert pdf_header == b'%PDF', "PDF file is invalid"

        print(f"✅ PDF screenplay export created")
        print(f"   Path: {pdf_path}")
        print(f"   Size: {pdf_size} bytes")

        # ================================================================
        # PHASE 6: Verification
        # ================================================================
        print("\n[PHASE 6] Verification")
        print("-" * 70)

        # Verify all phases completed successfully
        checks = {
            "Sprint 3: Config generated": config is not None,
            "Sprint 3: Config validated": validation.is_valid,
            "Orchestrator: Simulation executed": len(result['entities']) > 0,
            "Sprint 1: Relationships queried": relationships is not None,
            "Sprint 1: Knowledge flow generated": knowledge_flow is not None,
            "Sprint 1: Timeline generated": timeline is not None,
            "Sprint 1: Batch queries executed": len(batch_results) > 0,
            "Sprint 1: Query stats tracked": stats.get('queries_executed', 0) > 0,
            "Sprint 2: Markdown report generated": len(md_report) > 0,
            "Sprint 2: JSON report generated": len(json_report) > 0,
            "Sprint 2: Knowledge report generated": len(knowledge_report) > 0,
            "Sprint 2: JSON export created": os.path.exists(json_path),
            "Sprint 2: Markdown export created": os.path.exists(md_path),
            "Sprint 2: Compressed export created": os.path.exists(compressed_path),
            "Sprint 2: Fountain script export created": os.path.exists(fountain_path),
            "Sprint 2: Storyboard JSON export created": os.path.exists(storyboard_path),
            "Sprint 2: PDF screenplay export created": os.path.exists(pdf_path),
        }

        print("\nVerification Results:")
        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
            all_passed = all_passed and passed

        assert all_passed, "Some verification checks failed"

        # ================================================================
        # FINAL SUMMARY
        # ================================================================
        print("\n" + "="*70)
        print("COMPLETE PIPELINE TEST: SUCCESS")
        print("="*70)
        print("\nPipeline Summary:")
        print(f"  1. Sprint 3 (NL Interface):     {len(config['entities'])} entities configured")
        print(f"  2. Orchestrator:                {len(result['entities'])} entities created")
        print(f"  3. Sprint 1 (Query):            {stats.get('queries_executed', 0)} queries executed")
        print(f"  4. Sprint 2 (Reports):          {report_stats['formats_generated']} report formats generated")
        print(f"  5. Sprint 2 (Export):           6 export formats created (JSON, MD, compressed, Fountain, Storyboard, PDF)")
        print("\nAll Sprints Verified:")
        print("  ✅ Sprint 1: Query Interface")
        print("  ✅ Sprint 2: Reporting & Export")
        print("  ✅ Sprint 3: Natural Language Interface")
        print("  ✅ Orchestrator: Simulation Engine")
        print("\n" + "="*70)
        print("TIMEPOINT-DAEDALUS COMPLETE INTEGRATION: SUCCESS")
        print("="*70 + "\n")


if __name__ == "__main__":
    """Run complete pipeline test"""
    import sys
    pytest_args = [__file__, "-v", "-s", "-m", "e2e"]
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)
