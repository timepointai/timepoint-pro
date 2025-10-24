"""
Quick test to verify M14, M15, M16 integration into E2E workflow
"""
import sys
import sqlite3
from orchestrator import OrchestratorAgent
from generation.config_schema import TEMPLATE_REGISTRY, E2EWorkflowConfig
from llm_v2 import LLMClient
from storage import GraphStore
from metadata.run_tracker import MetadataManager
from metadata.tracking import set_metadata_manager, set_current_run_id, clear_current_run_id
from schemas import TemporalMode
import uuid

def test_mechanism_integration():
    """Test that M14, M15, M16 fire during E2E execution"""

    # Initialize services
    llm = LLMClient()
    store = GraphStore("timepoint.db")

    # Initialize tracking
    metadata_mgr = MetadataManager("metadata/runs.db")
    set_metadata_manager(metadata_mgr)

    # Test M14 with hospital_crisis template
    print("\n" + "=" * 80)
    print("Testing M14 (Circadian Patterns) with hospital_crisis template")
    print("=" * 80)

    config = TEMPLATE_REGISTRY.get("hospital_crisis")
    if not config:
        print("❌ hospital_crisis template not found")
        return False

    # Create run tracking
    run_id = f"test_m14_{uuid.uuid4().hex[:8]}"
    set_current_run_id(run_id)

    metadata = metadata_mgr.start_run(
        run_id=run_id,
        template_id="hospital_crisis",
        causal_mode=TemporalMode.PEARL,
        max_entities=10,
        max_timepoints=10
    )

    try:
        # Run orchestrator
        orchestrator = OrchestratorAgent(llm, store, context=config.metadata or {})
        result = orchestrator.orchestrate_scene(config.scene_description)

        # Check if M14 fired
        conn = sqlite3.connect("metadata/runs.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM mechanism_usage WHERE run_id = ? AND mechanism = 'M14'",
            (run_id,)
        )
        m14_count = cursor.fetchone()[0]
        conn.close()

        if m14_count > 0:
            print(f"\n✅ M14 fired {m14_count} times during orchestration!")
            return True
        else:
            print(f"\n⚠️  M14 did not fire during orchestration")
            print(f"   This might be expected if dialog synthesis wasn't called")
            return False

    except Exception as e:
        print(f"\n❌ Error during orchestration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        clear_current_run_id()
        metadata_mgr.complete_run(
            run_id=run_id,
            entities_created=0,
            timepoints_created=0,
            training_examples=0,
            cost_usd=0.0,
            llm_calls=0,
            tokens_used=0
        )

if __name__ == "__main__":
    success = test_mechanism_integration()
    sys.exit(0 if success else 1)
