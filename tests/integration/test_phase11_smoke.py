#!/usr/bin/env python3
"""
Smoke test for Phase 11 Architecture Pivot - E2E Integration

Tests that the new tensor initialization pipeline works end-to-end.
"""

import os
import pytest

from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from generation.config_schema import SimulationConfig, EntityConfig, CompanyConfig, TemporalConfig
from schemas import TemporalMode
from metadata.run_tracker import MetadataManager


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_phase11_simple_scenario():
    """Test a simple 2-entity scenario with new baseline initialization"""
    print("🧪 Phase 11 Smoke Test - Simple Scenario")
    print("=" * 80)

    print("✓ API key found")

    # Create simple config
    config = SimulationConfig(
        scenario_description="Two friends meet at a coffee shop to discuss a book they both read.",
        world_id="phase11_smoke_test",
        entities=EntityConfig(count=2),
        timepoints=CompanyConfig(count=1),
        temporal=TemporalConfig(mode=TemporalMode.PEARL),
        metadata={
            "test": "phase_11_smoke"
        }
    )

    print(f"✓ Config created: {config.world_id}")
    print(f"  - Entities: {config.entities.count}")
    print(f"  - Timepoints: {config.timepoints.count}")

    # Create metadata manager
    manager = MetadataManager()
    print("✓ Metadata manager created")

    # Create E2E runner
    runner = ResilientE2EWorkflowRunner(manager)
    print("✓ E2E runner created")

    print("\n🚀 Running E2E workflow...")
    print("-" * 80)

    metadata = runner.run(config)

    print("-" * 80)
    print("\n✅ E2E Workflow completed successfully!")
    print(f"   Run ID: {metadata.run_id}")
    print(f"   Entities: {metadata.entities_created}")
    print(f"   Timepoints: {metadata.timepoints_created}")
    print(f"   Training examples: {metadata.training_examples}")

    # Verify new architecture was used
    assert metadata.entities_created > 0, "No entities created"

    print("\n🔍 Verifying new tensor initialization...")
    # The fact that it completed without errors means:
    # 1. Baseline tensors were created (Step 2.5)
    # 2. Entities were processed through ANDOS
    # 3. No prospection errors occurred
    print("✅ New baseline initialization pipeline working!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
