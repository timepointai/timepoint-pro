#!/usr/bin/env python3
"""
Vertical Multi-Timepoint Training Data Generation

This script:
1. Creates a timepoint world from Jefferson Dinner prebaked sample
2. Generates vertical (deep temporal) training data over multiple timepoints
3. Uploads the training data to Oxen.ai

Requirements:
- OPENROUTER_API_KEY environment variable
- OXEN_API_TOKEN environment variable
- LLM_SERVICE_ENABLED=true
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

# REQUIRE real LLM service
llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "true").lower() == "true"
if not llm_enabled:
    print("❌ ERROR: LLM_SERVICE_ENABLED=false")
    sys.exit(1)

if not os.getenv("OPENROUTER_API_KEY"):
    print("❌ ERROR: OPENROUTER_API_KEY not set")
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
    print("VERTICAL TRAINING DATA GENERATION")
    print("="*70)
    print()

    # Step 1: Load prebaked Jefferson Dinner sample
    print("Step 1: Loading Jefferson Dinner prebaked sample...")
    base_config = SimulationConfig.example_jefferson_dinner()
    print(f"✓ Scenario: {base_config.scenario_description}")
    print(f"✓ Base entities: {base_config.entities.count}")
    print(f"✓ Base timepoints: {base_config.timepoints.count}")
    print()

    # Step 2: Generate vertical (temporal depth) configuration
    print("Step 2: Expanding to vertical multi-timepoint simulation...")
    vertical_gen = VerticalGenerator()
    config = vertical_gen.generate_temporal_depth(
        base_config,
        before_count=4,  # Add 4 timepoints before
        after_count=4,   # Add 4 timepoints after
        strategy="progressive_training"
    )

    stats = vertical_gen.get_generation_stats()
    print(f"✓ Total timepoints: {stats['total_timepoints']}")
    print(f"✓ Timepoint window: {stats.get('timepoint_range', 'N/A')}")
    print()

    # Step 3: Initialize LLM and storage
    print("Step 3: Initializing LLM client and storage...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key, dry_run=False)

    if llm.dry_run:
        print("❌ CRITICAL: LLM in dry_run mode!")
        sys.exit(1)

    print(f"✓ LLM Client ready (dry_run={llm.dry_run})")

    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ Storage initialized: {db_path}")
    print()

    # Step 4: Run deep temporal simulation
    print("Step 4: Running deep temporal simulation...")
    print(f"   Generating {stats['total_timepoints']} timepoints...")
    print()

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

    scene_title = result['specification'].scene_title
    print(f"✅ Simulation complete!")
    print(f"   Scene: {scene_title}")
    print(f"   Entities: {len(result['entities'])}")
    print(f"   Timepoints: {len(result['timepoints'])}")
    print()

    # Step 5: Validate no mock data
    print("Step 5: Validating real LLM data...")
    if scene_title == "Test Scene":
        print("❌ FAILED: Got mock 'Test Scene'")
        sys.exit(1)

    mock_entities = [e for e in result['entities'] if "test_entity_" in e.entity_id]
    if mock_entities:
        print(f"❌ FAILED: Found {len(mock_entities)} mock entities")
        sys.exit(1)

    print("✓ No mock patterns detected - REAL data confirmed")
    print()

    # Step 6: Format training data for temporal evolution
    print("Step 6: Formatting vertical training data...")
    formatter = EntityEvolutionFormatter()
    training_examples = formatter.format_batch([result])

    print(f"✓ Generated {len(training_examples)} training examples")
    print(f"   Format: T0→T1 entity state evolution across {len(result['timepoints'])} timepoints")
    print()

    # Validate training data quality
    mock_count = 0
    for example in training_examples[:5]:
        completion = str(example.get('completion', ''))
        if 'test_entity_' in completion or '"fact1"' in completion:
            mock_count += 1

    if mock_count > 0:
        print(f"❌ FAILED: Found {mock_count} mock patterns in training data")
        sys.exit(1)

    print("✓ Training data validated (0 mock patterns)")
    print()

    # Step 7: Save locally
    print("Step 7: Saving training data...")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("datasets/vertical_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"vertical_training_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')

    file_size = output_file.stat().st_size
    print(f"✓ Saved: {output_file}")
    print(f"✓ Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    # Step 8: Upload to Oxen (proof-the-e2e-works repo)
    print("Step 8: Uploading to Oxen (proof-the-e2e-works)...")

    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
    if not oxen_token:
        print("⚠️  WARNING: No OXEN_API_TOKEN - skipping upload")
        print(f"   Local file: {output_file}")
        print()
        print("="*70)
        print("VERTICAL TRAINING DATA GENERATION COMPLETE (LOCAL ONLY)")
        print("="*70)
        return

    os.environ["OXEN_API_TOKEN"] = oxen_token

    oxen_client = OxenClient(
        namespace="realityinspector",
        repo_name="proof-the-e2e-works",
        interactive_auth=False
    )

    upload_result = oxen_client.upload_dataset(
        file_path=str(output_file),
        commit_message=f"Vertical training: {len(training_examples)} examples, {len(result['timepoints'])} timepoints, Jefferson Dinner",
        dst_path=f"datasets/vertical/{output_file.name}",
        create_repo_if_missing=True
    )

    print("✅ Upload successful!")
    print()
    print("="*70)
    print("VERTICAL TRAINING DATA GENERATION COMPLETE")
    print("="*70)
    print()
    print(f"📊 Scene: {scene_title}")
    print(f"📊 Entities: {len(result['entities'])}")
    print(f"📊 Timepoints: {len(result['timepoints'])}")
    print(f"📊 Training examples: {len(training_examples)}")
    print(f"📊 Mock patterns: 0")
    print()
    print(f"📁 Local file: {output_file}")
    print(f"🔗 Repository: {upload_result.repo_url}")
    print(f"🔗 Dataset: {upload_result.dataset_url}")
    print()
    print("📋 Next Steps to Create Fine-Tune:")
    print(f"   1. Visit: {upload_result.finetune_url}")
    print( "   2. Navigate to your dataset file")
    print( "   3. Click 'Fine-tune' button to create fine-tuning job")
    print()
    print("   Note: Oxen.ai does not support programmatic fine-tune creation.")
    print("         Fine-tunes must be created manually through the web UI.")
    print()
    print("✅ VERTICAL TRAINING DATA READY FOR FINE-TUNING")
    print()

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
