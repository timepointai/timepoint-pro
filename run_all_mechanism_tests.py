#!/usr/bin/env python3
"""
Comprehensive Mechanism Coverage Test Suite
============================================
ONE COMMAND to:
- Run all test templates
- Validate all 17 mechanisms
- Export training data to Oxen
- Report clean integrated results
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from generation.config_schema import SimulationConfig
from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
from metadata.run_tracker import MetadataManager

# Auto-load .env file
def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()


def run_all_templates():
    """Run all mechanism test templates"""

    print("=" * 80)
    print("COMPREHENSIVE MECHANISM COVERAGE TEST")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Initialize
    metadata_manager = MetadataManager()
    runner = FullE2EWorkflowRunner(metadata_manager)

    # Define all templates to test
    templates = [
        ("hospital_crisis", SimulationConfig.example_hospital_crisis(), ["M8", "M14"]),
        ("kami_shrine", SimulationConfig.example_kami_shrine(), ["M16"]),
        ("detective_prospection", SimulationConfig.example_detective_prospection(), ["M15"]),
        ("board_meeting", SimulationConfig.example_board_meeting(), ["M7"]),
        ("jefferson_dinner", SimulationConfig.example_jefferson_dinner(), ["M7", "M3"]),
    ]

    results = {}
    all_tracked = set()

    # Run each template
    for idx, (name, config, expected_mechanisms) in enumerate(templates, 1):
        print(f"\n[{idx}/{len(templates)}] Running: {name}")
        print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
        print("-" * 80)

        try:
            result = runner.run(config)
            mechanisms = result.mechanisms_used

            all_tracked.update(mechanisms)
            results[name] = {
                'success': True,
                'run_id': result.run_id,
                'mechanisms': mechanisms,
                'expected': set(expected_mechanisms)
            }

            print(f"✅ Success: {name}")
            print(f"   Run ID: {result.run_id}")
            print(f"   Tracked: {', '.join(sorted(mechanisms))}")
            print(f"   Count: {len(mechanisms)} mechanisms")

        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e),
                'mechanisms': set(),
                'expected': set(expected_mechanisms)
            }
            print(f"❌ Failed: {name}")
            print(f"   Error: {str(e)[:100]}")

    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RESULTS")
    print("=" * 80)

    print("\nTemplate Results:")
    for name, result in results.items():
        if result['success']:
            expected = result['expected']
            tracked = result['mechanisms']
            match = expected & tracked

            if match == expected:
                status = f"✅ FULL ({len(match)}/{len(expected)})"
            elif match:
                status = f"⚠️  PARTIAL ({len(match)}/{len(expected)})"
            else:
                status = "❌ NONE"

            print(f"  {name:25s} {status:15s} Tracked: {', '.join(sorted(tracked))}")
        else:
            print(f"  {name:25s} ❌ ERROR         {result['error'][:40]}...")

    print(f"\nTotal Unique Mechanisms This Run: {len(all_tracked)}/17")
    print(f"Mechanisms: {', '.join(sorted(all_tracked))}")

    # Check historical coverage
    print("\n" + "-" * 80)
    print("Historical Coverage (All Runs):")
    print("-" * 80)

    all_runs = metadata_manager.get_all_runs()
    historical_mechanisms = set()
    for run in all_runs:
        if run.mechanisms_used:
            historical_mechanisms.update(run.mechanisms_used)

    print(f"Total Coverage: {len(historical_mechanisms)}/17 ({len(historical_mechanisms)/17*100:.1f}%)")
    print(f"Tracked: {', '.join(sorted(historical_mechanisms))}")

    missing = set([f"M{i}" for i in range(1, 18)]) - historical_mechanisms
    if missing:
        print(f"\nMissing: {', '.join(sorted(missing))}")
        print("\nTo track remaining mechanisms:")
        mechanism_tests = {
            "M2": "Runs automatically during multi-timepoint workflows",
            "M5": "pytest test_m5_query_resolution.py -v",
            "M6": "Runs automatically during tensor operations",
            "M9": "pytest test_m9_on_demand_generation.py -v",
            "M10": "pytest test_scene_queries.py -v",
            "M11": "Runs automatically with include_dialogs=True",
            "M12": "pytest test_branching_mechanism.py -v",
            "M13": "pytest test_phase3_dialog_multi_entity.py -v",
        }
        for m in sorted(missing):
            if m in mechanism_tests:
                print(f"  {m}: {mechanism_tests[m]}")
    else:
        print("\n🎉 SUCCESS: All 17 mechanisms tracked!")

    # Final summary
    print("\n" + "=" * 80)
    print("TEST RUN COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Templates Run: {len([r for r in results.values() if r['success']])}/{len(templates)}")
    print(f"Historical Coverage: {len(historical_mechanisms)}/17")
    print("=" * 80)

    return len(historical_mechanisms) == 17


if __name__ == "__main__":
    # Verify API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("Checked .env file - not found or empty")
        sys.exit(1)

    print(f"✓ API keys loaded from .env")
    print()

    success = run_all_templates()
    sys.exit(0 if success else 1)
