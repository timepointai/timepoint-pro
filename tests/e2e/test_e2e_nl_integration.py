"""
E2E Integration Test: Sprint 3 NL Interface + Orchestrator

Tests the complete workflow:
1. Natural language description
2. Sprint 3 NL Interface generates config
3. Orchestrator executes simulation

This test demonstrates Sprint 3 integrated with the existing system.
"""

import os
import shutil
import tempfile

import pytest

from nl_interface import NLConfigGenerator
from orchestrator import simulate_event
from storage import GraphStore


@pytest.mark.e2e
@pytest.mark.slow
class TestNLOrchestratorIntegration:
    """E2E integration test for NL → Orchestrator pipeline"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = GraphStore(f"sqlite:///{db_path}")

    def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.mark.llm
    def test_nl_to_orchestrator_complete_pipeline(self, llm_client):
        """
        E2E: Natural Language → Config → Orchestrator → Simulation

        This is the complete Sprint 3 integration test showing:
        1. NL interface (Sprint 3) generates config from plain English
        2. Config is validated
        3. Orchestrator executes the simulation
        4. Entities and timepoints are created
        """
        print("\n" + "=" * 70)
        print("Sprint 3 Integration Test: NL → Orchestrator Pipeline")
        print("=" * 70)

        # Phase 1: Natural Language → Config (Sprint 3)
        print("\n[Phase 1] Generating config from natural language...")

        description = (
            "Simulate a board meeting with 5 executives discussing an acquisition. "
            "Focus on dialog and decision making."
        )

        # Use mock mode (no API key needed for CI/CD)
        generator = NLConfigGenerator()

        print(f'Description: "{description}"')

        config, confidence = generator.generate_config(description)

        print(f"✅ Config generated with {confidence:.1%} confidence")
        print(f"   Scenario: {config['scenario'][:50]}...")
        print(f"   Entities: {len(config['entities'])}")
        print(f"   Timepoints: {config['timepoint_count']}")
        print(f"   Temporal Mode: {config['temporal_mode']}")

        # Phase 2: Validate Config
        print("\n[Phase 2] Validating config...")

        validation = generator.validate_config(config)

        assert validation.is_valid, f"Validation failed: {validation.errors}"

        print("✅ Config validated")
        print(f"   Validation confidence: {validation.confidence_score:.1%}")

        # Phase 3: Execute with Orchestrator
        print("\n[Phase 3] Executing simulation with orchestrator...")

        result = simulate_event(
            config["scenario"],
            llm_client,
            self.storage,
            context={
                "max_entities": len(config["entities"]),
                "max_timepoints": min(config["timepoint_count"], 3),  # Limit for testing
                "temporal_mode": config.get("temporal_mode", "forward"),
            },
            save_to_db=True,
        )

        print("✅ Simulation executed")
        print(f"   Scene: {result['specification'].scene_title}")
        print(f"   Entities created: {len(result['entities'])}")
        print(f"   Timepoints created: {len(result['timepoints'])}")
        print(f"   Graph nodes: {result['graph'].number_of_nodes()}")
        print(f"   Graph edges: {result['graph'].number_of_edges()}")

        # Phase 4: Verify Results
        print("\n[Phase 4] Verifying results...")

        assert len(result["entities"]) >= 1, "Should create at least 1 entity"
        assert len(result["timepoints"]) >= 1, "Should create at least 1 timepoint"
        assert result["graph"].number_of_nodes() >= 1, "Graph should have nodes"

        print("✅ Results verified")

        # Phase 5: Summary
        print("\n" + "=" * 70)
        print("Sprint 3 Integration: SUCCESS")
        print("=" * 70)
        print("Pipeline Stages:")
        print("  1. Natural Language Input ✅")
        print("  2. Config Generation (Sprint 3) ✅")
        print("  3. Config Validation (Sprint 3) ✅")
        print("  4. Orchestrator Execution ✅")
        print("  5. Entity & Timepoint Creation ✅")
        print("=" * 70)
        print("\nSprint 3 is FULLY INTEGRATED with Timepoint-Pro! 🎉")
        print("=" * 70 + "\n")
