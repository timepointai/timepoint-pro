
import os
import tempfile
from generation.config_schema import SimulationConfig
from orchestrator import simulate_event
from llm_v2 import LLMClient
from storage import GraphStore
import logging

logging.basicConfig(level=logging.INFO)

# Load template
config = SimulationConfig.example_jefferson_dinner()

print("\n" + "="*80)
print(f"RUNNING: {config.world_id}")
print("="*80 + "\n")

try:
    # Initialize LLM client
    api_key = os.getenv("OPENROUTER_API_KEY")
    llm = LLMClient(api_key=api_key, dry_run=False)

    # Initialize storage
    db_path = tempfile.mktemp(suffix=".db")
    store = GraphStore(f"sqlite:///{db_path}")

    # Run simulation
    result = simulate_event(
        config.scenario_description,
        llm,
        store,
        context={
            "max_entities": config.entities.count,
            "max_timepoints": config.timepoints.count,
            "temporal_mode": config.temporal.mode.value
        },
        save_to_db=True
    )

    print(f"\n✅ COMPLETE: {config.world_id}")
    print(f"   Entities: {len(result['entities'])}")
    print(f"   Timepoints: {len(result['timepoints'])}")

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)

except Exception as e:
    print(f"\n❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    raise
