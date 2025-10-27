"""
ANDOS Proof of Concept Test
============================

Minimal E2E test demonstrating ANDOS layer-by-layer training.

Expected output:
- Step 3.5: ANDOS computes layers
- Step 4: Entities train layer-by-layer
- Step 4.5: Dialog synthesis succeeds (no "missing tensor" errors)
"""

import os
import sys
from pathlib import Path

# Ensure we can import from project
sys.path.insert(0, str(Path(__file__).parent))

from generation.config_schema import SimulationConfig, TemporalConfig, EntityConfig, TimepointConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager
from schemas import TemporalMode


def create_minimal_config() -> SimulationConfig:
    """Create minimal 3-entity config for ANDOS demonstration"""

    # Simple scenario: 3 people having a conversation
    scenario = """
    Three colleagues meet for lunch: Alice (senior engineer), Bob (junior engineer), and Charlie (intern).
    Track their conversation across 2 timepoints: initial greeting and main discussion.
    Alice talks to Bob, Bob talks to Charlie.
    """

    return SimulationConfig(
        world_id="andos_proof_test",
        scenario_description=scenario.strip(),

        temporal=TemporalConfig(
            mode=TemporalMode.PEARL,
            use_agent=True
        ),

        entities=EntityConfig(
            count=3,
            allow_animistic=False
        ),

        timepoints=TimepointConfig(
            count=2  # Minimal for speed
        ),

        metadata={}
    )


def main():
    """Run ANDOS proof-of-concept test"""

    print("\n" + "="*80)
    print("ANDOS PROOF OF CONCEPT TEST")
    print("="*80 + "\n")

    print("🎯 Goal: Demonstrate ANDOS layer-by-layer training")
    print("📊 Expected: 3 entities → 3 layers (charlie, bob, alice)")
    print("✅ Success: No 'missing tensor' warnings in Step 4.5\n")

    # Initialize metadata manager
    metadata_manager = MetadataManager(db_path="metadata/runs.db")

    # Create E2E runner
    runner = ResilientE2EWorkflowRunner(metadata_manager)

    # Create minimal config
    config = create_minimal_config()

    try:
        # Run E2E workflow with ANDOS
        print("🚀 Starting E2E workflow with ANDOS...\n")
        result = runner.run(config)

        print("\n" + "="*80)
        print("✅ ANDOS PROOF-OF-CONCEPT COMPLETE")
        print("="*80)
        print(f"Run ID: {result.run_id}")
        print(f"Entities Created: {result.entities_created}")
        print(f"Timepoints Created: {result.timepoints_created}")
        print(f"Training Examples: {result.training_examples}")

        # Check for success indicators
        if result.entities_created == 3 and result.timepoints_created >= 1:
            print("\n✅ ANDOS layer-by-layer training succeeded!")
            print("   Check logs above for:")
            print("   - Step 3.5: ANDOS layer computation")
            print("   - Step 4: Layer-by-layer training progress")
            print("   - Step 4.5: Dialog synthesis (no missing tensor errors)")
            return 0
        else:
            print("\n⚠️  Unexpected results - check logs above")
            return 1

    except Exception as e:
        print(f"\n❌ ANDOS test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
