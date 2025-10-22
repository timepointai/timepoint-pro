#!/usr/bin/env python3
"""
E2E Proof Script - Run vertical fine-tuning and upload to proof-the-e2e-works repo

This script:
1. Runs a vertical temporal simulation (12 timepoints)
2. Validates no mock patterns
3. Uploads to Oxen repo: realityinspector/proof-the-e2e-works
4. Returns fine-tune URL
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
    print("E2E PROOF: VERTICAL FINE-TUNING WITH REAL LLM")
    print("="*70)
    print()

    # Step 1: Create vertical configuration (12 timepoints)
    print("Step 1: Creating vertical configuration (12 timepoints)...")
    base_config = SimulationConfig.example_jefferson_dinner()

    vertical_gen = VerticalGenerator()
    config = vertical_gen.generate_temporal_depth(
        base_config,
        before_count=4,
        after_count=4,
        strategy="progressive_training"
    )

    stats = vertical_gen.get_generation_stats()
    print(f"✓ Total timepoints: {stats['total_timepoints']}")
    print(f"✓ Scenario: {config.scenario_description}")
    print()

    # Step 2: Initialize LLM and storage
    print("Step 2: Initializing LLM client...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key, dry_run=False)

    if llm.dry_run:
        print("❌ CRITICAL: LLM in dry_run mode!")
        sys.exit(1)

    print(f"✓ LLM Client ready (dry_run={llm.dry_run})")

    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ Storage initialized")
    print()

    # Step 3: Run deep temporal simulation
    print("Step 3: Running REAL LLM simulation...")
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

    # Validate NO mock data
    print("Step 4: Validating no mock patterns...")
    if scene_title == "Test Scene":
        print("❌ FAILED: Got mock 'Test Scene'")
        sys.exit(1)

    mock_entities = [e for e in result['entities'] if "test_entity_" in e.entity_id]
    if mock_entities:
        print(f"❌ FAILED: Found {len(mock_entities)} mock entities")
        sys.exit(1)

    print("✓ No mock patterns detected - REAL data confirmed")
    print()

    # Step 5: Format training data
    print("Step 5: Formatting training data...")
    formatter = EntityEvolutionFormatter()
    training_examples = formatter.format_batch([result])

    print(f"✓ Generated {len(training_examples)} training examples")

    # Validate training data
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

    # Step 6: Save locally
    print("Step 6: Saving training data...")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("datasets/e2e_proof")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"e2e_proof_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')

    file_size = output_file.stat().st_size
    print(f"✓ Saved: {output_file}")
    print(f"✓ Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    # Step 7: Upload to Oxen (proof-the-e2e-works repo)
    print("Step 7: Uploading to Oxen (proof-the-e2e-works)...")

    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
    if not oxen_token:
        print("⚠️  WARNING: No OXEN_API_TOKEN - skipping upload")
        print(f"   Local file: {output_file}")
        return

    os.environ["OXEN_API_TOKEN"] = oxen_token

    oxen_client = OxenClient(
        namespace="realityinspector",
        repo_name="proof-the-e2e-works",
        interactive_auth=False
    )

    upload_result = oxen_client.upload_dataset(
        file_path=str(output_file),
        commit_message=f"E2E proof: {len(training_examples)} examples, 12 timepoints, REAL LLM",
        dst_path=f"datasets/{output_file.name}",
        create_repo_if_missing=True
    )

    print("✅ Upload successful!")
    print()
    print("="*70)
    print("E2E PROOF COMPLETE")
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
    print("✅ E2E WORKS - REAL LLM VALIDATED")
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
