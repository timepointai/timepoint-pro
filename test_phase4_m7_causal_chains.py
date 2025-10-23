#!/usr/bin/env python3
"""
Test Phase 4: M7 (Causal Temporal Chains)
Tests multi-timepoint generation to ensure M7 tracking.
"""
import sys
from generation.config_schema import SimulationConfig
from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
from metadata.run_tracker import MetadataManager


def test_m7_board_meeting():
    """Test M7 using board_meeting template (3 timepoints)"""
    print("=" * 80)
    print("Testing M7: Causal Temporal Chains")
    print("Template: board_meeting (3 timepoints)")
    print("=" * 80)
    print()

    config = SimulationConfig.example_board_meeting()

    print(f"Configuration:")
    print(f"  - World: {config.world_id}")
    print(f"  - Entities: {config.entities.count}")
    print(f"  - Timepoints: {config.timepoints.count}")
    print(f"  - Temporal mode: {config.temporal.mode}")
    print()

    metadata_manager = MetadataManager()
    runner = FullE2EWorkflowRunner(metadata_manager)

    try:
        print("Running E2E workflow...")
        result_metadata = runner.run(config)
        mechanisms = result_metadata.mechanisms_used

        print()
        print("✅ Run completed successfully")
        print(f"   Run ID: {result_metadata.run_id}")
        print(f"   Mechanisms tracked: {', '.join(sorted(mechanisms)) if mechanisms else 'NONE'}")
        print(f"   Total: {len(mechanisms)}/17")
        print()

        if 'M7' in mechanisms:
            print("🎯 SUCCESS: M7 (Causal Temporal Chains) was tracked!")
            return True, mechanisms
        else:
            print(f"⚠️  WARNING: M7 not tracked")
            print(f"   Tracked mechanisms: {mechanisms}")
            return False, mechanisms

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, set()


def test_m7_jefferson_dinner():
    """Test M7 using jefferson_dinner template (5 timepoints with before/after)"""
    print("=" * 80)
    print("Testing M7: Causal Temporal Chains (Alternative)")
    print("Template: jefferson_dinner (5 timepoints with temporal expansion)")
    print("=" * 80)
    print()

    config = SimulationConfig.example_jefferson_dinner()

    total_timepoints = config.timepoints.count + config.timepoints.before_count + config.timepoints.after_count
    print(f"Configuration:")
    print(f"  - World: {config.world_id}")
    print(f"  - Entities: {config.entities.count}")
    print(f"  - Timepoints: {total_timepoints} (base={config.timepoints.count}, before={config.timepoints.before_count}, after={config.timepoints.after_count})")
    print(f"  - Temporal mode: {config.temporal.mode}")
    print()

    metadata_manager = MetadataManager()
    runner = FullE2EWorkflowRunner(metadata_manager)

    try:
        print("Running E2E workflow...")
        result_metadata = runner.run(config)
        mechanisms = result_metadata.mechanisms_used

        print()
        print("✅ Run completed successfully")
        print(f"   Run ID: {result_metadata.run_id}")
        print(f"   Mechanisms tracked: {', '.join(sorted(mechanisms)) if mechanisms else 'NONE'}")
        print(f"   Total: {len(mechanisms)}/17")
        print()

        if 'M7' in mechanisms:
            print("🎯 SUCCESS: M7 (Causal Temporal Chains) was tracked!")
            return True, mechanisms
        else:
            print(f"⚠️  WARNING: M7 not tracked")
            print(f"   Tracked mechanisms: {mechanisms}")
            return False, mechanisms

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, set()


def main():
    """Run all M7 tests"""
    print()
    print("=" * 80)
    print("PHASE 4: M7 CAUSAL TEMPORAL CHAINS TESTING")
    print("=" * 80)
    print()

    results = {}

    # Test 1: Board meeting (simpler, 3 timepoints)
    success1, mechanisms1 = test_m7_board_meeting()
    results['board_meeting'] = {
        'success': success1,
        'mechanisms': mechanisms1
    }

    print()
    print("-" * 80)
    print()

    # Test 2: Jefferson dinner (more complex, 5 timepoints with expansion)
    success2, mechanisms2 = test_m7_jefferson_dinner()
    results['jefferson_dinner'] = {
        'success': success2,
        'mechanisms': mechanisms2
    }

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_mechanisms = set()
    for template, result in results.items():
        all_mechanisms.update(result['mechanisms'])

        if result['success']:
            status = f"✅ M7 TRACKED"
        elif result['mechanisms']:
            status = f"⚠️  Tracked {len(result['mechanisms'])} mechanisms but M7 missing"
        else:
            status = f"❌ ERROR"

        print(f"{template:30s} {status}")

    print()
    m7_tracked = any(results[t]['success'] for t in results)
    if m7_tracked:
        print("🎉 Phase 4 SUCCESS: M7 tracked in at least one test!")
    else:
        print("⚠️  Phase 4 INCOMPLETE: M7 not tracked in any test")

    print()
    print(f"All mechanisms from Phase 4 tests: {', '.join(sorted(all_mechanisms))}")
    print(f"Total unique mechanisms: {len(all_mechanisms)}/17")

    # Check overall coverage
    print()
    print("-" * 80)
    print("Checking historical coverage...")
    print("-" * 80)

    metadata_manager = MetadataManager()
    all_runs = metadata_manager.get_all_runs()
    historical_mechanisms = set()
    for run in all_runs:
        if run.mechanisms_used:
            historical_mechanisms.update(run.mechanisms_used)

    print(f"Total historical coverage: {len(historical_mechanisms)}/17")
    print(f"Mechanisms: {', '.join(sorted(historical_mechanisms))}")

    return 0 if m7_tracked else 1


if __name__ == "__main__":
    sys.exit(main())
