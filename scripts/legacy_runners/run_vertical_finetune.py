#!/usr/bin/env python3
"""
Vertical Fine-Tuning Data Generation

Generates deep temporal simulations with 12 timepoints for fine-tuning.
Uses progressive training strategy to create rich temporal depth.

Based on demo example: SimulationConfig.example_jefferson_dinner()

Usage:
    python run_vertical_finetune.py

Requirements:
    - OPENROUTER_API_KEY set in environment
    - OXEN_API_TOKEN set for upload
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from pathlib import Path

# Ensure environment is configured
from dotenv import load_dotenv
load_dotenv()

# REQUIRE real LLM service - no mock mode allowed
llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "true").lower() == "true"
if not llm_enabled:
    print("❌ ERROR: LLM_SERVICE_ENABLED=false")
    print("   This script requires REAL simulations, not mocks.")
    print("   Set LLM_SERVICE_ENABLED=true in your environment or .env file")
    sys.exit(1)

if not os.getenv("OPENROUTER_API_KEY"):
    print("❌ ERROR: OPENROUTER_API_KEY not set")
    print("   Set your OpenRouter API key in environment or .env file:")
    print("   export OPENROUTER_API_KEY=your_key_here")
    sys.exit(1)

from generation import VerticalGenerator
from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from oxen_integration import OxenClient
from oxen_integration.data_formatters import EntityEvolutionFormatter


def main():
    print("="*70)
    print("VERTICAL FINE-TUNING DATA GENERATION")
    print("="*70)
    print()
    print("Configuration:")
    print("  - Base scenario: Jefferson Dinner (1790 Compromise)")
    print("  - Vertical expansion: 12 timepoints total")
    print("  - Strategy: Progressive training")
    print("  - Entities: 3 (Jefferson, Hamilton, Madison)")
    print()

    # Step 1: Create vertical configuration
    print("="*70)
    print("STEP 1: Creating Vertical Configuration")
    print("="*70)

    base_config = SimulationConfig.example_jefferson_dinner()
    print(f"✓ Base scenario: {base_config.scenario_description}")

    vertical_gen = VerticalGenerator()
    config = vertical_gen.generate_temporal_depth(
        base_config,
        before_count=4,
        after_count=4,
        strategy="progressive_training"
    )

    stats = vertical_gen.get_generation_stats()
    print(f"✓ Total timepoints: {stats['total_timepoints']}")
    print(f"✓ Before count: {stats['timepoints_added_before']}")
    print(f"✓ After count: {stats['timepoints_added_after']}")
    print(f"✓ Cost savings (estimated): {stats.get('cost_savings_estimated', 0.0):.1%}")
    print()

    # Step 2: Initialize LLM and storage
    print("="*70)
    print("STEP 2: Initializing LLM and Storage")
    print("="*70)

    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key, dry_run=False)
    print(f"✓ LLM Client initialized (dry_run={llm.dry_run})")

    if llm.dry_run:
        print("❌ CRITICAL: LLM client in dry_run mode! This is test theater!")
        sys.exit(1)

    # Create temporary database for this run
    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ GraphStore initialized: {db_path}")
    print()

    # Step 3: Run deep temporal simulation
    print("="*70)
    print("STEP 3: Running Deep Temporal Simulation")
    print("="*70)
    print()
    print("🎬 Generating simulation with REAL LLM...")
    print(f"   Scenario: {config.scenario_description}")
    print(f"   Max timepoints: {stats['total_timepoints']}")
    print()

    try:
        result = simulate_event(
            config.scenario_description,
            llm,
            store,
            context={
                "max_entities": config.entities.count,
                "max_timepoints": stats['total_timepoints'],
                "temporal_mode": config.temporal.mode.value
            },
            save_to_db=True
        )

        print("✅ SIMULATION COMPLETE")
        print()
        print(f"   Scene Title: {result['specification'].scene_title}")
        print(f"   Entities: {len(result['entities'])}")
        print(f"   Timepoints: {len(result['timepoints'])}")
        print(f"   Graph Nodes: {result['graph'].number_of_nodes()}")
        print(f"   Graph Edges: {result['graph'].number_of_edges()}")
        print()

        # Validate NOT mock data
        if result['specification'].scene_title == "Test Scene":
            print("❌ CRITICAL: Got mock 'Test Scene' - test theater detected!")
            sys.exit(1)

        if any("test_entity_" in e.entity_id for e in result['entities']):
            print("❌ CRITICAL: Got test_entity_* IDs - mock data detected!")
            sys.exit(1)

        print("✓ No mock patterns detected - REAL simulation confirmed")
        print()

    except RuntimeError as e:
        if "Mock mode is disabled" in str(e) or "dry_run" in str(e):
            print(f"✅ GOOD: System correctly rejected mock mode")
            print(f"   Error: {e}")
            sys.exit(0)
        else:
            print(f"❌ Unexpected error: {e}")
            raise

    # Step 4: Format training data
    print("="*70)
    print("STEP 4: Formatting Training Data")
    print("="*70)

    formatter = EntityEvolutionFormatter()
    training_examples = formatter.format_single(result)

    print(f"✓ Generated {len(training_examples)} training examples")
    print()

    # Validate training data quality
    print("🔍 Validating training data quality...")
    mock_patterns_found = 0

    for i, example in enumerate(training_examples[:5]):
        completion = example.get('completion', '')

        if isinstance(completion, str):
            if 'test_entity_' in completion:
                print(f"   ❌ Example {i+1}: Contains test_entity_* (mock)")
                mock_patterns_found += 1
            elif '"fact1"' in completion or '"fact2"' in completion:
                print(f"   ❌ Example {i+1}: Contains generic fact1/fact2 (mock)")
                mock_patterns_found += 1
            else:
                print(f"   ✓ Example {i+1}: No mock patterns")

    if mock_patterns_found > 0:
        print(f"\n❌ CRITICAL: {mock_patterns_found} mock patterns found in training data!")
        sys.exit(1)

    print(f"\n✓ Training data quality validated (0 mock patterns)")
    print()

    # Step 5: Save training data locally
    print("="*70)
    print("STEP 5: Saving Training Data Locally")
    print("="*70)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("datasets/vertical")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"vertical_training_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')

    file_size = output_file.stat().st_size
    print(f"✓ Saved to: {output_file}")
    print(f"✓ File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"✓ Examples: {len(training_examples)}")
    print()

    # Step 6: Upload to Oxen
    print("="*70)
    print("STEP 6: Uploading to Oxen")
    print("="*70)

    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
    if not oxen_token:
        print("⚠️  WARNING: OXEN_API_TOKEN not set - skipping upload")
        print("   Set OXEN_API_TOKEN in your environment to enable upload")
        print()
        print("✅ VERTICAL FINE-TUNING DATA GENERATION COMPLETE (local only)")
        print(f"   Training data saved to: {output_file}")
        return

    # Export the current OXEN_API_KEY as OXEN_API_TOKEN for the client
    os.environ["OXEN_API_TOKEN"] = oxen_token

    oxen_client = OxenClient(
        namespace=os.getenv("OXEN_TEST_NAMESPACE", "realityinspector"),
        repo_name="timepoint_finetune_vertical",
        interactive_auth=False
    )

    upload_result = oxen_client.upload_dataset(
        file_path=str(output_file),
        commit_message=f"Vertical fine-tuning data ({len(training_examples)} examples, 12 timepoints)",
        dst_path=f"datasets/{output_file.name}",
        create_repo_if_missing=True
    )

    print(f"✓ Upload successful!")
    print(f"✓ Repository: {upload_result.repo_url}")
    print(f"✓ Dataset URL: {upload_result.dataset_url}")
    print(f"✓ Fine-tune URL: {upload_result.finetune_url}")
    print()

    # Step 7: Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()
    print(f"Scene: {result['specification'].scene_title}")
    print(f"Entities: {len(result['entities'])}")
    print(f"Timepoints: {len(result['timepoints'])}")
    print(f"Training examples: {len(training_examples)}")
    print(f"Mock patterns detected: 0")
    print(f"Local file: {output_file}")
    if upload_result:
        print(f"Oxen repository: {upload_result.repo_url}")
    print()
    print("✅ VERTICAL FINE-TUNING DATA GENERATION COMPLETE")
    print()

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
