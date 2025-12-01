"""
Unit tests for convergence analysis functions.

Tests the core convergence utilities:
- normalize_timepoint_id: Strips run_id prefix for cross-run comparison
- graph_similarity: Jaccard similarity between causal graphs
- CausalGraph: Data structure for causal relationships
"""

import pytest
from evaluation.convergence import (
    normalize_timepoint_id,
    graph_similarity,
    CausalGraph,
    find_divergence_points,
    compute_convergence_from_graphs,
)


class TestNormalizeTimepointId:
    """Tests for normalize_timepoint_id function."""

    def test_strips_run_id_prefix(self):
        """Should strip run_id prefix from timepoint_id."""
        run_id = "run_20251129_185541_c6f3cb0f"
        tp_id = "run_20251129_185541_c6f3cb0f_tp_001_opening"

        result = normalize_timepoint_id(tp_id, run_id)

        assert result == "tp_001_opening"

    def test_preserves_id_without_prefix(self):
        """Should preserve timepoint_id if it doesn't have run_id prefix."""
        run_id = "run_20251129_185541_c6f3cb0f"
        tp_id = "tp_001_opening"

        result = normalize_timepoint_id(tp_id, run_id)

        assert result == "tp_001_opening"

    def test_handles_different_run_id(self):
        """Should not strip if run_id doesn't match."""
        run_id = "run_20251129_185541_c6f3cb0f"
        tp_id = "run_20251129_190211_be027577_tp_001_opening"

        result = normalize_timepoint_id(tp_id, run_id)

        # Should NOT strip because prefix doesn't match
        assert result == "run_20251129_190211_be027577_tp_001_opening"

    def test_handles_empty_timepoint_id(self):
        """Should handle empty timepoint_id gracefully."""
        run_id = "run_123"
        tp_id = ""

        result = normalize_timepoint_id(tp_id, run_id)

        assert result == ""

    def test_handles_empty_run_id(self):
        """Should handle empty run_id gracefully."""
        run_id = ""
        tp_id = "tp_001_opening"

        result = normalize_timepoint_id(tp_id, run_id)

        # Empty run_id means prefix is "_", which doesn't match
        assert result == "tp_001_opening"

    def test_handles_partial_prefix_match(self):
        """Should not strip if only partial prefix matches."""
        run_id = "run_20251129"
        tp_id = "run_20251129_185541_c6f3cb0f_tp_001"

        result = normalize_timepoint_id(tp_id, run_id)

        # Should strip "run_20251129_" prefix
        assert result == "185541_c6f3cb0f_tp_001"

    def test_complex_timepoint_id(self):
        """Should handle complex timepoint IDs with multiple underscores."""
        run_id = "run_20251129_185541_c6f3cb0f"
        tp_id = "run_20251129_185541_c6f3cb0f_tp_002_midpoint_action"

        result = normalize_timepoint_id(tp_id, run_id)

        assert result == "tp_002_midpoint_action"


class TestGraphSimilarity:
    """Tests for graph_similarity function."""

    def test_identical_graphs(self):
        """Identical graphs should have similarity of 1.0."""
        g1 = CausalGraph(
            run_id="run_1",
            temporal_edges={("a", "b"), ("b", "c")},
        )
        g2 = CausalGraph(
            run_id="run_2",
            temporal_edges={("a", "b"), ("b", "c")},
        )

        assert graph_similarity(g1, g2) == 1.0

    def test_disjoint_graphs(self):
        """Completely disjoint graphs should have similarity of 0.0."""
        g1 = CausalGraph(
            run_id="run_1",
            temporal_edges={("a", "b")},
        )
        g2 = CausalGraph(
            run_id="run_2",
            temporal_edges={("c", "d")},
        )

        assert graph_similarity(g1, g2) == 0.0

    def test_partial_overlap(self):
        """Graphs with partial overlap should have intermediate similarity."""
        g1 = CausalGraph(
            run_id="run_1",
            temporal_edges={("a", "b"), ("b", "c")},
        )
        g2 = CausalGraph(
            run_id="run_2",
            temporal_edges={("a", "b"), ("c", "d")},
        )

        # Intersection: {("a", "b")} = 1 edge
        # Union: {("a", "b"), ("b", "c"), ("c", "d")} = 3 edges
        # Jaccard = 1/3
        similarity = graph_similarity(g1, g2)
        assert abs(similarity - 1/3) < 0.01

    def test_both_empty_graphs(self):
        """Two empty graphs should have similarity of 1.0."""
        g1 = CausalGraph(run_id="run_1")
        g2 = CausalGraph(run_id="run_2")

        assert graph_similarity(g1, g2) == 1.0

    def test_one_empty_graph(self):
        """One empty graph vs non-empty should have similarity of 0.0."""
        g1 = CausalGraph(run_id="run_1")
        g2 = CausalGraph(
            run_id="run_2",
            temporal_edges={("a", "b")},
        )

        assert graph_similarity(g1, g2) == 0.0

    def test_knowledge_edges_included(self):
        """Similarity should include knowledge edges."""
        g1 = CausalGraph(
            run_id="run_1",
            knowledge_edges={("alice", "bob")},
        )
        g2 = CausalGraph(
            run_id="run_2",
            knowledge_edges={("alice", "bob")},
        )

        assert graph_similarity(g1, g2) == 1.0

    def test_mixed_temporal_and_knowledge(self):
        """Similarity should work with mixed edge types."""
        g1 = CausalGraph(
            run_id="run_1",
            temporal_edges={("tp1", "tp2")},
            knowledge_edges={("alice", "bob")},
        )
        g2 = CausalGraph(
            run_id="run_2",
            temporal_edges={("tp1", "tp2")},
            knowledge_edges={("alice", "charlie")},  # Different
        )

        # Intersection: temporal edge only (knowledge edges are tuples, need to count as edges in all_edges)
        # g1.all_edges = {("tp1", "tp2", "temporal"), ("alice", "bob", "knowledge")}
        # g2.all_edges = {("tp1", "tp2", "temporal"), ("alice", "charlie", "knowledge")}
        # Intersection = {("tp1", "tp2", "temporal")} = 1
        # Union = 3 edges
        similarity = graph_similarity(g1, g2)
        assert abs(similarity - 1/3) < 0.01


class TestCausalGraph:
    """Tests for CausalGraph data structure."""

    def test_all_edges_combines_temporal_and_knowledge(self):
        """all_edges should return union of temporal and knowledge edges with type."""
        g = CausalGraph(
            run_id="test",
            temporal_edges={("tp1", "tp2")},
            knowledge_edges={("alice", "bob")},
        )

        all_edges = g.all_edges

        assert ("tp1", "tp2", "temporal") in all_edges
        assert ("alice", "bob", "knowledge") in all_edges
        assert len(all_edges) == 2

    def test_edge_count(self):
        """edge_count should return total number of edges."""
        g = CausalGraph(
            run_id="test",
            temporal_edges={("a", "b"), ("b", "c")},
            knowledge_edges={("x", "y")},
        )

        assert g.edge_count == 3

    def test_to_dict_round_trip(self):
        """to_dict and from_dict should round-trip correctly."""
        original = CausalGraph(
            run_id="run_123",
            template_id="template_abc",
            temporal_edges={("a", "b")},
            knowledge_edges={("x", "y")},
            entities={"alice", "bob"},
            timepoints={"tp1", "tp2"},
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = CausalGraph.from_dict(data)

        assert restored.run_id == original.run_id
        assert restored.template_id == original.template_id
        assert restored.temporal_edges == original.temporal_edges
        assert restored.knowledge_edges == original.knowledge_edges


class TestFindDivergencePoints:
    """Tests for find_divergence_points function."""

    def test_no_divergence_with_identical_graphs(self):
        """Identical graphs should have no divergence points."""
        graphs = [
            CausalGraph(run_id="run_1", temporal_edges={("a", "b")}),
            CausalGraph(run_id="run_2", temporal_edges={("a", "b")}),
        ]

        divergence = find_divergence_points(graphs)

        assert len(divergence) == 0

    def test_finds_contested_edges(self):
        """Should identify edges present in some but not all graphs."""
        graphs = [
            CausalGraph(run_id="run_1", temporal_edges={("a", "b"), ("b", "c")}),
            CausalGraph(run_id="run_2", temporal_edges={("a", "b")}),  # Missing (b, c)
        ]

        divergence = find_divergence_points(graphs)

        assert len(divergence) == 1
        assert divergence[0].edge == ("b", "c", "temporal")
        assert divergence[0].agreement_ratio == 0.5

    def test_single_graph_returns_empty(self):
        """Single graph should return no divergence."""
        graphs = [CausalGraph(run_id="run_1", temporal_edges={("a", "b")})]

        divergence = find_divergence_points(graphs)

        assert len(divergence) == 0


class TestComputeConvergenceFromGraphs:
    """Tests for compute_convergence_from_graphs function."""

    def test_perfect_convergence(self):
        """Identical graphs should have 100% convergence."""
        graphs = [
            CausalGraph(run_id="run_1", temporal_edges={("a", "b"), ("b", "c")}),
            CausalGraph(run_id="run_2", temporal_edges={("a", "b"), ("b", "c")}),
            CausalGraph(run_id="run_3", temporal_edges={("a", "b"), ("b", "c")}),
        ]

        result = compute_convergence_from_graphs(graphs)

        assert result.convergence_score == 1.0
        assert result.robustness_grade == "A"
        assert len(result.consensus_edges) == 2
        assert len(result.contested_edges) == 0

    def test_partial_convergence(self):
        """Graphs with some overlap should have partial convergence."""
        graphs = [
            CausalGraph(run_id="run_1", temporal_edges={("a", "b"), ("b", "c")}),
            CausalGraph(run_id="run_2", temporal_edges={("a", "b"), ("c", "d")}),
        ]

        result = compute_convergence_from_graphs(graphs)

        # Jaccard = 1/3
        assert abs(result.convergence_score - 1/3) < 0.01
        assert result.robustness_grade == "F"  # < 0.5

    def test_requires_at_least_two_graphs(self):
        """Should raise error with less than 2 graphs."""
        with pytest.raises(ValueError, match="at least 2"):
            compute_convergence_from_graphs([CausalGraph(run_id="run_1")])

    def test_tracks_run_count(self):
        """Should track number of runs analyzed."""
        graphs = [
            CausalGraph(run_id="run_1"),
            CausalGraph(run_id="run_2"),
            CausalGraph(run_id="run_3"),
        ]

        result = compute_convergence_from_graphs(graphs)

        assert result.run_count == 3
        assert result.run_ids == ["run_1", "run_2", "run_3"]
