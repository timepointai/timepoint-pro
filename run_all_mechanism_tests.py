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


def confirm_expensive_run(mode: str, min_cost: float, max_cost: float, runtime_min: int) -> bool:
    """
    Ask user to confirm expensive test runs.

    Args:
        mode: The mode name
        min_cost: Minimum estimated cost in USD
        max_cost: Maximum estimated cost in USD
        runtime_min: Estimated runtime in minutes

    Returns:
        True if user confirms, False otherwise
    """
    print("\n" + "="*80)
    print("⚠️  EXPENSIVE RUN CONFIRMATION REQUIRED")
    print("="*80)
    print(f"Mode: {mode}")
    print(f"Estimated Cost: ${min_cost:.0f}-${max_cost:.0f}")
    print(f"Estimated Runtime: {runtime_min} minutes")
    print()

    response = input("Do you want to proceed? [y/N]: ").strip().lower()

    if response in ['y', 'yes']:
        print("✓ Confirmed. Starting test run...")
        return True
    else:
        print("❌ Cancelled by user")
        return False


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
    from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
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
    runner = ResilientE2EWorkflowRunner(metadata_manager)

    # Define templates
    # Quick mode: safe, fast templates
    quick_templates = [
        ("board_meeting", SimulationConfig.example_board_meeting(), {"M7"}),
        ("jefferson_dinner", SimulationConfig.example_jefferson_dinner(), {"M3", "M7"}),
        ("hospital_crisis", SimulationConfig.example_hospital_crisis(), {"M8", "M14"}),
        ("kami_shrine", SimulationConfig.example_kami_shrine(), {"M16"}),
        ("detective_prospection", SimulationConfig.example_detective_prospection(), {"M15"}),
        ("vc_pitch_pearl", SimulationConfig.example_vc_pitch_pearl(), {"M7", "M11", "M15"}),
        ("vc_pitch_roadshow", SimulationConfig.example_vc_pitch_roadshow(), {"M3", "M7", "M10", "M13"}),
    ]

    # Full mode: expensive, comprehensive templates
    full_templates = [
        ("empty_house_flashback", SimulationConfig.example_empty_house_flashback(), {"M17", "M13", "M8"}),
        ("final_problem_branching", SimulationConfig.example_final_problem_branching(), {"M12", "M17", "M15"}),
        ("hound_shadow_directorial", SimulationConfig.example_hound_shadow_directorial(), {"M17", "M10", "M14"}),
        ("sign_loops_cyclical", SimulationConfig.example_sign_loops_cyclical(), {"M17", "M15", "M3"}),
        ("vc_pitch_branching", SimulationConfig.example_vc_pitch_branching(), {"M12", "M15", "M8", "M17"}),
        ("vc_pitch_strategies", SimulationConfig.example_vc_pitch_strategies(), {"M12", "M10", "M15", "M17"}),
        # WARNING: These are VERY expensive!
        # ("variations", SimulationConfig.example_variations(), {"M1", "M2"}),  # 100 variations
        # ("scarlet_study_deep", SimulationConfig.example_scarlet_study_deep(), {"M1-M17"}),  # 101 timepoints
    ]

    # Timepoint Corporate Formation Analysis (new category)
    timepoint_corporate_templates = [
        # Corporate formation reverse-engineering (medium cost)
        ("timepoint_ipo_reverse", SimulationConfig.timepoint_ipo_reverse_engineering(), {"M12", "M15", "M7", "M13", "M11"}),
        ("timepoint_acquisition_scenarios", SimulationConfig.timepoint_acquisition_scenarios(), {"M12", "M15", "M11", "M8", "M7", "M13"}),
        ("timepoint_cofounder_configs", SimulationConfig.timepoint_cofounder_configurations(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_equity_incentives", SimulationConfig.timepoint_equity_performance_incentives(), {"M12", "M13", "M7", "M15", "M11", "M8"}),
        ("timepoint_formation_decisions", SimulationConfig.timepoint_critical_formation_decisions(), {"M12", "M7", "M15", "M11"}),
        ("timepoint_success_vs_failure", SimulationConfig.timepoint_success_vs_failure_paths(), {"M12", "M7", "M13", "M8", "M11", "M15"}),
        # Emergent growth strategy templates (Phase 5 - new!)
        ("timepoint_launch_marketing", SimulationConfig.timepoint_launch_marketing_campaigns(), {"M3", "M10", "M14"}),
        ("timepoint_staffing_growth", SimulationConfig.timepoint_staffing_and_growth(), {"M3", "M10", "M14", "M15"}),
        # Founder personality × governance structure (expensive, comprehensive)
        ("timepoint_personality_archetypes", SimulationConfig.timepoint_founder_personality_archetypes(), {"M12", "M13", "M8", "M7", "M11"}),
        ("timepoint_charismatic_founder", SimulationConfig.timepoint_charismatic_founder_archetype(), {"M12", "M13", "M8", "M11", "M7"}),
        ("timepoint_demanding_genius", SimulationConfig.timepoint_demanding_genius_archetype(), {"M12", "M13", "M8", "M7", "M15", "M11"}),
        # AI marketplace competitive dynamics (NEW - Phase 11)
        ("timepoint_ai_pricing_war", SimulationConfig.timepoint_ai_pricing_war(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_capability_leapfrog", SimulationConfig.timepoint_ai_capability_leapfrog(), {"M12", "M9", "M10", "M13"}),
        ("timepoint_ai_business_model_evolution", SimulationConfig.timepoint_ai_business_model_evolution(), {"M12", "M7", "M13", "M15", "M8"}),
        ("timepoint_ai_regulatory_divergence", SimulationConfig.timepoint_ai_regulatory_divergence(), {"M12", "M7", "M13", "M14"}),
    ]

    # PORTAL mode templates (backward temporal reasoning)
    portal_templates = [
        ("portal_presidential_election", SimulationConfig.portal_presidential_election(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn", SimulationConfig.portal_startup_unicorn(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure", SimulationConfig.portal_academic_tenure(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure", SimulationConfig.portal_startup_failure(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # PORTAL mode with SIMULATION-BASED JUDGING (enhanced quality)
    # Quick variants: 1 forward step, no dialog (~2x cost)
    portal_templates_simjudged_quick = [
        ("portal_presidential_election_simjudged_quick", SimulationConfig.portal_presidential_election_simjudged_quick(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_quick", SimulationConfig.portal_startup_unicorn_simjudged_quick(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_quick", SimulationConfig.portal_academic_tenure_simjudged_quick(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_quick", SimulationConfig.portal_startup_failure_simjudged_quick(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # Standard variants: 2 forward steps, dialog enabled (~3x cost)
    portal_templates_simjudged = [
        ("portal_presidential_election_simjudged", SimulationConfig.portal_presidential_election_simjudged(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged", SimulationConfig.portal_startup_unicorn_simjudged(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged", SimulationConfig.portal_academic_tenure_simjudged(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged", SimulationConfig.portal_startup_failure_simjudged(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
    ]

    # Thorough variants: 3 forward steps, extra analysis (~4-5x cost)
    portal_templates_simjudged_thorough = [
        ("portal_presidential_election_simjudged_thorough", SimulationConfig.portal_presidential_election_simjudged_thorough(), {"M17", "M15", "M12", "M7", "M13"}),
        ("portal_startup_unicorn_simjudged_thorough", SimulationConfig.portal_startup_unicorn_simjudged_thorough(), {"M17", "M13", "M8", "M11", "M15", "M7"}),
        ("portal_academic_tenure_simjudged_thorough", SimulationConfig.portal_academic_tenure_simjudged_thorough(), {"M17", "M15", "M3", "M14", "M13"}),
        ("portal_startup_failure_simjudged_thorough", SimulationConfig.portal_startup_failure_simjudged_thorough(), {"M17", "M12", "M8", "M13", "M15", "M11"}),
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
    elif mode == 'portal':
        templates_to_run = portal_templates
        print("🌀 PORTAL MODE: Backward Temporal Reasoning (Standard)")
        print("   Running 4 PORTAL mode templates (M17 - Modal Temporal Causality):")
        print("   - portal_presidential_election: Tech exec → President (15 years)")
        print("   - portal_startup_unicorn: Idea → $1B+ valuation (6 years)")
        print("   - portal_academic_tenure: PhD → Tenure (10 years)")
        print("   - portal_startup_failure: Seed → Shutdown (4 years)")
        print("   Estimated cost: $5-10, Runtime: 10-15 minutes")
        print("   Each template generates multiple backward paths with coherence scoring")
        print()
    elif mode == 'portal_simjudged_quick':
        templates_to_run = portal_templates_simjudged_quick
        print("🎬 PORTAL MODE: Simulation-Judged QUICK (Enhanced Quality)")
        print("   Running 4 PORTAL templates with lightweight simulation judging:")
        print("   - 1 forward step per candidate antecedent")
        print("   - No dialog generation (faster)")
        print("   - Judge LLM: Llama 3.1 70B")
        print("   Estimated cost: $10-20 (~2x standard), Runtime: 20-30 minutes")
        print("   Quality: Good - captures basic emergent behaviors")
        print()
    elif mode == 'portal_simjudged':
        templates_to_run = portal_templates_simjudged
        print("🎬 PORTAL MODE: Simulation-Judged STANDARD (High Quality)")
        print("   Running 4 PORTAL templates with standard simulation judging:")
        print("   - 2 forward steps per candidate antecedent")
        print("   - Dialog generation enabled")
        print("   - Judge LLM: Llama 3.1 405B")
        print("   Estimated cost: $15-30 (~3x standard), Runtime: 30-45 minutes")
        print("   Quality: High - captures dialog realism and emergent patterns")
        print()
    elif mode == 'portal_simjudged_thorough':
        templates_to_run = portal_templates_simjudged_thorough
        print("🎬 PORTAL MODE: Simulation-Judged THOROUGH (Maximum Quality)")
        print("   Running 4 PORTAL templates with thorough simulation judging:")
        print("   - 3 forward steps per candidate antecedent")
        print("   - Dialog generation + extra analysis")
        print("   - Judge LLM: Llama 3.1 405B (low temperature)")
        print("   - More candidates per step for better exploration")
        print("   Estimated cost: $25-50 (~4-5x standard), Runtime: 45-60 minutes")
        print("   Quality: Maximum - research-grade path generation")
        print()
    elif mode == 'portal_all':
        templates_to_run = portal_templates + portal_templates_simjudged_quick + portal_templates_simjudged + portal_templates_simjudged_thorough
        print("🎬🌀 PORTAL MODE: ALL VARIANTS (Comprehensive)")
        print("   Running ALL 16 PORTAL templates:")
        print("   - 4 standard PORTAL templates")
        print("   - 4 simulation-judged QUICK variants")
        print("   - 4 simulation-judged STANDARD variants")
        print("   - 4 simulation-judged THOROUGH variants")
        print("   Estimated cost: $55-110, Runtime: 105-150 minutes")
        print("   Use this for comprehensive quality comparison across all approaches")
        print()
    elif mode == 'timepoint_corporate':
        templates_to_run = timepoint_corporate_templates
        print("🏢 TIMEPOINT CORPORATE ANALYSIS MODE")
        print("   Running 15 Timepoint-specific corporate templates:")
        print("   - 6 formation analysis templates (IPO, acquisition, cofounder configs, equity, decisions, success/failure)")
        print("   - 2 emergent growth templates (marketing campaigns, staffing & growth)")
        print("   - 3 personality × governance templates (archetypes, charismatic founder, demanding genius)")
        print("   - 4 AI marketplace dynamics templates (pricing war, capability leapfrog, business model evolution, regulatory divergence)")
        print("   Estimated cost: $15-30, Runtime: 30-60 minutes")
        print()

    results = {}
    total_cost = 0.0

    # Confirmation for expensive runs
    expensive_modes = {
        'full': (20, 50, 45),
        'portal_simjudged': (15, 30, 38),
        'portal_simjudged_thorough': (25, 50, 53),
        'portal_all': (55, 110, 128)
    }

    if mode in expensive_modes:
        min_cost, max_cost, runtime = expensive_modes[mode]
        if not confirm_expensive_run(mode.upper(), min_cost, max_cost, runtime):
            print("\nTest run cancelled.")
            sys.exit(0)

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
        fountain_files = list(datasets_dir.glob("**/*.fountain"))
        pdf_files = list(datasets_dir.glob("**/*.pdf"))

        print(f"  JSON files: {len(json_files)}")
        print(f"  JSONL files: {len(jsonl_files)}")
        print(f"  Markdown files: {len(md_files)}")
        print(f"  Fountain scripts: {len(fountain_files)}")
        print(f"  PDF scripts: {len(pdf_files)}")

        if fountain_files:
            print(f"  ✅ Fountain export working")
        else:
            print(f"  ⚠️  No Fountain files found")

        if pdf_files:
            print(f"  ✅ PDF export working")
        else:
            print(f"  ⚠️  No PDF files found")
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
    parser.add_argument(
        "--portal-test-only",
        action="store_true",
        help="Run ONLY PORTAL mode backward simulation tests (4 templates)"
    )
    parser.add_argument(
        "--timepoint-corporate-analysis-only",
        action="store_true",
        help="Run ONLY Timepoint corporate formation scenarios (VC pitches + formation analysis)"
    )
    parser.add_argument(
        "--portal-simjudged-quick-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged QUICK variants (1 step, ~2x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-simjudged-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged STANDARD variants (2 steps + dialog, ~3x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-simjudged-thorough-only",
        action="store_true",
        help="Run ONLY PORTAL simulation-judged THOROUGH variants (3 steps + analysis, ~4-5x cost, 4 templates)"
    )
    parser.add_argument(
        "--portal-all",
        action="store_true",
        help="Run ALL PORTAL tests (standard + all 3 simulation-judged variants = 16 templates total)"
    )
    args = parser.parse_args()

    # Verify API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("Checked .env file - not found or empty")
        sys.exit(1)

    print(f"✓ API keys loaded from .env")
    print()

    # Determine mode
    if args.portal_test_only:
        mode = 'portal'
    elif args.portal_simjudged_quick_only:
        mode = 'portal_simjudged_quick'
    elif args.portal_simjudged_only:
        mode = 'portal_simjudged'
    elif args.portal_simjudged_thorough_only:
        mode = 'portal_simjudged_thorough'
    elif args.portal_all:
        mode = 'portal_all'
    elif args.timepoint_corporate_analysis_only:
        mode = 'timepoint_corporate'
    elif args.full:
        mode = 'full'
    else:
        mode = 'quick'

    success = run_all_templates(mode)
    sys.exit(0 if success else 1)
