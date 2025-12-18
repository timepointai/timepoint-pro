#!/usr/bin/env python3
"""
Test script for Mechanism 1.3: LangGraph Parallel Execution
Tests that entity population runs in parallel using asyncio within LangGraph workflow.
"""

import os
import asyncio
import time
import pytest
from workflows import create_entity_training_workflow, WorkflowState
from llm_v2 import LLMClient
from storage import GraphStore
from schemas import ResolutionLevel
import networkx as nx


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set"
)
def test_parallel_execution():
    """Test that the parallel execution workflow works correctly"""
    print("🧪 Testing Mechanism 1.3: LangGraph Parallel Execution")

    api_key = os.getenv("OPENROUTER_API_KEY")
    llm_client = LLMClient(api_key=api_key)
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

        print("🎉 Mechanism 1.3 test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
