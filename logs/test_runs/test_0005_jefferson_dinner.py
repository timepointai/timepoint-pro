
from generation.config_schema import SimulationConfig
from workflows import create_entity_training_workflow
import logging

logging.basicConfig(level=logging.INFO)

# Load template
config = SimulationConfig.example_jefferson_dinner()

# Run workflow
print("\n" + "="*80)
print(f"RUNNING: {config.world_id}")
print("="*80 + "\n")

try:
    workflow = create_entity_training_workflow(config)
    workflow.run()
    print(f"\n✅ COMPLETE: {config.world_id}")
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    raise
