
import os
from generation.config_schema import SimulationConfig
from e2e_workflows.e2e_runner import FullE2EWorkflowRunner
from metadata.run_tracker import MetadataManager
import logging

logging.basicConfig(level=logging.INFO)

# Load template
config = SimulationConfig.example_sign_loops_cyclical()

print("\n" + "="*80)
print(f"RUNNING FULL E2E WORKFLOW: {config.world_id}")
print(f"6-Step Pipeline: scene → temporal → training → format → oxen → metadata")
print("="*80 + "\n")

try:
    # Initialize metadata manager
    metadata_manager = MetadataManager("metadata/runs.db")

    # Initialize E2E runner
    runner = FullE2EWorkflowRunner(metadata_manager)

    # Run complete workflow
    metadata = runner.run(config)

    print(f"\n✅ E2E WORKFLOW COMPLETE")
    print(f"   Run ID: {metadata.run_id}")
    print(f"   Entities: {metadata.entities_created}")
    print(f"   Timepoints: {metadata.timepoints_created}")
    print(f"   Training Examples: {metadata.training_examples}")
    print(f"   Mechanisms Used: {len(metadata.mechanisms_used)}/17")
    print(f"   Cost: ${metadata.cost_usd:.2f}")
    if metadata.oxen_repo_url:
        print(f"   Oxen Repo: {metadata.oxen_repo_url}")

except Exception as e:
    print(f"\n❌ E2E WORKFLOW FAILED: {e}")
    import traceback
    traceback.print_exc()
    raise
