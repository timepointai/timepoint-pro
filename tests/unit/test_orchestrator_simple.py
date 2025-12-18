#!/usr/bin/env python
"""
Simple test to verify orchestrator imports and basic functionality.
"""
import pytest

from orchestrator import (
    OrchestratorAgent,
    SceneParser,
    KnowledgeSeeder,
    RelationshipExtractor,
    ResolutionAssigner,
    simulate_event
)
from llm import LLMClient
from storage import GraphStore


@pytest.mark.unit
def test_orchestrator_imports():
    """Test that all orchestrator components can be imported."""
    # If we get here, imports succeeded
    assert OrchestratorAgent is not None
    assert SceneParser is not None
    assert KnowledgeSeeder is not None
    assert RelationshipExtractor is not None
    assert ResolutionAssigner is not None
    assert simulate_event is not None
    print("✓ All imports successful")


@pytest.mark.unit
def test_dependency_imports():
    """Test that dependencies can be imported."""
    assert LLMClient is not None
    assert GraphStore is not None
    print("✓ Dependencies imported")


@pytest.mark.unit
def test_llm_client_dry_run():
    """Test LLMClient can be created in dry_run mode."""
    llm_client = LLMClient(api_key="test", dry_run=True)
    assert llm_client is not None
    print("✓ LLMClient created (dry_run mode)")


@pytest.mark.unit
def test_graph_store_memory():
    """Test GraphStore can be created with in-memory database."""
    store = GraphStore("sqlite:///:memory:")
    assert store is not None
    print("✓ GraphStore created")


@pytest.mark.unit
def test_orchestrator_agent_creation():
    """Test OrchestratorAgent can be instantiated."""
    llm_client = LLMClient(api_key="test", dry_run=True)
    store = GraphStore("sqlite:///:memory:")
    orchestrator = OrchestratorAgent(llm_client, store)
    assert orchestrator is not None
    print("✓ OrchestratorAgent created")


@pytest.mark.unit
@pytest.mark.llm
def test_scene_parsing_dry_run():
    """Test scene parsing in dry_run mode."""
    llm_client = LLMClient(api_key="test", dry_run=True)
    parser = SceneParser(llm_client)
    spec = parser.parse("simulate a test event")

    assert spec is not None
    assert spec.scene_title is not None
    print(f"✓ Scene parsed: '{spec.scene_title}'")
    print(f"  - Entities: {len(spec.entities)}")
    print(f"  - Timepoints: {len(spec.timepoints)}")
    print(f"  - Temporal mode: {spec.temporal_mode}")


@pytest.mark.unit
@pytest.mark.llm
def test_full_orchestration_dry_run():
    """Test full orchestration in dry_run mode."""
    llm_client = LLMClient(api_key="test", dry_run=True)
    store = GraphStore("sqlite:///:memory:")
    orchestrator = OrchestratorAgent(llm_client, store)

    result = orchestrator.orchestrate(
        "simulate a small historical meeting",
        context={"max_entities": 3, "max_timepoints": 2},
        save_to_db=False
    )

    assert result is not None
    assert 'entities' in result
    assert 'timepoints' in result
    assert 'graph' in result

    print("✓ Orchestration successful")
    print(f"  - Entities created: {len(result['entities'])}")
    print(f"  - Timepoints created: {len(result['timepoints'])}")
    print(f"  - Graph nodes: {result['graph'].number_of_nodes()}")
    print(f"  - Graph edges: {result['graph'].number_of_edges()}")


@pytest.mark.unit
@pytest.mark.llm
def test_simulate_event_dry_run():
    """Test convenience function simulate_event in dry_run mode."""
    llm_client = LLMClient(api_key="test", dry_run=True)
    store = GraphStore("sqlite:///:memory:")

    result = simulate_event(
        "simulate a brief gathering",
        llm_client,
        store,
        save_to_db=False
    )

    assert result is not None
    assert 'specification' in result
    print("✓ simulate_event() successful")
    print(f"  - Scene: {result['specification'].scene_title}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
