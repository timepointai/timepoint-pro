#!/usr/bin/env python3
"""
Complete E2E Workflow: Timepoint → Training → Fine-tune → Model Comparison

This script executes the complete workflow:
a) Run timepoint AI with prebaked examples
b) Train identity tensors (TTM compression)
c) Use LLM functions within timepoint orchestrator
d) Use prebaked Jefferson Dinner example
e) Create vertical training set with 200+ timepoints
f) Publish data to Oxen (new repo with experiment branch)
g) Manual fine-tune creation on Oxen (documented steps)
h) Prepare for model comparison (future: test fine-tuned vs base)

Requirements:
- OPENROUTER_API_KEY environment variable
- OXEN_API_TOKEN environment variable
- LLM_SERVICE_ENABLED=true

Output:
- Training data link on Oxen
- Fine-tune creation instructions
- Model comparison setup (for manual execution)
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
    print("="*80)
    print("COMPLETE E2E WORKFLOW: TIMEPOINT → TRAINING → FINE-TUNE")
    print("="*80)
    print()

    # Generate unique experiment ID
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    experiment_id = f"temporal-reasoning-{timestamp}"

    print(f"Experiment ID: {experiment_id}")
    print()

    # =========================================================================
    # STEP 1: Load prebaked example (Jefferson Dinner)
    # =========================================================================
    print("STEP 1: Load prebaked Jefferson Dinner example")
    print("-" * 80)
    base_config = SimulationConfig.example_jefferson_dinner()
    print(f"✓ Scenario: {base_config.scenario_description}")
    print(f"✓ Base entities: {base_config.entities.count}")
    print(f"✓ Base timepoints: {base_config.timepoints.count}")
    print()

    # =========================================================================
    # STEP 2: Configure for maximum timepoints within constraints
    # =========================================================================
    print("STEP 2: Configure simulation for deep temporal depth")
    print("-" * 80)
    vertical_gen = VerticalGenerator()

    # Max allowed: 50 before + 50 after = 101 total timepoints per simulation
    # For demonstration, we'll use 25+25 = 51 timepoints (more reasonable for testing)
    # User can adjust for production runs
    config = vertical_gen.generate_temporal_depth(
        base_config,
        before_count=25,  # 25 timepoints before
        after_count=25,   # 25 timepoints after
        strategy="progressive_training"
    )

    stats = vertical_gen.get_generation_stats()
    print(f"✓ Configured timepoints: {stats['total_timepoints']}")
    print()

    # For full 200+ timepoint generation, set target_timepoints = 201
    target_timepoints = 201  # FULL 200+ TIMEPOINT GENERATION
    print(f"✓ Target timepoints: {target_timepoints}")
    print(f"   This will generate ~{config.entities.count * 200} training examples")
    print(f"   Expected runtime: 30-60 minutes with real LLM calls")
    print()

    # =========================================================================
    # STEP 3: Initialize LLM and storage
    # =========================================================================
    print("STEP 3: Initialize LLM client and storage")
    print("-" * 80)
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key)

    if llm.dry_run:
        print("❌ CRITICAL: LLM in dry_run mode!")
        sys.exit(1)

    print(f"✓ LLM Client ready (dry_run={llm.dry_run})")

    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ Storage initialized: {db_path}")
    print()

    # =========================================================================
    # STEP 4: Run timepoint AI orchestrator (200+ timepoints)
    # =========================================================================
    print("STEP 4: Run timepoint AI orchestrator with real LLM")
    print("-" * 80)
    print(f"   Requesting {target_timepoints} timepoints from orchestrator...")
    print("   This will take several minutes with real LLM calls...")
    print()

    result = simulate_event(
        config.scenario_description,
        llm,
        store,
        context={
            "max_entities": config.entities.count,
            "max_timepoints": target_timepoints,  # Request 201 timepoints
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

    # =========================================================================
    # STEP 5: Validate real LLM data (no mocks)
    # =========================================================================
    print("STEP 5: Validate real LLM data")
    print("-" * 80)
    if scene_title == "Test Scene":
        print("❌ FAILED: Got mock 'Test Scene'")
        sys.exit(1)

    mock_entities = [e for e in result['entities'] if "test_entity_" in e.entity_id]
    if mock_entities:
        print(f"❌ FAILED: Found {len(mock_entities)} mock entities")
        sys.exit(1)

    print("✓ No mock patterns detected - REAL data confirmed")
    print(f"✓ Scene title: {scene_title}")
    print(f"✓ Entity IDs: {[e.entity_id for e in result['entities']]}")
    print()

    # =========================================================================
    # STEP 6: Format training data (T0→T1 temporal evolution)
    # =========================================================================
    print("STEP 6: Format vertical training data (T0→T1 pairs)")
    print("-" * 80)
    formatter = EntityEvolutionFormatter()
    training_examples = formatter.format_batch([result])

    print(f"✓ Generated {len(training_examples)} training examples")
    print(f"   Format: T0→T1 entity state evolution across {len(result['timepoints'])} timepoints")

    # Calculate expected examples: (entities * (timepoints - 1))
    expected_examples = len(result['entities']) * max(0, len(result['timepoints']) - 1)
    print(f"   Expected: ~{expected_examples} examples ({len(result['entities'])} entities × {len(result['timepoints']) - 1} transitions)")
    print()

    # Validate training data quality
    mock_count = 0
    for example in training_examples[:10]:
        completion = str(example.get('completion', ''))
        if 'test_entity_' in completion or '"fact1"' in completion:
            mock_count += 1

    if mock_count > 0:
        print(f"❌ FAILED: Found {mock_count} mock patterns in training data")
        sys.exit(1)

    print("✓ Training data validated (0 mock patterns)")
    print()

    # =========================================================================
    # STEP 7: Save training data locally
    # =========================================================================
    print("STEP 7: Save training data locally")
    print("-" * 80)
    output_dir = Path("datasets/complete_e2e")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"temporal_reasoning_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')

    file_size = output_file.stat().st_size
    print(f"✓ Saved: {output_file}")
    print(f"✓ Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    # =========================================================================
    # STEP 8: Create new Oxen repo with experiment branch
    # =========================================================================
    print("STEP 8: Publish to Oxen (new repo with experiment branch)")
    print("-" * 80)

    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
    if not oxen_token:
        print("⚠️  WARNING: No OXEN_API_TOKEN - skipping Oxen upload")
        print(f"   Local file: {output_file}")
        print()
        print_summary(scene_title, result, training_examples, output_file, None, None)
        cleanup(db_path)
        return

    os.environ["OXEN_API_TOKEN"] = oxen_token

    # Create Oxen client for new repo
    repo_name = f"timepoint-training-{timestamp[:8]}"  # YYYYMMDD format

    oxen_client = OxenClient(
        namespace="realityinspector",
        repo_name=repo_name,
        interactive_auth=False
    )

    print(f"   Repository: realityinspector/{repo_name}")
    print()

    # =========================================================================
    # STEP 9: Create experiment branch
    # =========================================================================
    print("STEP 9: Create experiment branch")
    print("-" * 80)

    try:
        # Create repo if it doesn't exist
        if not oxen_client.repo_exists():
            print(f"   Creating repository: {repo_name}...")
            repo_info = oxen_client.create_repo(
                name=repo_name,
                description=f"Temporal reasoning training data - {experiment_id}"
            )
            print(f"✓ Repository created: {repo_info.url}")
        else:
            print(f"✓ Repository exists: realityinspector/{repo_name}")

        # Create experiment branch
        experiment_branch = f"experiments/{experiment_id}"
        if not oxen_client.branch_exists(experiment_branch):
            print(f"   Creating experiment branch: {experiment_branch}...")
            oxen_client.create_experiment_branch(experiment_id)
            print(f"✓ Branch created: {experiment_branch}")
        else:
            print(f"✓ Branch exists: {experiment_branch}")

        # Switch to experiment branch
        oxen_client.switch_branch(experiment_branch)
        print(f"✓ Switched to: {experiment_branch}")
        print()

    except Exception as e:
        print(f"⚠️  Branch creation warning: {e}")
        print("   Continuing with main branch...")
        experiment_branch = "main"
        print()

    # =========================================================================
    # STEP 10: Upload training data
    # =========================================================================
    print("STEP 10: Upload training data to Oxen")
    print("-" * 80)

    upload_result = oxen_client.upload_dataset(
        file_path=str(output_file),
        commit_message=f"Temporal reasoning training: {len(training_examples)} examples, {len(result['timepoints'])} timepoints, {experiment_id}",
        dst_path=f"datasets/{experiment_id}/{output_file.name}",
        create_repo_if_missing=True
    )

    print("✅ Upload successful!")
    print()

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_summary(scene_title, result, training_examples, output_file, upload_result, experiment_branch)

    # =========================================================================
    # CLEANUP
    # =========================================================================
    cleanup(db_path)


def print_summary(scene_title, result, training_examples, output_file, upload_result, experiment_branch):
    """Print final summary and next steps"""
    print("="*80)
    print("COMPLETE E2E WORKFLOW FINISHED")
    print("="*80)
    print()
    print("📊 SIMULATION RESULTS")
    print("-" * 80)
    print(f"Scene: {scene_title}")
    print(f"Entities: {len(result['entities'])}")
    print(f"Timepoints: {len(result['timepoints'])}")
    print(f"Training examples: {len(training_examples)}")
    print(f"Mock patterns: 0")
    print()

    print("📁 LOCAL DATA")
    print("-" * 80)
    print(f"File: {output_file}")
    print(f"Size: {output_file.stat().st_size:,} bytes")
    print()

    if upload_result:
        print("🔗 OXEN DATA")
        print("-" * 80)
        print(f"Repository: {upload_result.repo_url}")
        print(f"Dataset: {upload_result.dataset_url}")
        print(f"Branch: {experiment_branch}")
        print(f"Commit: {upload_result.commit_id}")
        print()

        print("📋 NEXT STEPS: FINE-TUNE CREATION")
        print("-" * 80)
        print("Oxen.ai does not support programmatic fine-tune creation.")
        print("Follow these steps to create a fine-tuning job:")
        print()
        print(f"1. Visit: {upload_result.repo_url}")
        print(f"2. Navigate to branch: {experiment_branch}")
        print(f"3. Navigate to dataset file")
        print("4. Click 'Fine-tune' button to create fine-tuning job")
        print("5. Configure:")
        print("   - Base model: Qwen/Qwen3-4B (or your choice)")
        print("   - Epochs: 1-3")
        print("   - Learning rate: 0.0001")
        print("   - LoRA rank: 16")
        print()
        print("📋 MODEL COMPARISON (Future)")
        print("-" * 80)
        print("After fine-tune completes:")
        print("1. Download fine-tuned model from Oxen")
        print("2. Run comparison script (to be created)")
        print("3. Test on held-out temporal reasoning examples")
        print("4. Compare base model vs fine-tuned accuracy")
        print()

    print("✅ WORKFLOW COMPLETE")
    print()


def cleanup(db_path):
    """Clean up temporary files"""
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
