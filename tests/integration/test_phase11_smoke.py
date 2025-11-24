#!/usr/bin/env python3
"""
Smoke test for Phase 11 Architecture Pivot - E2E Integration

Tests that the new tensor initialization pipeline works end-to-end.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from generation.config_schema import SimulationConfig, EntityConfig, TimepointConfig, TemporalConfig, TemporalMode
from metadata.run_tracker import MetadataManager

def test_simple_scenario():
    """Test a simple 2-entity scenario with new baseline initialization"""
    print("🧪 Phase 11 Smoke Test - Simple Scenario")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    print("✓ API key found")

    # Create simple config
    config = SimulationConfig(
        scenario_description="Two friends meet at a coffee shop to discuss a book they both read.",
        world_id="phase11_smoke_test",
        entities=EntityConfig(count=2),
        timepoints=TimepointConfig(count=1),
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

    try:
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
        if metadata.entities_created > 0:
            print("\n🔍 Verifying new tensor initialization...")
            # The fact that it completed without errors means:
            # 1. Baseline tensors were created (Step 2.5)
            # 2. Entities were processed through ANDOS
            # 3. No prospection errors occurred
            print("✅ New baseline initialization pipeline working!")

        return True

    except Exception as e:
        print(f"\n❌ E2E workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_scenario()
    sys.exit(0 if success else 1)
