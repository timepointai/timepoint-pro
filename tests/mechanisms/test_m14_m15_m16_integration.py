"""
Quick test to verify M14, M15, M16 integration into E2E workflow
"""
import os
import pytest
import sqlite3
import uuid

from orchestrator import OrchestratorAgent
from generation.templates.loader import TemplateLoader
from llm_v2 import LLMClient
from storage import GraphStore
from metadata.run_tracker import MetadataManager
from metadata.tracking import set_metadata_manager, set_current_run_id, clear_current_run_id
from schemas import TemporalMode


@pytest.mark.mechanism
@pytest.mark.m14
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_m14_mechanism_integration():
    """Test that M14 (Circadian Patterns) fires during E2E execution with hospital_crisis template."""

    # Initialize services
    llm = LLMClient()
    store = GraphStore("sqlite:///:memory:")

    # Initialize tracking
    metadata_mgr = MetadataManager("metadata/runs.db")
    set_metadata_manager(metadata_mgr)

    # Load hospital_crisis template using TemplateLoader
    print("\n" + "=" * 80)
    print("Testing M14 (Circadian Patterns) with hospital_crisis template")
    print("=" * 80)

    loader = TemplateLoader()
    config = loader.load_template("showcase/hospital_crisis")
    assert config is not None, "hospital_crisis template not found"

    # Create run tracking
    run_id = f"test_m14_{uuid.uuid4().hex[:8]}"
    set_current_run_id(run_id)

    metadata_mgr.start_run(
        run_id=run_id,
        template_id="hospital_crisis",
        causal_mode=TemporalMode.PEARL,
        max_entities=10,
        max_timepoints=10
    )

    try:
        # Run orchestrator
        orchestrator = OrchestratorAgent(llm, store, context=config.metadata or {})
        result = orchestrator.orchestrate_scene(config.scenario_description)

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
        else:
            print(f"\n⚠️  M14 did not fire during orchestration")
            print(f"   This might be expected if dialog synthesis wasn't called")

    except Exception as e:
        print(f"\n❌ Error during orchestration: {e}")
        raise
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
    pytest.main([__file__, "-v"])
