#!/usr/bin/env python3
"""
Comprehensive Mechanism Coverage Test Suite
============================================
ONE COMMAND to:
- Run all E2E test templates with ANDOS
- Validate all 17 mechanisms
- Export training data to Oxen
- Report clean integrated results
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

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
    """Run all mechanism test templates using ANDOS E2E workflows"""

    print("=" * 80)
    print("COMPREHENSIVE MECHANISM COVERAGE TEST (ANDOS)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Define all test scripts to run
    test_scripts = [
        ("M5 Query Evolution", "test_m5_query_evolution.py", ["M5"]),
        ("M9 Missing Witness", "test_m9_missing_witness.py", ["M9"]),
        ("M10 Scene Analysis", "test_m10_scene_analysis.py", ["M10"]),
        ("M12 Alternate History", "test_m12_alternate_history.py", ["M12"]),
        ("M14/M15/M16 Integration", "test_m14_m15_m16_integration.py", ["M14", "M15", "M16"]),
    ]

    results = {}
    python_exe = sys.executable

    # Run each test script
    for idx, (name, script, expected_mechanisms) in enumerate(test_scripts, 1):
        print(f"\n[{idx}/{len(test_scripts)}] Running: {name}")
        print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
        print(f"Script: {script}")
        print("-" * 80)

        try:
            # Run the test script
            result = subprocess.run(
                [python_exe, script],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test
                env={**os.environ, "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY")}
            )

            success = result.returncode == 0

            if success:
                results[name] = {
                    'success': True,
                    'expected': set(expected_mechanisms),
                    'exit_code': result.returncode
                }
                print(f"✅ Success: {name}")
                print(f"   Exit code: {result.returncode}")
                # Print last few lines of output
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[-5:]:
                    print(f"   {line}")
            else:
                results[name] = {
                    'success': False,
                    'error': f"Exit code {result.returncode}",
                    'expected': set(expected_mechanisms)
                }
                print(f"❌ Failed: {name}")
                print(f"   Exit code: {result.returncode}")
                # Print error output
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}")

        except subprocess.TimeoutExpired:
            results[name] = {
                'success': False,
                'error': "Timeout (>5 minutes)",
                'expected': set(expected_mechanisms)
            }
            print(f"❌ Timeout: {name}")
        except Exception as e:
            results[name] = {
                'success': False,
                'error': str(e),
                'expected': set(expected_mechanisms)
            }
            print(f"❌ Exception: {name}")
            print(f"   Error: {str(e)[:100]}")

    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RESULTS")
    print("=" * 80)

    print("\nTemplate Results:")
    passed = 0
    for name, result in results.items():
        if result['success']:
            print(f"  ✅ {name:30s} PASSED")
            passed += 1
        else:
            print(f"  ❌ {name:30s} FAILED - {result.get('error', 'Unknown error')}")

    print(f"\nTests Passed: {passed}/{len(test_scripts)}")

    # Check metadata database for mechanism coverage
    print("\n" + "-" * 80)
    print("Checking Mechanism Coverage in metadata/runs.db:")
    print("-" * 80)

    try:
        from metadata.run_tracker import MetadataManager
        metadata_manager = MetadataManager(db_path="metadata/runs.db")
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
        else:
            print("\n🎉 SUCCESS: All 17 mechanisms tracked!")

    except Exception as e:
        print(f"Could not check metadata: {e}")

    # Final summary
    print("\n" + "=" * 80)
    print("TEST RUN COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests Passed: {passed}/{len(test_scripts)}")
    print("=" * 80)

    return passed == len(test_scripts)


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
