"""
Integration test for ANDOS E2E workflow.

Tests the ANDOS integration in e2e_runner.py with a simple 3-entity scenario.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from e2e_workflows.e2e_runner import _infer_interaction_graph
from andos.layer_computer import compute_andos_layers, validate_andos_layers
from schemas import Entity


def make_entity(entity_id: str, entity_type: str = "human") -> Entity:
    """Helper to create test entity"""
    return Entity(
        entity_id=entity_id,
        entity_type=entity_type,
        resolution_level="scene",
        entity_metadata={}
    )


def test_infer_interaction_graph_simple():
    """Test _infer_interaction_graph with 3 entities"""
    entities = [
        make_entity("alice"),
        make_entity("bob"),
        make_entity("charlie")
    ]

    graph = _infer_interaction_graph(entities)

    # Should create sequential chain: alice → bob → charlie
    assert "interactions" in graph
    assert len(graph["interactions"]) == 2

    interactions = graph["interactions"]
    assert interactions[0]["from"] == "alice"
    assert interactions[0]["to"] == "bob"
    assert interactions[1]["from"] == "bob"
    assert interactions[1]["to"] == "charlie"


def test_infer_interaction_graph_single():
    """Test _infer_interaction_graph with 1 entity"""
    entities = [make_entity("alice")]

    graph = _infer_interaction_graph(entities)

    # Single entity - no interactions
    assert graph["interactions"] == []


def test_andos_with_inferred_graph():
    """Test ANDOS with inferred interaction graph"""
    entities = [
        make_entity("alice"),
        make_entity("bob"),
        make_entity("charlie")
    ]

    # Infer graph
    graph = _infer_interaction_graph(entities)

    # Compute ANDOS layers
    layers = compute_andos_layers(entities, "alice", graph)

    # Should have 3 layers: [charlie], [bob], [alice]
    assert len(layers) == 3
    assert [e.entity_id for e in layers[0]] == ["charlie"]  # Periphery
    assert [e.entity_id for e in layers[1]] == ["bob"]
    assert [e.entity_id for e in layers[2]] == ["alice"]  # Core

    # Validate layers
    valid, violations = validate_andos_layers(layers, graph)
    assert valid is True
    assert len(violations) == 0


def test_andos_with_5_entities():
    """Test ANDOS with 5 entities (larger scenario)"""
    entities = [
        make_entity("a"),
        make_entity("b"),
        make_entity("c"),
        make_entity("d"),
        make_entity("e")
    ]

    # Infer graph
    graph = _infer_interaction_graph(entities)

    # Compute ANDOS layers
    layers = compute_andos_layers(entities, "a", graph)

    # Should have 5 layers: [e], [d], [c], [b], [a]
    assert len(layers) == 5
    assert [e.entity_id for e in layers[0]] == ["e"]  # Periphery
    assert [e.entity_id for e in layers[4]] == ["a"]  # Core

    # Validate layers
    valid, violations = validate_andos_layers(layers, graph)
    assert valid is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
