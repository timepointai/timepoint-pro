#!/usr/bin/env python3
"""
E2E Test: Prebaked Example → Timepoint AI → Oxen Upload

This test validates the complete workflow:
1. Load a prebaked simulation config (Jefferson Dinner)
2. Run the actual timepoint AI orchestrator with real LLM
3. Generate training data from simulation results
4. Upload to Oxen.ai
5. Return and validate Oxen repo link

Requirements:
- OPENROUTER_API_KEY environment variable
- OXEN_API_TOKEN environment variable
- LLM_SERVICE_ENABLED=true
"""

import os
import sys
import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path

# Ensure environment is configured
from dotenv import load_dotenv
load_dotenv()

from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
from oxen_integration import OxenClient
from oxen_integration.data_formatters import EntityEvolutionFormatter


@pytest.mark.e2e
@pytest.mark.llm
def test_prebaked_jefferson_to_oxen():
    """
    E2E Test: Jefferson Dinner prebaked → orchestrator → Oxen upload

    This test:
    - Uses a prebaked example (no generation needed)
    - Runs the actual timepoint AI orchestrator
    - Validates real LLM integration (no mocks)
    - Uploads training data to Oxen
    - Returns valid Oxen repo link
    """
    print("\n" + "="*70)
    print("E2E TEST: PREBAKED → TIMEPOINT AI → OXEN")
    print("="*70)
    print()

    # Step 1: Verify environment
    print("Step 1: Verifying environment...")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    oxen_token = os.getenv("OXEN_API_TOKEN") or os.getenv("OXEN_API_KEY")
    if not oxen_token:
        pytest.skip("OXEN_API_TOKEN not set")

    llm_enabled = os.getenv("LLM_SERVICE_ENABLED", "true").lower() == "true"
    if not llm_enabled:
        pytest.fail("LLM_SERVICE_ENABLED=false - real LLM required")

    print("✓ OPENROUTER_API_KEY set")
    print("✓ OXEN_API_TOKEN set")
    print("✓ LLM_SERVICE_ENABLED=true")
    print()

    # Step 2: Load prebaked Jefferson Dinner example
    print("Step 2: Loading prebaked Jefferson Dinner config...")
    config = SimulationConfig.example_jefferson_dinner()

    print(f"✓ Scenario: {config.scenario_description}")
    print(f"✓ Entities: {config.entities.count}")
    print(f"✓ Timepoints: {config.timepoints.count}")
    print(f"✓ Temporal mode: {config.temporal.mode.value}")
    print()

    # Step 3: Initialize LLM client and storage
    print("Step 3: Initializing LLM client and storage...")
    llm = LLMClient(api_key=api_key, dry_run=False)

    if llm.dry_run:
        pytest.fail("LLM client in dry_run mode - real LLM required")

    print(f"✓ LLM Client ready (dry_run={llm.dry_run})")

    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")
    print(f"✓ Storage initialized: {db_path}")
    print()

    # Step 4: Run ACTUAL timepoint AI orchestrator
    print("Step 4: Running timepoint AI orchestrator...")
    print("   (This uses REAL LLM to generate scene specifications)")
    print()

    # Use the timepoint config to create multiple timepoints for T0→T1 training data
    # The orchestrator will generate timepoints based on max_timepoints
    total_timepoints = config.timepoints.count + config.timepoints.before_count + config.timepoints.after_count

    result = simulate_event(
        config.scenario_description,
        llm,
        store,
        context={
            "max_entities": config.entities.count,
            "max_timepoints": total_timepoints,  # Use expanded timepoint count
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

    # Step 5: Validate real LLM data (no mocks)
    print("Step 5: Validating real LLM data...")

    # Check for mock patterns
    assert scene_title != "Test Scene", "Got mock 'Test Scene' - real LLM not used"

    mock_entities = [e for e in result['entities'] if "test_entity_" in e.entity_id]
    assert len(mock_entities) == 0, f"Found {len(mock_entities)} mock entities - real LLM not used"

    # Verify entities have real names
    entity_ids = [e.entity_id for e in result['entities']]
    print(f"✓ Entity IDs: {entity_ids}")

    # Verify timepoints have real event descriptions
    timepoint_events = [t.event_description for t in result['timepoints']]
    print(f"✓ Timepoint events: {timepoint_events[:3] if len(timepoint_events) > 3 else timepoint_events}")

    print("✓ No mock patterns detected - REAL LLM data confirmed")
    print()

    # Step 6: Format training data
    print("Step 6: Formatting training data...")
    formatter = EntityEvolutionFormatter()
    training_examples = formatter.format_batch([result])

    print(f"✓ Generated {len(training_examples)} training examples")
    print(f"   Format: T0→T1 entity state evolution")
    print()

    # Validate training data quality
    mock_count = 0
    for example in training_examples[:5]:
        completion = str(example.get('completion', ''))
        if 'test_entity_' in completion or '"fact1"' in completion:
            mock_count += 1

    assert mock_count == 0, f"Found {mock_count} mock patterns in training data"
    print("✓ Training data validated (0 mock patterns)")
    print()

    # Step 7: Save locally
    print("Step 7: Saving training data locally...")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("datasets/e2e_prebaked")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"prebaked_jefferson_{timestamp}.jsonl"

    with open(output_file, 'w') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')

    file_size = output_file.stat().st_size
    print(f"✓ Saved: {output_file}")
    print(f"✓ Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    # Step 8: Upload to Oxen
    print("Step 8: Uploading to Oxen (proof-the-e2e-works)...")

    os.environ["OXEN_API_TOKEN"] = oxen_token

    oxen_client = OxenClient(
        namespace="realityinspector",
        repo_name="proof-the-e2e-works",
        interactive_auth=False
    )

    upload_result = oxen_client.upload_dataset(
        file_path=str(output_file),
        commit_message=f"E2E Test: Jefferson Dinner prebaked, {len(training_examples)} examples, {len(result['timepoints'])} timepoints",
        dst_path=f"datasets/e2e_prebaked/{output_file.name}",
        create_repo_if_missing=True
    )

    print("✅ Upload successful!")
    print()

    # Step 9: Validate Oxen URLs
    print("Step 9: Validating Oxen URLs...")

    assert upload_result.success, "Upload failed"
    assert upload_result.repo_url, "No repo URL returned"
    assert "www.oxen.ai" in upload_result.repo_url, f"Wrong domain: {upload_result.repo_url}"
    assert "realityinspector/proof-the-e2e-works" in upload_result.repo_url, f"Wrong repo: {upload_result.repo_url}"

    print(f"✓ Repo URL: {upload_result.repo_url}")
    print(f"✓ Dataset URL: {upload_result.dataset_url}")
    print(f"✓ Commit ID: {upload_result.commit_id}")
    print()

    # Step 10: Summary
    print("="*70)
    print("E2E TEST COMPLETE: PREBAKED → TIMEPOINT AI → OXEN")
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
    print("✅ ALL VALIDATIONS PASSED")
    print()

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

    # Return the repo URL for external validation
    return upload_result.repo_url


if __name__ == "__main__":
    """
    Run this test standalone to validate the complete workflow.

    Usage:
        export OPENROUTER_API_KEY=your_key
        export OXEN_API_TOKEN=your_token
        export LLM_SERVICE_ENABLED=true
        python test_e2e_prebaked_to_oxen.py
    """
    try:
        repo_url = test_prebaked_jefferson_to_oxen()
        print(f"\n✅ SUCCESS: Repository at {repo_url}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
