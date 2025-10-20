#!/usr/bin/env python
# Simple test to verify orchestrator imports and basic functionality

import sys
sys.path.insert(0, '/code')

print("Testing orchestrator imports...")

try:
    from orchestrator import (
        OrchestratorAgent,
        SceneParser,
        KnowledgeSeeder,
        RelationshipExtractor,
        ResolutionAssigner,
        simulate_event
    )
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    from llm import LLMClient
    from storage import GraphStore
    print("✓ Dependencies imported")
except Exception as e:
    print(f"✗ Dependency import failed: {e}")
    sys.exit(1)

# Test basic instantiation
print("\nTesting basic instantiation...")

try:
    llm_client = LLMClient(api_key="test", dry_run=True)
    print(f"✓ LLMClient created (dry_run mode)")
except Exception as e:
    print(f"✗ LLMClient creation failed: {e}")
    sys.exit(1)

try:
    store = GraphStore("sqlite:///:memory:")
    print("✓ GraphStore created")
except Exception as e:
    print(f"✗ GraphStore creation failed: {e}")
    sys.exit(1)

try:
    orchestrator = OrchestratorAgent(llm_client, store)
    print("✓ OrchestratorAgent created")
except Exception as e:
    print(f"✗ OrchestratorAgent creation failed: {e}")
    sys.exit(1)

# Test scene parsing
print("\nTesting scene parsing...")

try:
    parser = SceneParser(llm_client)
    spec = parser.parse("simulate a test event")
    print(f"✓ Scene parsed: '{spec.scene_title}'")
    print(f"  - Entities: {len(spec.entities)}")
    print(f"  - Timepoints: {len(spec.timepoints)}")
    print(f"  - Temporal mode: {spec.temporal_mode}")
except Exception as e:
    print(f"✗ Scene parsing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test full orchestration
print("\nTesting full orchestration...")

try:
    result = orchestrator.orchestrate(
        "simulate a small historical meeting",
        context={"max_entities": 3, "max_timepoints": 2},
        save_to_db=False
    )
    print("✓ Orchestration successful")
    print(f"  - Entities created: {len(result['entities'])}")
    print(f"  - Timepoints created: {len(result['timepoints'])}")
    print(f"  - Graph nodes: {result['graph'].number_of_nodes()}")
    print(f"  - Graph edges: {result['graph'].number_of_edges()}")
    print(f"  - Temporal agent mode: {result['temporal_agent'].mode.value}")
except Exception as e:
    print(f"✗ Orchestration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test convenience function
print("\nTesting convenience function...")

try:
    result = simulate_event(
        "simulate a brief gathering",
        llm_client,
        store,
        save_to_db=False
    )
    print("✓ simulate_event() successful")
    print(f"  - Scene: {result['specification'].scene_title}")
except Exception as e:
    print(f"✗ simulate_event() failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED ✓")
print("="*60)
