"""
Unit Tests: Convergence Evaluation Mechanism

Tests the core convergence module components:
- CausalEdge and CausalGraph data structures
- Jaccard similarity calculation (graph_similarity)
- Divergence point detection (find_divergence_points)
- Convergence computation (compute_convergence_from_graphs)
- Grading thresholds and edge cases
"""

import pytest
from typing import List, Set, Tuple

from evaluation.convergence import (
    CausalEdge,
    CausalGraph,
    DivergencePoint,
    ConvergenceResult,
    graph_similarity,
    find_divergence_points,
    compute_convergence_from_graphs,
)


class TestCausalEdge:
    """Unit tests for CausalEdge dataclass."""

    def test_edge_equality(self):
        """Edges with same source, target, type should be equal."""
        e1 = CausalEdge("a", "b", "temporal")
        e2 = CausalEdge("a", "b", "temporal")
        e3 = CausalEdge("a", "b", "knowledge")  # Different type

        assert e1 == e2, "Same edges should be equal"
        assert e1 != e3, "Different types should not be equal"

    def test_edge_hash(self):
        """Edges should be hashable for use in sets."""
        e1 = CausalEdge("a", "b", "temporal")
        e2 = CausalEdge("a", "b", "temporal")

        edge_set = {e1, e2}
        assert len(edge_set) == 1, "Equal edges should hash to same value"

    def test_edge_to_tuple(self):
        """Edge should convert to tuple correctly."""
        e = CausalEdge("src", "tgt", "knowledge", label="info")
        t = e.to_tuple()

        assert t == ("src", "tgt", "knowledge")
        assert len(t) == 3  # Label not included in tuple

    def test_edge_label_optional(self):
        """Label should be optional."""
        e1 = CausalEdge("a", "b", "temporal")
        e2 = CausalEdge("a", "b", "temporal", label="caused by")

        assert e1.label is None
        assert e2.label == "caused by"
        assert e1 == e2  # Label doesn't affect equality


class TestCausalGraph:
    """Unit tests for CausalGraph dataclass."""

    def test_all_edges_property(self):
        """all_edges should combine temporal and knowledge edges."""
        g = CausalGraph(
            run_id="test",
            temporal_edges={("t1", "t2"), ("t2", "t3")},
            knowledge_edges={("e1", "e2")},
        )

        edges = g.all_edges
        assert len(edges) == 3
        assert ("t1", "t2", "temporal") in edges
        assert ("e1", "e2", "knowledge") in edges

    def test_edge_count_property(self):
        """edge_count should be sum of temporal + knowledge edges."""
        g = CausalGraph(
            run_id="test",
            temporal_edges={("a", "b"), ("b", "c")},
            knowledge_edges={("x", "y")},
        )

        assert g.edge_count == 3

    def test_empty_graph(self):
        """Empty graph should have zero edges."""
        g = CausalGraph(run_id="empty")

        assert g.edge_count == 0
        assert len(g.all_edges) == 0

    def test_serialization_roundtrip(self):
        """Graph should survive serialization/deserialization."""
        original = CausalGraph(
            run_id="serialize_test",
            template_id="test_template",
            temporal_edges={("a", "b"), ("b", "c")},
            knowledge_edges={("x", "y")},
            entities={"e1", "e2"},
            timepoints={"t1", "t2"},
            metadata={"key": "value"},
        )

        serialized = original.to_dict()
        restored = CausalGraph.from_dict(serialized)

        assert restored.run_id == original.run_id
        assert restored.template_id == original.template_id
        assert restored.temporal_edges == original.temporal_edges
        assert restored.knowledge_edges == original.knowledge_edges
        assert restored.entities == original.entities
        assert restored.timepoints == original.timepoints
        assert restored.metadata == original.metadata


class TestGraphSimilarity:
    """Unit tests for Jaccard similarity function."""

    def test_identical_graphs_similarity_one(self):
        """Identical graphs should have similarity 1.0."""
        g1 = CausalGraph(run_id="1", temporal_edges={("a", "b")})
        g2 = CausalGraph(run_id="2", temporal_edges={("a", "b")})

        assert graph_similarity(g1, g2) == 1.0

    def test_disjoint_graphs_similarity_zero(self):
        """Disjoint graphs should have similarity 0.0."""
        g1 = CausalGraph(run_id="1", temporal_edges={("a", "b")})
        g2 = CausalGraph(run_id="2", temporal_edges={("c", "d")})

        assert graph_similarity(g1, g2) == 0.0

    def test_empty_graphs_similarity_one(self):
        """Two empty graphs should have similarity 1.0."""
        g1 = CausalGraph(run_id="1")
        g2 = CausalGraph(run_id="2")

        assert graph_similarity(g1, g2) == 1.0

    def test_one_empty_one_not_similarity_zero(self):
        """One empty, one not should have similarity 0.0."""
        g1 = CausalGraph(run_id="1")
        g2 = CausalGraph(run_id="2", temporal_edges={("a", "b")})

        assert graph_similarity(g1, g2) == 0.0

    def test_partial_overlap_similarity(self):
        """Partial overlap should give correct Jaccard value."""
        # g1 has {A, B}, g2 has {A, C}
        # Jaccard = |{A}| / |{A, B, C}| = 1/3
        g1 = CausalGraph(
            run_id="1",
            temporal_edges={("a", "b"), ("b", "c")},
        )
        g2 = CausalGraph(
            run_id="2",
            temporal_edges={("a", "b"), ("c", "d")},
        )

        sim = graph_similarity(g1, g2)
        assert abs(sim - 1/3) < 0.01, f"Expected ~0.33, got {sim}"

    def test_fifty_percent_overlap(self):
        """50% overlap should give Jaccard = 1/3."""
        # g1 has {A, B}, g2 has {B, C}
        # Intersection = {B}, Union = {A, B, C}
        # Jaccard = 1/3
        g1 = CausalGraph(
            run_id="1",
            temporal_edges={("1", "2"), ("2", "3")},
        )
        g2 = CausalGraph(
            run_id="2",
            temporal_edges={("2", "3"), ("3", "4")},
        )

        sim = graph_similarity(g1, g2)
        assert abs(sim - 1/3) < 0.01

    def test_mixed_edge_types(self):
        """Similarity should consider both temporal and knowledge edges."""
        g1 = CausalGraph(
            run_id="1",
            temporal_edges={("t1", "t2")},
            knowledge_edges={("e1", "e2")},
        )
        g2 = CausalGraph(
            run_id="2",
            temporal_edges={("t1", "t2")},
            knowledge_edges={("e3", "e4")},  # Different knowledge edge
        )

        # 1 shared (temporal), 3 total
        sim = graph_similarity(g1, g2)
        assert abs(sim - 1/3) < 0.01


class TestFindDivergencePoints:
    """Unit tests for divergence point detection."""

    def test_no_divergence_identical_graphs(self):
        """Identical graphs should have no divergence points."""
        edges = {("a", "b"), ("b", "c")}
        graphs = [
            CausalGraph(run_id=f"r{i}", temporal_edges=edges)
            for i in range(3)
        ]

        divergence = find_divergence_points(graphs)
        assert len(divergence) == 0

    def test_all_different_all_contested(self):
        """Graphs with no overlap should have all edges contested."""
        g1 = CausalGraph(run_id="1", temporal_edges={("a", "b")})
        g2 = CausalGraph(run_id="2", temporal_edges={("c", "d")})

        divergence = find_divergence_points([g1, g2])

        # Each edge appears in only 1 of 2 graphs = 50% agreement
        assert len(divergence) == 2
        for dp in divergence:
            assert dp.agreement_ratio == 0.5

    def test_divergence_sorted_by_ratio(self):
        """Divergence points should be sorted by agreement ratio (ascending)."""
        g1 = CausalGraph(run_id="1", temporal_edges={("a", "b"), ("b", "c"), ("c", "d")})
        g2 = CausalGraph(run_id="2", temporal_edges={("a", "b"), ("b", "c")})
        g3 = CausalGraph(run_id="3", temporal_edges={("a", "b")})

        divergence = find_divergence_points([g1, g2, g3])

        # (c,d) in 1/3, (b,c) in 2/3 - sorted ascending
        ratios = [dp.agreement_ratio for dp in divergence]
        assert ratios == sorted(ratios)

    def test_single_graph_no_divergence(self):
        """Single graph should return empty divergence list."""
        g = CausalGraph(run_id="1", temporal_edges={("a", "b")})

        divergence = find_divergence_points([g])
        assert len(divergence) == 0

    def test_divergence_point_metadata(self):
        """Divergence points should track which runs have each edge."""
        g1 = CausalGraph(run_id="run_a", temporal_edges={("x", "y")})
        g2 = CausalGraph(run_id="run_b", temporal_edges=set())

        divergence = find_divergence_points([g1, g2])

        assert len(divergence) == 1
        dp = divergence[0]
        assert "run_a" in dp.present_in_runs
        assert "run_b" in dp.absent_in_runs
        assert dp.agreement_ratio == 0.5


class TestComputeConvergence:
    """Unit tests for compute_convergence_from_graphs."""

    def test_minimum_two_graphs_required(self):
        """Should raise error with fewer than 2 graphs."""
        g = CausalGraph(run_id="1")

        with pytest.raises(ValueError, match="at least 2"):
            compute_convergence_from_graphs([g])

    def test_perfect_convergence(self):
        """Identical graphs should yield perfect convergence."""
        graphs = [
            CausalGraph(run_id=f"r{i}", temporal_edges={("a", "b"), ("b", "c")})
            for i in range(3)
        ]

        result = compute_convergence_from_graphs(graphs)

        assert result.convergence_score == 1.0
        assert result.min_similarity == 1.0
        assert result.max_similarity == 1.0
        assert result.robustness_grade == "A"
        assert result.run_count == 3

    def test_zero_convergence(self):
        """Completely disjoint graphs should yield zero convergence."""
        graphs = [
            CausalGraph(run_id="1", temporal_edges={("a", "b")}),
            CausalGraph(run_id="2", temporal_edges={("c", "d")}),
        ]

        result = compute_convergence_from_graphs(graphs)

        assert result.convergence_score == 0.0
        assert result.robustness_grade == "F"

    def test_consensus_vs_contested_edges(self):
        """Should correctly partition consensus and contested edges."""
        # Edge A in all 3, Edge B in 2, Edge C in 1
        g1 = CausalGraph(run_id="1", temporal_edges={("a", "b"), ("b", "c"), ("c", "d")})
        g2 = CausalGraph(run_id="2", temporal_edges={("a", "b"), ("b", "c")})
        g3 = CausalGraph(run_id="3", temporal_edges={("a", "b")})

        result = compute_convergence_from_graphs([g1, g2, g3])

        # (a,b) should be consensus
        assert ("a", "b", "temporal") in result.consensus_edges
        # (b,c) and (c,d) should be contested
        assert ("b", "c", "temporal") in result.contested_edges
        assert ("c", "d", "temporal") in result.contested_edges

    def test_template_id_propagation(self):
        """Template ID should be taken from first graph."""
        graphs = [
            CausalGraph(run_id="1", template_id="my_template"),
            CausalGraph(run_id="2", template_id="my_template"),
        ]

        result = compute_convergence_from_graphs(graphs)
        assert result.template_id == "my_template"

    def test_run_ids_preserved(self):
        """All run IDs should be preserved in result."""
        run_ids = ["run_alpha", "run_beta", "run_gamma"]
        graphs = [CausalGraph(run_id=rid) for rid in run_ids]

        result = compute_convergence_from_graphs(graphs)
        assert result.run_ids == run_ids


class TestRobustnessGrades:
    """Unit tests for grading thresholds."""

    @pytest.mark.parametrize("score,expected_grade", [
        (1.0, "A"),
        (0.95, "A"),
        (0.90, "A"),
        (0.89, "B"),
        (0.85, "B"),
        (0.80, "B"),
        (0.79, "C"),
        (0.75, "C"),
        (0.70, "C"),
        (0.69, "D"),
        (0.60, "D"),
        (0.50, "D"),
        (0.49, "F"),
        (0.25, "F"),
        (0.0, "F"),
    ])
    def test_grade_thresholds(self, score, expected_grade):
        """Test all grade threshold boundaries."""
        result = ConvergenceResult(
            run_ids=["r1", "r2"],
            template_id="test",
            mean_similarity=score,
            min_similarity=score,
            max_similarity=score,
            divergence_points=[],
            consensus_edges=set(),
            contested_edges=set(),
        )

        assert result.robustness_grade == expected_grade, \
            f"Score {score} should get grade {expected_grade}, got {result.robustness_grade}"


class TestConvergenceResultSerialization:
    """Unit tests for ConvergenceResult serialization."""

    def test_to_dict_includes_all_fields(self):
        """Serialization should include all fields."""
        result = ConvergenceResult(
            run_ids=["r1", "r2"],
            template_id="test",
            mean_similarity=0.85,
            min_similarity=0.80,
            max_similarity=0.90,
            divergence_points=[],
            consensus_edges={("a", "b", "temporal")},
            contested_edges={("c", "d", "knowledge")},
        )

        d = result.to_dict()

        expected_keys = {
            "run_ids", "template_id", "mean_similarity", "min_similarity",
            "max_similarity", "convergence_score", "robustness_grade",
            "divergence_points", "consensus_edges", "contested_edges",
            "computed_at", "run_count"
        }
        assert set(d.keys()) == expected_keys

    def test_divergence_points_serialization(self):
        """Divergence points should serialize correctly."""
        result = ConvergenceResult(
            run_ids=["r1", "r2"],
            template_id="test",
            mean_similarity=0.5,
            min_similarity=0.5,
            max_similarity=0.5,
            divergence_points=[
                DivergencePoint(
                    edge=("x", "y", "temporal"),
                    present_in_runs=["r1"],
                    absent_in_runs=["r2"],
                    agreement_ratio=0.5,
                )
            ],
            consensus_edges=set(),
            contested_edges=set(),
        )

        d = result.to_dict()
        dp = d["divergence_points"][0]

        assert dp["edge"] == ("x", "y", "temporal")
        assert dp["present_in_runs"] == ["r1"]
        assert dp["absent_in_runs"] == ["r2"]
        assert dp["agreement_ratio"] == 0.5


if __name__ == "__main__":
    import sys
    pytest_args = [__file__, "-v"]
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)
