"""
Unit tests for ANDOS layer computation algorithm.

Tests cover:
- Simple chain graphs
- Branching graphs
- Cycle detection
- Disconnected entities
- Single entity edge cases
- Real detective_prospection graph structure
"""

import pytest
import networkx as nx
from andos.layer_computer import (
    build_interaction_graph,
    compute_entity_distances,
    group_by_distance,
    compute_andos_layers,
    validate_andos_layers
)


# Test entity mock class
class MockEntity:
    """Mock entity for testing"""
    def __init__(self, entity_id: str):
        self.entity_id = entity_id

    def __repr__(self):
        return f"Entity({self.entity_id})"


def make_entity(entity_id: str) -> MockEntity:
    """Helper to create test entity"""
    return MockEntity(entity_id)


# ============================================================================
# Test: build_interaction_graph()
# ============================================================================

def test_build_graph_simple():
    """Build graph from simple interaction config"""
    config = {
        "interactions": [
            {"from": "A", "to": "B"}
        ]
    }

    G = build_interaction_graph(config)

    assert G.number_of_nodes() == 2
    assert G.number_of_edges() == 1
    assert G.has_edge("A", "B")


def test_build_graph_multiple_targets():
    """Build graph with multiple targets per interaction"""
    config = {
        "interactions": [
            {"from": "A", "to": ["B", "C"]}
        ]
    }

    G = build_interaction_graph(config)

    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2
    assert G.has_edge("A", "B")
    assert G.has_edge("A", "C")


def test_build_graph_empty():
    """Build graph with no interactions"""
    config = {"interactions": []}

    G = build_interaction_graph(config)

    assert G.number_of_nodes() == 0
    assert G.number_of_edges() == 0


# ============================================================================
# Test: compute_entity_distances()
# ============================================================================

def test_compute_distances_chain():
    """Compute distances in simple chain A → B → C"""
    G = nx.DiGraph([("A", "B"), ("B", "C")])

    distances = compute_entity_distances(G, "A")

    assert distances == {"A": 0, "B": 1, "C": 2}


def test_compute_distances_branching():
    """Compute distances in branching graph A → B,C"""
    G = nx.DiGraph([("A", "B"), ("A", "C")])

    distances = compute_entity_distances(G, "A")

    assert distances == {"A": 0, "B": 1, "C": 1}


def test_compute_distances_target_not_found():
    """Raise error if target not in graph"""
    G = nx.DiGraph([("A", "B")])

    with pytest.raises(nx.NodeNotFound, match="Target entity 'Z'"):
        compute_entity_distances(G, "Z")


# ============================================================================
# Test: group_by_distance()
# ============================================================================

def test_group_by_distance_chain():
    """Group entities by distance in chain"""
    entity_ids = ["A", "B", "C"]
    distances = {"A": 0, "B": 1, "C": 2}

    layers = group_by_distance(entity_ids, distances)

    # Expect: [[C], [B], [A]] (periphery to core)
    assert len(layers) == 3
    assert layers[0] == ["C"]  # Periphery (max distance)
    assert layers[1] == ["B"]
    assert layers[2] == ["A"]  # Core (distance 0)


def test_group_by_distance_with_orphan():
    """Group entities including one not in distance map"""
    entity_ids = ["A", "B", "C", "orphan"]
    distances = {"A": 0, "B": 1, "C": 2}

    layers = group_by_distance(entity_ids, distances)

    # Orphan should be in periphery layer with C
    assert len(layers) == 3
    assert set(layers[0]) == {"C", "orphan"}  # Periphery
    assert layers[1] == ["B"]
    assert layers[2] == ["A"]  # Core


def test_group_by_distance_empty():
    """Handle empty distances gracefully"""
    entity_ids = ["A", "B"]
    distances = {}

    layers = group_by_distance(entity_ids, distances)

    # All entities in one layer
    assert len(layers) == 1
    assert set(layers[0]) == {"A", "B"}


# ============================================================================
# Test: compute_andos_layers() - Main Algorithm
# ============================================================================

def test_simple_chain():
    """A → B → C should give layers [[C], [B], [A]]"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 3
    assert [e.entity_id for e in layers[0]] == ["C"]  # Periphery (seed)
    assert [e.entity_id for e in layers[1]] == ["B"]
    assert [e.entity_id for e in layers[2]] == ["A"]  # Core (target)


def test_branching():
    """A → B,C; B → D; C → E should give [[D,E], [B,C], [A]]"""
    entities = [
        make_entity("A"), make_entity("B"), make_entity("C"),
        make_entity("D"), make_entity("E")
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B", "C"]},
            {"from": "B", "to": "D"},
            {"from": "C", "to": "E"}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 3
    assert set(e.entity_id for e in layers[0]) == {"D", "E"}  # Periphery
    assert set(e.entity_id for e in layers[1]) == {"B", "C"}
    assert set(e.entity_id for e in layers[2]) == {"A"}  # Core


def test_cycle_detection():
    """A → B → C → A should raise ValueError"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "A"}  # Creates cycle
        ]
    }

    with pytest.raises(ValueError, match="contains.*cycle"):
        compute_andos_layers(entities, "A", graph)


def test_disconnected_entity():
    """Entity not in graph should be added to periphery"""
    entities = [
        make_entity("A"), make_entity("B"), make_entity("C"), make_entity("orphan")
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    # Orphan should be in periphery layer with C
    periphery_ids = [e.entity_id for e in layers[0]]
    assert "orphan" in periphery_ids
    assert "C" in periphery_ids


def test_single_entity():
    """Single entity should create single layer"""
    entities = [make_entity("A")]
    graph = {"interactions": []}

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 1
    assert layers[0][0].entity_id == "A"


def test_two_entity_interaction():
    """Two entities with one interaction"""
    entities = [make_entity("A"), make_entity("B")]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"}
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    assert len(layers) == 2
    assert [e.entity_id for e in layers[0]] == ["B"]  # Periphery
    assert [e.entity_id for e in layers[1]] == ["A"]  # Core


# ============================================================================
# Test: detective_prospection Graph Structure
# ============================================================================

def test_detective_prospection_structure():
    """Test real detective_prospection template structure"""
    entities = [
        make_entity("sherlock_holmes"),
        make_entity("watson"),
        make_entity("lestrade"),
        make_entity("mrs_hudson"),
        make_entity("stamford"),
        make_entity("street_vendor_1"),
        make_entity("street_vendor_2")
    ]

    graph = {
        "interactions": [
            {"from": "sherlock_holmes", "to": ["watson", "lestrade"]},
            {"from": "watson", "to": ["mrs_hudson", "stamford"]},
            {"from": "mrs_hudson", "to": ["street_vendor_1", "street_vendor_2"]}
        ]
    }

    layers = compute_andos_layers(entities, "sherlock_holmes", graph)

    # Should have 4 layers (stamford and lestrade are separate from main chain)
    assert len(layers) >= 3  # At least 3, possibly 4 depending on structure

    # Layer 0 (periphery): street vendors
    periphery_ids = set(e.entity_id for e in layers[0])
    assert "street_vendor_1" in periphery_ids
    assert "street_vendor_2" in periphery_ids

    # Verify sherlock_holmes is in final layer (core)
    core_ids = [e.entity_id for e in layers[-1]]
    assert "sherlock_holmes" in core_ids

    # Verify watson and mrs_hudson are in middle layers
    all_middle_ids = set()
    for layer in layers[1:-1]:
        all_middle_ids.update(e.entity_id for e in layer)
    assert "watson" in all_middle_ids
    assert "mrs_hudson" in all_middle_ids


# ============================================================================
# Test: validate_andos_layers()
# ============================================================================

def test_validate_correct_layers():
    """Validate correctly ordered layers"""
    layers = [
        [make_entity("C")],
        [make_entity("B")],
        [make_entity("A")]
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"}
        ]
    }

    valid, violations = validate_andos_layers(layers, graph)

    assert valid is True
    assert len(violations) == 0


def test_validate_incorrect_layers():
    """Detect incorrect layer ordering"""
    layers = [
        [make_entity("A")],  # Should be last, not first
        [make_entity("B")],
        [make_entity("C")]
    ]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"}
        ]
    }

    valid, violations = validate_andos_layers(layers, graph)

    assert valid is False
    assert len(violations) > 0
    assert "A" in violations[0]
    assert "B" in violations[0]


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_pipeline_simple():
    """Test complete ANDOS pipeline with simple graph"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"}
        ]
    }

    # Compute layers
    layers = compute_andos_layers(entities, "A", graph)

    # Validate layers
    valid, violations = validate_andos_layers(layers, graph)

    assert valid is True
    assert len(layers) == 3
    assert [e.entity_id for e in layers[0]] == ["C"]
    assert [e.entity_id for e in layers[1]] == ["B"]
    assert [e.entity_id for e in layers[2]] == ["A"]


def test_full_pipeline_detective():
    """Test complete ANDOS pipeline with detective_prospection graph"""
    entities = [
        make_entity("sherlock_holmes"),
        make_entity("watson"),
        make_entity("lestrade"),
        make_entity("mrs_hudson"),
        make_entity("stamford"),
        make_entity("street_vendor_1"),
        make_entity("street_vendor_2")
    ]

    graph = {
        "interactions": [
            {"from": "sherlock_holmes", "to": ["watson", "lestrade"]},
            {"from": "watson", "to": ["mrs_hudson", "stamford"]},
            {"from": "mrs_hudson", "to": ["street_vendor_1", "street_vendor_2"]}
        ]
    }

    # Compute layers
    layers = compute_andos_layers(entities, "sherlock_holmes", graph)

    # Validate layers
    valid, violations = validate_andos_layers(layers, graph)

    assert valid is True
    assert len(layers) >= 3  # At least 3 layers, possibly 4

    # Verify sherlock_holmes is in final layer
    final_layer_ids = [e.entity_id for e in layers[-1]]
    assert "sherlock_holmes" in final_layer_ids


# ============================================================================
# Edge Cases
# ============================================================================

def test_fully_connected_graph():
    """Test graph where everyone talks to everyone"""
    entities = [make_entity("A"), make_entity("B"), make_entity("C")]
    graph = {
        "interactions": [
            {"from": "A", "to": ["B", "C"]},
            {"from": "B", "to": ["A", "C"]},
            {"from": "C", "to": ["A", "B"]}
        ]
    }

    # This creates cycles - should raise ValueError
    with pytest.raises(ValueError, match="cycle"):
        compute_andos_layers(entities, "A", graph)


def test_star_graph():
    """Test star graph where one entity talks to all others"""
    entities = [make_entity("center")] + [make_entity(f"spoke_{i}") for i in range(5)]
    graph = {
        "interactions": [
            {"from": "center", "to": [f"spoke_{i}" for i in range(5)]}
        ]
    }

    layers = compute_andos_layers(entities, "center", graph)

    # Should have 2 layers: all spokes, then center
    assert len(layers) == 2
    assert len(layers[0]) == 5  # All spokes in periphery
    assert layers[1][0].entity_id == "center"  # Center is core


def test_linear_chain_long():
    """Test long linear chain A → B → C → D → E → F"""
    n = 6
    entities = [make_entity(chr(65 + i)) for i in range(n)]  # A, B, C, D, E, F
    graph = {
        "interactions": [
            {"from": chr(65 + i), "to": chr(65 + i + 1)}
            for i in range(n - 1)
        ]
    }

    layers = compute_andos_layers(entities, "A", graph)

    # Should have n layers, one entity per layer
    assert len(layers) == n
    assert [e.entity_id for e in layers[0]] == ["F"]  # Furthest from A
    assert [e.entity_id for e in layers[-1]] == ["A"]  # Target


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
