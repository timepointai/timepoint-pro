#!/usr/bin/env python3
"""
Quick test of LLM-powered run summary generation.

Tests the full summarizer pipeline:
1. Run a small template (board_meeting)
2. Generate summary with LLM
3. Display summary
4. Verify it's stored in database
"""

import os
from pathlib import Path

# Load environment variables
def load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

from generation.config_schema import SimulationConfig
from generation.resilience_orchestrator import ResilientE2EWorkflowRunner
from generation.templates.loader import TemplateLoader
from metadata.run_tracker import MetadataManager

_loader = TemplateLoader()

def test_summary_generation():
    """Test summary generation on a small template"""

    print("=" * 80)
    print("TESTING LLM-POWERED RUN SUMMARY GENERATION")
    print("=" * 80)
    print()

    # Check API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("❌ ERROR: OPENROUTER_API_KEY not set")
        return False

    print("✓ API key loaded")
    print()

    # Initialize
    metadata_manager = MetadataManager(db_path="metadata/runs.db")
    runner = ResilientE2EWorkflowRunner(
        metadata_manager,
        generate_summary=True  # Enable summary generation
    )

    # Run small template
    print("Running small template: board_meeting")
    print("Expected: ~5 entities, 2-3 timepoints, <$1 cost")
    print()

    config = _loader.load_template("showcase/board_meeting")

    try:
        result = runner.run(config)

        print()
        print("=" * 80)
        print("RUN COMPLETE")
        print("=" * 80)
        print(f"Run ID: {result.run_id}")
        print(f"Entities: {result.entities_created}")
        print(f"Timepoints: {result.timepoints_created}")
        print(f"Cost: ${result.cost_usd:.2f}")
        print(f"Status: {result.status}")
        print()

        # Check summary
        if result.summary:
            print("=" * 80)
            print("📝 GENERATED SUMMARY")
            print("=" * 80)
            print(result.summary)
            print("=" * 80)
            print()
            print("✅ Summary generation WORKING")
            print(f"   Length: {len(result.summary)} characters")
            print(f"   Generated at: {result.summary_generated_at}")
            print()

            # Verify in database
            fetched = metadata_manager.get_run(result.run_id)
            if fetched.summary == result.summary:
                print("✅ Summary persisted correctly in database")
            else:
                print("⚠️  Summary mismatch in database")

            return True
        else:
            print("❌ No summary generated")
            print("   Check logs for errors")
            return False

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_summary_generation()
    exit(0 if success else 1)
