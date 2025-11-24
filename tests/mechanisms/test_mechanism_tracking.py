#!/usr/bin/env python3
"""
Test mechanism tracking by running one template.
"""
import sys
from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager
from metadata.coverage_matrix import CoverageMatrix

# Initialize metadata manager
metadata_manager = MetadataManager()

# Initialize E2E runner
runner = ResilientE2EWorkflowRunner(metadata_manager)

# Run jefferson_dinner template
print("=" * 80)
print("Testing Mechanism Tracking: jefferson_dinner")
print("=" * 80)
print()

config = SimulationConfig.example_jefferson_dinner()
try:
    result_metadata = runner.run(config)

    # Check if mechanisms were tracked
    print()
    print("=" * 80)
    print("MECHANISM TRACKING TEST RESULTS")
    print("=" * 80)
    print(f"Run ID: {result_metadata.run_id}")
    print(f"Mechanisms Used: {result_metadata.mechanisms_used}")
    print(f"Total Mechanisms: {len(result_metadata.mechanisms_used)}/17")
    print()

    # Generate coverage matrix to see mechanism tracking
    runs = metadata_manager.get_all_runs()
    matrix_generator = CoverageMatrix()

    # Show mechanism matrix
    print("MECHANISM MATRIX:")
    print("-" * 80)
    mechanism_df = matrix_generator.generate_mechanism_matrix(runs)
    print(mechanism_df.to_string(index=False))
    print()

    # Show full matrix
    print("FULL MATRIX:")
    print("-" * 80)
    full_df = matrix_generator.generate_full_matrix(runs)
    print(full_df.to_string(index=False))

    if len(result_metadata.mechanisms_used) > 0:
        print()
        print("✅ SUCCESS: Mechanism tracking is working!")
        print(f"   Tracked mechanisms: {', '.join(sorted(result_metadata.mechanisms_used))}")
        sys.exit(0)
    else:
        print()
        print("❌ WARNING: No mechanisms were tracked")
        print("   Check if decorators are properly applied and run_id is set")
        sys.exit(1)

except Exception as e:
    print()
    print(f"❌ ERROR: Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
