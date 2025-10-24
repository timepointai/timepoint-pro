#!/usr/bin/env python3
"""
Test Phase 3 specialized templates for mechanism tracking.
Tests: hospital_crisis (M8, M14), kami_shrine (M16), detective_prospection (M15)
"""
import sys
from generation.config_schema import SimulationConfig
from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
from metadata.run_tracker import MetadataManager

def test_template(template_name, config):
    """Test a single template and return mechanisms tracked"""
    print("=" * 80)
    print(f"Testing: {template_name}")
    print("=" * 80)

    metadata_manager = MetadataManager()
    runner = FullE2EWorkflowRunner(metadata_manager)

    try:
        result_metadata = runner.run(config)
        mechanisms = result_metadata.mechanisms_used

        print(f"✅ Run completed")
        print(f"   Run ID: {result_metadata.run_id}")
        print(f"   Mechanisms: {', '.join(sorted(mechanisms)) if mechanisms else 'NONE'}")
        print(f"   Count: {len(mechanisms)}/17")
        print()

        return mechanisms, None
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        return set(), str(e)

def main():
    """Test all Phase 3 templates"""
    print()
    print("=" * 80)
    print("PHASE 3 TEMPLATE TESTING")
    print("Testing specialized templates for M8, M14, M15, M16")
    print("=" * 80)
    print()

    results = {}

    # Test 1: Hospital Crisis (M8, M14)
    config1 = SimulationConfig.example_hospital_crisis()
    mechanisms1, error1 = test_template("hospital_crisis (M8, M14)", config1)
    results['hospital_crisis'] = {
        'mechanisms': mechanisms1,
        'error': error1,
        'expected': {'M8', 'M14'}
    }

    # Test 2: Kami Shrine (M16)
    config2 = SimulationConfig.example_kami_shrine()
    mechanisms2, error2 = test_template("kami_shrine (M16)", config2)
    results['kami_shrine'] = {
        'mechanisms': mechanisms2,
        'error': error2,
        'expected': {'M16'}
    }

    # Test 3: Detective Prospection (M15)
    config3 = SimulationConfig.example_detective_prospection()
    mechanisms3, error3 = test_template("detective_prospection (M15)", config3)
    results['detective_prospection'] = {
        'mechanisms': mechanisms3,
        'error': error3,
        'expected': {'M15'}
    }

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    all_mechanisms = set()
    for template, result in results.items():
        all_mechanisms.update(result['mechanisms'])
        expected = result['expected']
        actual = result['mechanisms']

        if result['error']:
            status = f"❌ ERROR: {result['error'][:50]}..."
        elif expected & actual:
            status = f"✅ TRACKED: {', '.join(expected & actual)}"
        else:
            status = f"⚠️  Expected {', '.join(expected)} but tracked: {', '.join(actual) if actual else 'none'}"

        print(f"{template:30s} {status}")

    print()
    print(f"Total mechanisms from Phase 3: {len(all_mechanisms)}")
    print(f"All mechanisms tracked: {', '.join(sorted(all_mechanisms))}")
    print()

    # Check coverage
    metadata_manager = MetadataManager()
    all_runs = metadata_manager.get_all_runs()
    historical_mechanisms = set()
    for run in all_runs:
        if run.mechanisms_used:
            historical_mechanisms.update(run.mechanisms_used)

    print(f"Total historical coverage: {len(historical_mechanisms)}/17")
    print(f"Mechanisms: {', '.join(sorted(historical_mechanisms))}")

    return 0 if len(all_mechanisms) > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
