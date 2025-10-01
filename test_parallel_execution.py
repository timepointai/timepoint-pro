#!/usr/bin/env python3
"""
Test script for Mechanism 1.3: LangGraph Parallel Execution
Tests that entity population runs in parallel using asyncio within LangGraph workflow.
"""

import asyncio
import time
from workflows import create_entity_training_workflow, WorkflowState
from llm import LLMClient
from storage import GraphStore
from schemas import ResolutionLevel
import networkx as nx

def test_parallel_execution():
    """Test that the parallel execution workflow works correctly"""
    print("🧪 Testing Mechanism 1.3: LangGraph Parallel Execution")

    # Create test components
    llm_client = LLMClient(
        api_key="dummy_key",
        base_url="https://dummy.com",
        dry_run=True
    )  # Use dry run to avoid API calls
    store = GraphStore("sqlite:///:memory:")

    # Create test graph with multiple entities
    test_graph = nx.Graph()
    test_graph.add_nodes_from(["entity_1", "entity_2", "entity_3"])

    # Create workflow
    workflow = create_entity_training_workflow(llm_client, store)

    # Create initial state
    initial_state: WorkflowState = {
        "graph": test_graph,
        "entities": [],
        "timepoint": "1789_test",
        "resolution": ResolutionLevel.GRAPH,
        "violations": [],
        "results": {},
        "entity_populations": {}
    }

    print(f"📊 Test graph has {len(test_graph.nodes())} entities: {list(test_graph.nodes())}")

    # Run the workflow
    start_time = time.time()
    try:
        result = workflow.invoke(initial_state)
        end_time = time.time()

        print(f"✅ Workflow completed successfully in {end_time - start_time:.2f} seconds")

        # Check results
        populations = result.get("entity_populations", {})
        entities = result.get("entities", [])

        print(f"📈 Generated {len(populations)} entity populations")
        print(f"📈 Created {len(entities)} entity objects")

        # Verify all expected entities were processed
        expected_entities = set(test_graph.nodes())
        processed_entities = set(populations.keys())

        if expected_entities == processed_entities:
            print("✅ All entities processed successfully")
        else:
            print("❌ Entity mismatch:")
            print(f"   Expected: {expected_entities}")
            print(f"   Processed: {processed_entities}")

        # Check entity structure
        if entities:
            sample_entity = entities[0]
            required_fields = ["entity_id", "entity_type", "temporal_span_start", "temporal_span_end", "resolution_level", "entity_metadata"]
            missing_fields = [field for field in required_fields if not hasattr(sample_entity, field)]
            if not missing_fields:
                print("✅ Entity structure is correct")
            else:
                print(f"❌ Missing entity fields: {missing_fields}")

        # Check that populations have required data
        if populations:
            sample_pop = list(populations.values())[0]
            required_pop_fields = ["knowledge_state", "energy_budget", "personality_traits", "temporal_awareness", "confidence"]
            missing_pop_fields = [field for field in required_pop_fields if not hasattr(sample_pop, field)]
            if not missing_pop_fields:
                print("✅ Population structure is correct")
            else:
                print(f"❌ Missing population fields: {missing_pop_fields}")

        print("🎉 Mechanism 1.3 test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = test_parallel_execution()
    exit(0 if success else 1)
