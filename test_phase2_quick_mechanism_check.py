"""
Quick integration test for Phase 2 mechanisms (M5, M9, M10, M12, M13)
Tests that each mechanism invokes and tracks correctly
"""
import os
from datetime import datetime
from storage import GraphStore
from llm_v2 import LLMClient
from query_interface import QueryInterface
from schemas import Entity, Timepoint, ResolutionLevel
from metadata.tracking import MetadataManager

def setup_test_env():
    """Setup minimal test environment"""
    # Use in-memory DB for speed
    store = GraphStore("sqlite:///:memory:")
    llm = LLMClient(api_key=os.getenv("OPENROUTER_API_KEY", "test_key"),
                    dry_run=not os.getenv("LLM_SERVICE_ENABLED"))
    qi = QueryInterface(store, llm)

    # Create test timepoint
    timepoint = Timepoint(
        timepoint_id="test_tp",
        timestamp=datetime.now(),
        event_description="Test event for mechanism tracking",
        entities_present=["entity_a", "entity_b"],
        resolution_level=ResolutionLevel.SCENE
    )
    store.save_timepoint(timepoint)

    # Create test entities
    entity_a = Entity(
        entity_id="entity_a",
        entity_type="person",
        resolution_level=ResolutionLevel.TENSOR_ONLY,
        query_count=0,
        entity_metadata={
            "role": "participant",
            "knowledge_state": ["Basic knowledge about test event"]
        }
    )

    entity_b = Entity(
        entity_id="entity_b",
        entity_type="person",
        resolution_level=ResolutionLevel.SCENE,
        query_count=0,
        entity_metadata={
            "role": "observer",
            "knowledge_state": ["Observed the test event", "Interacted with entity_a"]
        }
    )

    store.save_entity(entity_a)
    store.save_entity(entity_b)

    return store, llm, qi, timepoint

def test_m5_query_resolution():
    """Test M5: Query Resolution - lazy elevation via query patterns"""
    print("\n🔍 Testing M5: Query Resolution")
    store, llm, qi, timepoint = setup_test_env()

    # Start tracking
    manager = MetadataManager()
    run_id = manager.start_run("test_m5_quick")

    try:
        # Query entity multiple times to trigger elevation
        for i in range(3):
            response = qi.query("What did entity_a know?")
            print(f"  Query {i+1}: {len(response)} chars")

        # Check if M5 was tracked
        metadata = manager.end_run(run_id)
        mechanisms = metadata.mechanisms_used.split(',') if metadata.mechanisms_used else []

        if "M5" in mechanisms:
            print("  ✅ M5 TRACKED")
            return True
        else:
            print(f"  ⚠️  M5 not tracked. Mechanisms: {mechanisms}")
            return False
    except Exception as e:
        print(f"  ❌ M5 test failed: {e}")
        manager.end_run(run_id)
        return False

def test_m9_on_demand_generation():
    """Test M9: On-Demand Entity Generation"""
    print("\n🆕 Testing M9: On-Demand Entity Generation")
    store, llm, qi, timepoint = setup_test_env()

    manager = MetadataManager()
    run_id = manager.start_run("test_m9_quick")

    try:
        # Query for entity that doesn't exist
        response = qi.query("What did attendee_99 think about the event?")
        print(f"  Response: {response[:100]}...")

        # Check if entity was created
        entity = store.get_entity("attendee_99")
        if entity:
            print(f"  ✅ Entity created: {entity.entity_id}")

        # Check tracking
        metadata = manager.end_run(run_id)
        mechanisms = metadata.mechanisms_used.split(',') if metadata.mechanisms_used else []

        if "M9" in mechanisms:
            print("  ✅ M9 TRACKED")
            return True
        else:
            print(f"  ⚠️  M9 not tracked. Mechanisms: {mechanisms}")
            return False
    except Exception as e:
        print(f"  ❌ M9 test failed: {e}")
        manager.end_run(run_id)
        return False

def test_m10_scene_entities():
    """Test M10: Scene-Level Entity Sets (atmosphere, environment, crowd)"""
    print("\n🎭 Testing M10: Scene Entities")
    store, llm, qi, timepoint = setup_test_env()

    manager = MetadataManager()
    run_id = manager.start_run("test_m10_quick")

    try:
        # Query for scene/atmosphere
        response = qi.query("What was the atmosphere like at the test event?")
        print(f"  Response: {response[:100]}...")

        # Check tracking
        metadata = manager.end_run(run_id)
        mechanisms = metadata.mechanisms_used.split(',') if metadata.mechanisms_used else []

        if "M10" in mechanisms:
            print("  ✅ M10 TRACKED")
            return True
        else:
            print(f"  ⚠️  M10 not tracked. Mechanisms: {mechanisms}")
            # M10 might be invoked in workflows, not query_interface
            print("  Note: M10 tracked via workflows.compute_scene_atmosphere()")
            return False
    except Exception as e:
        print(f"  ❌ M10 test failed: {e}")
        manager.end_run(run_id)
        return False

def test_m12_counterfactual_branching():
    """Test M12: Counterfactual Branching"""
    print("\n🌿 Testing M12: Counterfactual Branching")
    store, llm, qi, timepoint = setup_test_env()

    manager = MetadataManager()
    run_id = manager.start_run("test_m12_quick")

    try:
        # Submit "what if" query
        response = qi.query("What if entity_a was absent from the test event?")
        print(f"  Response: {response[:100]}...")

        # Check tracking
        metadata = manager.end_run(run_id)
        mechanisms = metadata.mechanisms_used.split(',') if metadata.mechanisms_used else []

        if "M12" in mechanisms:
            print("  ✅ M12 TRACKED")
            return True
        else:
            print(f"  ⚠️  M12 not tracked. Mechanisms: {mechanisms}")
            return False
    except Exception as e:
        print(f"  ❌ M12 test failed: {e}")
        manager.end_run(run_id)
        return False

def test_m13_multi_entity_synthesis():
    """Test M13: Multi-Entity Synthesis (relationship analysis)"""
    print("\n👥 Testing M13: Multi-Entity Synthesis")
    store, llm, qi, timepoint = setup_test_env()

    manager = MetadataManager()
    run_id = manager.start_run("test_m13_quick")

    try:
        # Query about relationship between entities
        response = qi.query("How did entity_a and entity_b interact?")
        print(f"  Response: {response[:100]}...")

        # Check tracking
        metadata = manager.end_run(run_id)
        mechanisms = metadata.mechanisms_used.split(',') if metadata.mechanisms_used else []

        if "M13" in mechanisms:
            print("  ✅ M13 TRACKED")
            return True
        else:
            print(f"  ⚠️  M13 not tracked. Mechanisms: {mechanisms}")
            # M13 might need workflow invocation
            print("  Note: M13 tracked via workflows.analyze_relationship_evolution()")
            return False
    except Exception as e:
        print(f"  ❌ M13 test failed: {e}")
        manager.end_run(run_id)
        return False

def main():
    """Run all Phase 2 mechanism tests"""
    print("=" * 70)
    print("PHASE 2 QUICK MECHANISM CHECK (M5, M9, M10, M12, M13)")
    print("=" * 70)

    results = {}

    # Test each mechanism
    results['M5'] = test_m5_query_resolution()
    results['M9'] = test_m9_on_demand_generation()
    results['M10'] = test_m10_scene_entities()
    results['M12'] = test_m12_counterfactual_branching()
    results['M13'] = test_m13_multi_entity_synthesis()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    tracked_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for mechanism, tracked in results.items():
        status = "✅ TRACKED" if tracked else "❌ NOT TRACKED"
        print(f"{mechanism}: {status}")

    print(f"\n📊 Total: {tracked_count}/{total_count} mechanisms tracked")

    if tracked_count == total_count:
        print("\n🎉 SUCCESS: All Phase 2 mechanisms tracked!")
        return 0
    else:
        print(f"\n⚠️  PARTIAL: {total_count - tracked_count} mechanisms need attention")
        return 1

if __name__ == "__main__":
    exit(main())
