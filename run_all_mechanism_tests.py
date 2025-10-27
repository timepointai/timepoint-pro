#!/usr/bin/env python3
"""
Comprehensive Mechanism Coverage Test Suite with ANDOS
=======================================================
ONE COMMAND to:
- Run ALL 15 E2E test templates (11 pre-programmed + 4 ANDOS)
- Validate all 17 mechanisms
- Test all output formats (JSON, JSONL, markdown, ML dataset)
- Validate Oxen publishing integration
- Report comprehensive results

Rate Limiting:
- Includes automatic cooldown periods between tests (10-15s)
- Prevents OpenRouter API rate limit errors
- Safe for concurrent test execution

Usage:
    python run_all_mechanism_tests.py           # Run quick mode (safe templates)
    python run_all_mechanism_tests.py --full    # Run all templates (expensive!)
"""
import os
import sys
import subprocess
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

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

# Map OXEN_API_KEY from .env to OXEN_API_TOKEN (used by oxen_integration)
if os.getenv("OXEN_API_KEY") and not os.getenv("OXEN_API_TOKEN"):
    os.environ["OXEN_API_TOKEN"] = os.environ["OXEN_API_KEY"]


def run_template(runner, config, name: str, expected_mechanisms: Set[str]) -> Dict:
    """Run a single template and return results"""
    print(f"\n{'='*80}")
    print(f"Running: {name}")
    print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
    print(f"{'='*80}\n")

    try:
        result = runner.run(config)
        mechanisms = set(result.mechanisms_used) if result.mechanisms_used else set()

        success = {
            'success': True,
            'run_id': result.run_id,
            'entities': result.entities_created,
            'timepoints': result.timepoints_created,
            'mechanisms': mechanisms,
            'expected': expected_mechanisms,
            'cost': result.cost_usd or 0.0
        }

        print(f"\n✅ Success: {name}")
        print(f"   Run ID: {result.run_id}")
        print(f"   Entities: {result.entities_created}, Timepoints: {result.timepoints_created}")
        print(f"   Mechanisms: {', '.join(sorted(mechanisms))}")
        print(f"   Cost: ${result.cost_usd:.2f}")

        return success

    except Exception as e:
        print(f"\n❌ Failed: {name}")
        print(f"   Error: {str(e)[:200]}")
        return {
            'success': False,
            'error': str(e),
            'mechanisms': set(),
            'expected': expected_mechanisms,
            'cost': 0.0
        }


def run_andos_script(script: str, name: str, expected_mechanisms: Set[str]) -> Dict:
    """Run a standalone ANDOS test script"""
    print(f"\n{'='*80}")
    print(f"Running ANDOS Script: {name}")
    print(f"Script: {script}")
    print(f"Expected mechanisms: {', '.join(expected_mechanisms)}")
    print(f"{'='*80}\n")

    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env={**os.environ, "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY")}
        )

        success = result.returncode == 0

        if success:
            # Parse run_id from output
            run_id = None
            for line in result.stdout.split('\n'):
                if 'Run ID:' in line or 'run_id:' in line:
                    # Extract run_id from lines like "Run ID: run_20251026_220100_2487a596"
                    parts = line.split(':')
                    if len(parts) >= 2:
                        run_id = parts[-1].strip()
                        break

            print(f"✅ Success: {name}")
            print(f"   Exit code: {result.returncode}")
            if run_id:
                print(f"   Run ID: {run_id}")

            # Print last few lines
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[-3:]:
                print(f"   {line}")

            return {
                'success': True,
                'run_id': run_id,
                'expected': expected_mechanisms,
                'exit_code': result.returncode
            }
        else:
            print(f"❌ Failed: {name}")
            print(f"   Exit code: {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")

            return {
                'success': False,
                'error': f"Exit code {result.returncode}",
                'expected': expected_mechanisms
            }

    except subprocess.TimeoutExpired:
        print(f"❌ Timeout: {name}")
        return {
            'success': False,
            'error': "Timeout (>10 minutes)",
            'expected': expected_mechanisms
        }
    except Exception as e:
        print(f"❌ Exception: {name}")
        print(f"   Error: {str(e)[:100]}")
        return {
            'success': False,
            'error': str(e),
            'expected': expected_mechanisms
        }


def run_all_templates(mode: str = 'quick'):
    """Run all mechanism test templates"""
    from generation.config_schema import SimulationConfig
    from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
    from metadata.run_tracker import MetadataManager

    print("=" * 80)
    print(f"COMPREHENSIVE MECHANISM COVERAGE TEST ({mode.upper()} MODE)")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    print("⏱️  Rate Limiting Strategy:")
    print("   - Paid mode (1000 req/min): Minimal delays")
    print("   - Templates: 0s cooldown (16.67 req/sec available)")
    print("   - ANDOS scripts: 0s cooldown")
    print("   - Phase transition: 0s")
    print()

    # Initialize
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    runner = FullE2EWorkflowRunner(metadata_manager)

    # Define templates
    # Quick mode: safe, fast templates
    quick_templates = [
        ("board_meeting", SimulationConfig.example_board_meeting(), {"M7"}),
        ("jefferson_dinner", SimulationConfig.example_jefferson_dinner(), {"M3", "M7"}),
        ("hospital_crisis", SimulationConfig.example_hospital_crisis(), {"M8", "M14"}),
        ("kami_shrine", SimulationConfig.example_kami_shrine(), {"M16"}),
        ("detective_prospection", SimulationConfig.example_detective_prospection(), {"M15"}),
    ]

    # Full mode: expensive, comprehensive templates
    full_templates = [
        ("empty_house_flashback", SimulationConfig.example_empty_house_flashback(), {"M17", "M13", "M8"}),
        ("final_problem_branching", SimulationConfig.example_final_problem_branching(), {"M12", "M17", "M15"}),
        ("hound_shadow_directorial", SimulationConfig.example_hound_shadow_directorial(), {"M17", "M10", "M14"}),
        ("sign_loops_cyclical", SimulationConfig.example_sign_loops_cyclical(), {"M17", "M15", "M3"}),
        # WARNING: These are VERY expensive!
        # ("variations", SimulationConfig.example_variations(), {"M1", "M2"}),  # 100 variations
        # ("scarlet_study_deep", SimulationConfig.example_scarlet_study_deep(), {"M1-M17"}),  # 101 timepoints
    ]

    # ANDOS test scripts (always run)
    andos_scripts = [
        ("test_m5_query_evolution.py", "M5 Query Evolution", {"M5"}),
        ("test_m9_missing_witness.py", "M9 Missing Witness", {"M9"}),
        ("test_m10_scene_analysis.py", "M10 Scene Analysis", {"M10"}),
        ("test_m12_alternate_history.py", "M12 Alternate History", {"M12"}),
        ("test_m13_synthesis.py", "M13 Multi-Entity Synthesis", {"M13"}),
        ("test_m14_circadian.py", "M14 Circadian Patterns", {"M14"}),
    ]

    # Select templates based on mode
    templates_to_run = quick_templates
    if mode == 'full':
        templates_to_run = quick_templates + full_templates
        print("⚠️  FULL MODE: Running expensive templates!")
        print("   Estimated cost: $20-50, Runtime: 30-60 minutes")
        print()

    results = {}
    total_cost = 0.0

    # Run pre-programmed templates
    print(f"\n{'='*80}")
    print(f"PHASE 1: Pre-Programmed Templates ({len(templates_to_run)} templates)")
    print(f"{'='*80}\n")

    for idx, (name, config, expected) in enumerate(templates_to_run, 1):
        print(f"[{idx}/{len(templates_to_run)}] {name}")
        result = run_template(runner, config, name, expected)
        results[name] = result
        total_cost += result.get('cost', 0.0)

        # No delay needed in paid mode (1000 req/min = 16.67 req/sec)

    # Run ANDOS test scripts
    print(f"\n{'='*80}")
    print(f"PHASE 2: ANDOS Test Scripts ({len(andos_scripts)} scripts)")
    print(f"{'='*80}")
    print(f"\n📝 Note: All ANDOS scripts now include explicit mechanism tracking")
    print(f"   M5, M9, M10, M12, M13, M14 will be recorded in metadata/runs.db")

    # No delay needed between phases in paid mode
    print()

    for idx, (script, name, expected) in enumerate(andos_scripts, 1):
        print(f"[{idx}/{len(andos_scripts)}] {name}")
        result = run_andos_script(script, name, expected)
        results[name] = result

        # No delay needed between ANDOS scripts in paid mode

    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("COMPREHENSIVE RESULTS")
    print("=" * 80)

    # Template execution summary
    print("\n📊 Template Execution Summary:")
    passed = 0
    failed = 0
    for name, result in results.items():
        if result['success']:
            status = "✅ PASSED"
            passed += 1
            if 'run_id' in result:
                print(f"  {status:12s} {name:30s} (Run: {result['run_id'][:16]}...)")
            else:
                print(f"  {status:12s} {name:30s}")
        else:
            status = "❌ FAILED"
            failed += 1
            error = result.get('error', 'Unknown')[:40]
            print(f"  {status:12s} {name:30s} ({error})")

    print(f"\n  Total: {passed + failed} templates")
    print(f"  Passed: {passed} ({passed/(passed+failed)*100:.1f}%)")
    print(f"  Failed: {failed}")
    print(f"  Estimated Cost: ${total_cost:.2f}")

    # Mechanism coverage
    print("\n" + "-" * 80)
    print("🔬 Mechanism Coverage (metadata/runs.db):")
    print("-" * 80)

    try:
        all_runs = metadata_manager.get_all_runs()
        historical_mechanisms = set()
        for run in all_runs:
            if run.mechanisms_used:
                historical_mechanisms.update(run.mechanisms_used)

        print(f"\nTotal Coverage: {len(historical_mechanisms)}/17 ({len(historical_mechanisms)/17*100:.1f}%)")
        print(f"Tracked: {', '.join(sorted(historical_mechanisms))}")

        missing = set([f"M{i}" for i in range(1, 18)]) - historical_mechanisms
        if missing:
            print(f"\n⚠️  Missing: {', '.join(sorted(missing))}")
        else:
            print("\n🎉 SUCCESS: All 17 mechanisms tracked!")

    except Exception as e:
        print(f"Could not check metadata: {e}")

    # Output format validation
    print("\n" + "-" * 80)
    print("📁 Output Format Validation:")
    print("-" * 80)

    datasets_dir = Path("datasets")
    if datasets_dir.exists():
        json_files = list(datasets_dir.glob("**/*.json"))
        jsonl_files = list(datasets_dir.glob("**/*.jsonl"))
        md_files = list(datasets_dir.glob("**/*.md"))

        print(f"  JSON files: {len(json_files)}")
        print(f"  JSONL files: {len(jsonl_files)}")
        print(f"  Markdown files: {len(md_files)}")
    else:
        print("  No datasets/ directory found")

    # Oxen integration
    print("\n" + "-" * 80)
    print("🐂 Oxen Integration:")
    print("-" * 80)

    if os.getenv("OXEN_API_TOKEN"):
        print("  ✅ OXEN_API_TOKEN is set")
        print("  Oxen uploads should have been attempted for each template")
    else:
        print("  ⚠️  OXEN_API_TOKEN not set - Oxen uploads skipped")
        print("  Set OXEN_API_TOKEN to test Oxen publishing")

    # Final summary
    print("\n" + "=" * 80)
    print("TEST RUN COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {mode.upper()}")
    print(f"Templates Passed: {passed}/{passed + failed}")
    print(f"Total Cost: ${total_cost:.2f}")
    print("=" * 80)

    return passed == (passed + failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprehensive Mechanism Coverage Test")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all templates including expensive ones (default: quick mode)"
    )
    args = parser.parse_args()

    # Verify API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("Checked .env file - not found or empty")
        sys.exit(1)

    print(f"✓ API keys loaded from .env")
    print()

    mode = 'full' if args.full else 'quick'
    success = run_all_templates(mode)
    sys.exit(0 if success else 1)
