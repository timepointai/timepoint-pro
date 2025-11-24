#!/usr/bin/env python3
"""
Constitutional Convention Day 1 - Large-Scale Simulation Runner

This script runs the massive 500-timepoint simulation of the Constitutional
Convention's opening day (May 25, 1787). This is a stress test of Timepoint AI
demonstrating all 16 active mechanisms and generating vast training data.

Specifications:
- 28 entities (25 Founding Fathers + 3 animistic entities)
- 500 timepoints (minute-level resolution across 8 hours)
- 16/17 mechanisms exercised (M12 not used - single timeline)
- Estimated cost: $500-1,000 USD
- Estimated runtime: 2-4 hours
- Training data: 14,000+ entity-timepoint states

Usage:
    python run_constitutional_convention.py

Or via bash wrapper:
    bash large-test-phase-1.sh

Requirements:
- OPENROUTER_API_KEY must be set (paid account recommended for rate limits)
- Minimum 2-4 hours of runtime
- Stable internet connection
- ~500MB disk space for outputs
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Ensure we can import from project
sys.path.insert(0, str(Path(__file__).parent))

from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from metadata.run_tracker import MetadataManager


def print_banner():
    """Print welcome banner"""
    print("\n" + "="*80)
    print("CONSTITUTIONAL CONVENTION DAY 1 - LARGE-SCALE SIMULATION")
    print("="*80)
    print()
    print("Historical Event: May 25, 1787")
    print("Location: Independence Hall, Philadelphia")
    print("Duration: 8 hours (10:00 AM - 6:00 PM)")
    print()
    print("Simulation Specifications:")
    print("  - 28 entities (25 Founding Fathers + 3 animistic)")
    print("  - 500 timepoints (minute-level resolution)")
    print("  - 16/17 mechanisms exercised")
    print("  - Estimated cost: $500-1,000 USD")
    print("  - Estimated runtime: 2-4 hours")
    print("  - Training data: 14,000+ entity-timepoint states")
    print()
    print("="*80)
    print()


def validate_environment():
    """Validate environment prerequisites"""
    print("Step 1: Validating environment...")

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        print("   Please set your API key:")
        print("   export OPENROUTER_API_KEY=your_key_here")
        sys.exit(1)

    print(f"  ✓ OPENROUTER_API_KEY is set ({api_key[:20]}...)")

    # Check metadata database
    metadata_path = Path("metadata/runs.db")
    if not metadata_path.parent.exists():
        print(f"  Creating metadata directory: {metadata_path.parent}")
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  ✓ Metadata database: {metadata_path}")

    # Check output directory
    output_path = Path("datasets/constitutional_convention_day1")
    if not output_path.exists():
        print(f"  Creating output directory: {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)

    print(f"  ✓ Output directory: {output_path}")
    print()


def print_cost_warning():
    """Print cost warning and confirmation"""
    print("⚠️  COST WARNING:")
    print("   This simulation will make ~500 LLM API calls")
    print("   Estimated cost: $500-1,000 USD")
    print("   Estimated runtime: 2-4 hours")
    print()
    print("   You acknowledged the scale of this simulation.")
    print("   The simulation will now proceed automatically.")
    print()


def main():
    """Run Constitutional Convention Day 1 simulation"""

    # Print welcome banner
    print_banner()

    # Validate environment
    validate_environment()

    # Print cost warning
    print_cost_warning()

    # Initialize metadata manager
    print("Step 2: Initializing metadata tracking...")
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    print("  ✓ Metadata manager initialized")
    print()

    # Create Resilient E2E runner (with fault tolerance)
    print("Step 3: Creating resilient E2E workflow runner...")
    runner = ResilientE2EWorkflowRunner(metadata_manager)
    print("  ✓ Resilient E2E runner created (fault tolerance enabled)")
    print()

    # Load Constitutional Convention config
    print("Step 4: Loading Constitutional Convention Day 1 configuration...")
    config = SimulationConfig.example_constitutional_convention_day1()
    print(f"  ✓ Config loaded: {config.world_id}")
    print(f"  ✓ Entities: {config.entities.count}")
    print(f"  ✓ Timepoints: {config.timepoints.count}")
    print(f"  ✓ Resolution: {config.timepoints.resolution}")
    print(f"  ✓ Temporal mode: {config.temporal.mode}")
    print(f"  ✓ Cost limit: ${config.max_cost_usd}")
    print()

    # Run simulation
    print("Step 5: Running simulation...")
    print("  This will take 2-4 hours. Progress will be displayed below.")
    print("  Feel free to monitor in a separate terminal:")
    print("  tail -f logs/llm_calls/llm_calls_*.jsonl")
    print()

    start_time = datetime.now()

    try:
        result = runner.run(config)

        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "="*80)
        print("✅ SIMULATION COMPLETE!")
        print("="*80)
        print()
        print("Results:")
        print(f"  Run ID: {result.run_id}")
        print(f"  Entities Created: {result.entities_created}")
        print(f"  Timepoints Created: {result.timepoints_created}")
        print(f"  Training Examples: {result.training_examples}")
        print(f"  Cost: ${result.cost_usd:.2f}")
        print(f"  LLM Calls: {result.llm_calls}")
        print(f"  Tokens Used: {result.tokens_used:,}")
        print(f"  Duration: {duration}")
        print()

        if result.mechanisms_used:
            print(f"Mechanisms Exercised: {len(result.mechanisms_used)}")
            print(f"  {', '.join(sorted(result.mechanisms_used))}")
            print()

        if result.oxen_repo_url:
            print("Oxen Export:")
            print(f"  Repo: {result.oxen_repo_url}")
            if result.oxen_dataset_url:
                print(f"  Dataset: {result.oxen_dataset_url}")
            print()

        print("Output Files:")
        output_dir = Path("datasets") / config.world_id
        if output_dir.exists():
            files = list(output_dir.glob("**/*"))
            for f in files[:10]:  # Show first 10 files
                print(f"  {f}")
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more files")
        print()

        print("Metadata:")
        print(f"  Database: metadata/runs.db")
        print(f"  Query with: sqlite3 metadata/runs.db 'SELECT * FROM runs WHERE run_id=\"{result.run_id}\"'")
        print()

        print("="*80)
        print("Constitutional Convention Day 1 simulation completed successfully!")
        print("The founding fathers live on in your training data. 🇺🇸")
        print("="*80)
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user (Ctrl+C)")
        print("   Checkpoints may have been saved. Check metadata/runs.db for status.")
        return 1

    except Exception as e:
        end_time = datetime.now()
        duration = end_time - start_time

        print("\n" + "="*80)
        print("❌ SIMULATION FAILED")
        print("="*80)
        print()
        print(f"Error: {e}")
        print(f"Duration before failure: {duration}")
        print()
        print("Troubleshooting:")
        print("  1. Check your OPENROUTER_API_KEY is valid")
        print("  2. Ensure you have sufficient API credits")
        print("  3. Check network connection")
        print("  4. Review logs: logs/llm_calls/llm_calls_*.jsonl")
        print("  5. Check metadata: sqlite3 metadata/runs.db 'SELECT * FROM runs ORDER BY start_time DESC LIMIT 1'")
        print()

        import traceback
        print("Full traceback:")
        traceback.print_exc()
        print()

        return 1


if __name__ == "__main__":
    exit(main())
