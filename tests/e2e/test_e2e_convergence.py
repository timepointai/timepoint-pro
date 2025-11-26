"""
E2E Test: Convergence Evaluation Pipeline

Tests the complete convergence evaluation system:
- CausalGraph extraction from simulation runs
- Jaccard similarity calculation between graphs
- Convergence scoring and robustness grading (A-F)
- Divergence point detection
- Storage and retrieval of ConvergenceSet objects
"""

import pytest
import tempfile
import shutil
import os
from datetime import datetime
from typing import List

from evaluation.convergence import (
    CausalGraph,
    CausalEdge,
    DivergencePoint,
    ConvergenceResult,
    graph_similarity,
    find_divergence_points,
    compute_convergence_from_graphs,
)
from schemas import ConvergenceSet
from storage import GraphStore


@pytest.mark.e2e
class TestConvergenceE2EPipeline:
    """E2E tests for convergence evaluation pipeline."""

    def setup_method(self):
        """Setup test environment with temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_convergence.db")
        self.store = GraphStore(f"sqlite:///{self.db_path}")

    def teardown_method(self):
        """Cleanup test environment."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _create_sample_graph(
        self,
        run_id: str,
        template_id: str = "test_template",
        temporal_edges: List[tuple] = None,
        knowledge_edges: List[tuple] = None,
    ) -> CausalGraph:
        """Helper to create sample causal graphs for testing."""
        return CausalGraph(
            run_id=run_id,
            template_id=template_id,
            temporal_edges=set(temporal_edges or []),
            knowledge_edges=set(knowledge_edges or []),
            entities={"e1", "e2", "e3"},
            timepoints={"t1", "t2", "t3"},
        )

    def test_identical_graphs_perfect_convergence(self):
        """Identical graphs should have 100% convergence (grade A)."""
        print("\n" + "=" * 70)
        print("TEST: Identical Graphs → Perfect Convergence")
        print("=" * 70)

        # Create identical graphs
        edges = [("t1", "t2"), ("t2", "t3")]
        knowledge = [("e1", "e2"), ("e2", "e3")]

        g1 = self._create_sample_graph("run_1", temporal_edges=edges, knowledge_edges=knowledge)
        g2 = self._create_sample_graph("run_2", temporal_edges=edges, knowledge_edges=knowledge)
        g3 = self._create_sample_graph("run_3", temporal_edges=edges, knowledge_edges=knowledge)

        result = compute_convergence_from_graphs([g1, g2, g3])

        print(f"\nResults:")
        print(f"  Convergence Score: {result.convergence_score:.1%}")
        print(f"  Robustness Grade: {result.robustness_grade}")
        print(f"  Consensus Edges: {len(result.consensus_edges)}")
        print(f"  Contested Edges: {len(result.contested_edges)}")

        assert result.convergence_score == 1.0, "Identical graphs should have perfect convergence"
        assert result.robustness_grade == "A", "Perfect convergence should get grade A"
        assert len(result.contested_edges) == 0, "No edges should be contested"
        assert len(result.divergence_points) == 0, "No divergence points for identical graphs"

        print("\n✅ PASSED: Identical graphs yield perfect convergence")

    def test_disjoint_graphs_zero_convergence(self):
        """Completely different graphs should have 0% convergence (grade F)."""
        print("\n" + "=" * 70)
        print("TEST: Disjoint Graphs → Zero Convergence")
        print("=" * 70)

        # Create completely different graphs
        g1 = self._create_sample_graph("run_1", temporal_edges=[("t1", "t2")])
        g2 = self._create_sample_graph("run_2", temporal_edges=[("t3", "t4")])

        result = compute_convergence_from_graphs([g1, g2])

        print(f"\nResults:")
        print(f"  Convergence Score: {result.convergence_score:.1%}")
        print(f"  Robustness Grade: {result.robustness_grade}")
        print(f"  Consensus Edges: {len(result.consensus_edges)}")
        print(f"  Contested Edges: {len(result.contested_edges)}")

        assert result.convergence_score == 0.0, "Disjoint graphs should have zero convergence"
        assert result.robustness_grade == "F", "Zero convergence should get grade F"
        assert len(result.consensus_edges) == 0, "No consensus edges for disjoint graphs"

        print("\n✅ PASSED: Disjoint graphs yield zero convergence")

    def test_partial_overlap_moderate_convergence(self):
        """Partially overlapping graphs should have moderate convergence."""
        print("\n" + "=" * 70)
        print("TEST: Partial Overlap → Moderate Convergence")
        print("=" * 70)

        # Create graphs with 50% overlap
        # g1 has edges A, B
        # g2 has edges A, C
        # Jaccard = |{A}| / |{A,B,C}| = 1/3 ≈ 0.33

        g1 = self._create_sample_graph(
            "run_1",
            temporal_edges=[("t1", "t2"), ("t2", "t3")],
        )
        g2 = self._create_sample_graph(
            "run_2",
            temporal_edges=[("t1", "t2"), ("t3", "t4")],
        )

        result = compute_convergence_from_graphs([g1, g2])

        print(f"\nResults:")
        print(f"  Convergence Score: {result.convergence_score:.1%}")
        print(f"  Robustness Grade: {result.robustness_grade}")
        print(f"  Divergence Points: {len(result.divergence_points)}")

        # Should be around 33% (1 shared / 3 total edges)
        assert 0.2 < result.convergence_score < 0.5, f"Expected moderate convergence, got {result.convergence_score}"
        assert result.robustness_grade in ["D", "F"], "Low convergence should get grade D or F"
        assert len(result.divergence_points) > 0, "Should have divergence points"

        print("\n✅ PASSED: Partial overlap yields moderate convergence")

    def test_grading_thresholds(self):
        """Test that grading thresholds work correctly."""
        print("\n" + "=" * 70)
        print("TEST: Grading Thresholds")
        print("=" * 70)

        # Test each grade threshold
        test_cases = [
            (0.95, "A"),
            (0.90, "A"),
            (0.85, "B"),
            (0.80, "B"),
            (0.75, "C"),
            (0.70, "C"),
            (0.60, "D"),
            (0.50, "D"),
            (0.40, "F"),
            (0.0, "F"),
        ]

        for score, expected_grade in test_cases:
            # Create mock result
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

            actual_grade = result.robustness_grade
            assert actual_grade == expected_grade, \
                f"Score {score} should get grade {expected_grade}, got {actual_grade}"
            print(f"  Score {score:.0%} → Grade {actual_grade} ✓")

        print("\n✅ PASSED: All grading thresholds work correctly")

    def test_divergence_point_detection(self):
        """Test that divergence points are correctly identified."""
        print("\n" + "=" * 70)
        print("TEST: Divergence Point Detection")
        print("=" * 70)

        # Create 3 graphs with specific disagreements
        # Edge A: in all 3 (consensus)
        # Edge B: in 2 of 3 (contested, 67% agreement)
        # Edge C: in 1 of 3 (contested, 33% agreement)

        g1 = self._create_sample_graph(
            "run_1",
            temporal_edges=[("t1", "t2"), ("t2", "t3"), ("t3", "t4")],
        )
        g2 = self._create_sample_graph(
            "run_2",
            temporal_edges=[("t1", "t2"), ("t2", "t3")],
        )
        g3 = self._create_sample_graph(
            "run_3",
            temporal_edges=[("t1", "t2")],
        )

        divergence = find_divergence_points([g1, g2, g3])

        print(f"\nDivergence Points Found: {len(divergence)}")
        for dp in divergence:
            print(f"  Edge {dp.edge}: {dp.agreement_ratio:.0%} agreement")
            print(f"    Present in: {dp.present_in_runs}")
            print(f"    Absent in: {dp.absent_in_runs}")

        assert len(divergence) == 2, f"Should find 2 contested edges, found {len(divergence)}"

        # Verify sorted by agreement (lowest first)
        ratios = [dp.agreement_ratio for dp in divergence]
        assert ratios == sorted(ratios), "Divergence points should be sorted by agreement ratio"

        print("\n✅ PASSED: Divergence points correctly detected and sorted")

    def test_convergence_set_storage(self):
        """Test storing and retrieving ConvergenceSet objects."""
        print("\n" + "=" * 70)
        print("TEST: ConvergenceSet Storage")
        print("=" * 70)

        # Create a convergence set
        convergence_set = ConvergenceSet(
            set_id="conv_test_123",
            template_id="hospital_crisis",
            run_ids='["run_1", "run_2", "run_3"]',
            run_count=3,
            convergence_score=0.85,
            min_similarity=0.80,
            max_similarity=0.90,
            robustness_grade="B",
            consensus_edge_count=10,
            contested_edge_count=3,
            divergence_points='[{"edge": ["t1", "t2", "temporal"], "ratio": 0.67}]',
        )

        # Save to database
        self.store.save_convergence_set(convergence_set)
        print(f"  Saved ConvergenceSet: {convergence_set.set_id}")

        # Retrieve and verify
        retrieved = self.store.get_convergence_set("conv_test_123")

        assert retrieved is not None, "Should retrieve saved convergence set"
        assert retrieved.set_id == convergence_set.set_id
        assert retrieved.template_id == convergence_set.template_id
        assert retrieved.convergence_score == convergence_set.convergence_score
        assert retrieved.robustness_grade == convergence_set.robustness_grade

        print(f"  Retrieved: {retrieved.set_id}")
        print(f"  Score: {retrieved.convergence_score:.1%}")
        print(f"  Grade: {retrieved.robustness_grade}")

        print("\n✅ PASSED: ConvergenceSet storage and retrieval works")

    def test_convergence_stats_aggregation(self):
        """Test aggregate convergence statistics."""
        print("\n" + "=" * 70)
        print("TEST: Convergence Stats Aggregation")
        print("=" * 70)

        # Create multiple convergence sets
        test_sets = [
            ConvergenceSet(
                set_id=f"conv_test_{i}",
                template_id="template_A" if i < 2 else "template_B",
                run_ids=f'["r{i}_1", "r{i}_2"]',
                run_count=2,
                convergence_score=0.7 + i * 0.05,
                robustness_grade=["C", "B", "B", "A"][i],
            )
            for i in range(4)
        ]

        for cs in test_sets:
            self.store.save_convergence_set(cs)

        # Get aggregate stats
        stats = self.store.get_convergence_stats()

        print(f"\nAggregate Stats:")
        print(f"  Total Sets: {stats.get('total_sets', 0)}")
        print(f"  Average Score: {stats.get('average_score', 0):.1%}")
        print(f"  Grade Distribution: {stats.get('grade_distribution', {})}")
        print(f"  Template Coverage: {stats.get('template_coverage', {})}")

        assert stats.get('total_sets', 0) == 4, "Should have 4 convergence sets"
        assert 0.7 < stats.get('average_score', 0) < 0.9, "Average score should be around 0.8"

        print("\n✅ PASSED: Convergence stats aggregation works")

    def test_empty_graphs_handling(self):
        """Test handling of empty graphs."""
        print("\n" + "=" * 70)
        print("TEST: Empty Graphs Handling")
        print("=" * 70)

        g1 = self._create_sample_graph("run_1")  # No edges
        g2 = self._create_sample_graph("run_2")  # No edges

        result = compute_convergence_from_graphs([g1, g2])

        print(f"\nResults for empty graphs:")
        print(f"  Convergence Score: {result.convergence_score}")
        print(f"  Both empty = identical = 1.0 convergence")

        # Two empty graphs are identical (Jaccard of empty sets = 1.0)
        assert result.convergence_score == 1.0, "Empty graphs should be considered identical"

        print("\n✅ PASSED: Empty graphs handled correctly")

    def test_single_edge_graphs(self):
        """Test graphs with single edges."""
        print("\n" + "=" * 70)
        print("TEST: Single Edge Graphs")
        print("=" * 70)

        g1 = self._create_sample_graph("run_1", temporal_edges=[("a", "b")])
        g2 = self._create_sample_graph("run_2", temporal_edges=[("a", "b")])
        g3 = self._create_sample_graph("run_3", temporal_edges=[("c", "d")])

        # g1 and g2 should match perfectly
        sim_12 = graph_similarity(g1, g2)
        assert sim_12 == 1.0, "Identical single-edge graphs should have similarity 1.0"

        # g1 and g3 should have no overlap
        sim_13 = graph_similarity(g1, g3)
        assert sim_13 == 0.0, "Disjoint single-edge graphs should have similarity 0.0"

        print(f"  Similarity(g1, g2): {sim_12}")
        print(f"  Similarity(g1, g3): {sim_13}")

        print("\n✅ PASSED: Single edge graphs handled correctly")

    def test_graph_serialization(self):
        """Test CausalGraph serialization and deserialization."""
        print("\n" + "=" * 70)
        print("TEST: Graph Serialization")
        print("=" * 70)

        original = self._create_sample_graph(
            "test_run",
            template_id="serialize_test",
            temporal_edges=[("t1", "t2"), ("t2", "t3")],
            knowledge_edges=[("e1", "e2")],
        )
        original.metadata["test_key"] = "test_value"

        # Serialize and deserialize
        serialized = original.to_dict()
        restored = CausalGraph.from_dict(serialized)

        print(f"  Original run_id: {original.run_id}")
        print(f"  Restored run_id: {restored.run_id}")
        print(f"  Temporal edges match: {original.temporal_edges == restored.temporal_edges}")
        print(f"  Knowledge edges match: {original.knowledge_edges == restored.knowledge_edges}")

        assert restored.run_id == original.run_id
        assert restored.template_id == original.template_id
        assert restored.temporal_edges == original.temporal_edges
        assert restored.knowledge_edges == original.knowledge_edges
        assert restored.metadata.get("test_key") == "test_value"

        print("\n✅ PASSED: Graph serialization/deserialization works")

    def test_convergence_result_serialization(self):
        """Test ConvergenceResult serialization."""
        print("\n" + "=" * 70)
        print("TEST: ConvergenceResult Serialization")
        print("=" * 70)

        result = ConvergenceResult(
            run_ids=["r1", "r2", "r3"],
            template_id="test_template",
            mean_similarity=0.85,
            min_similarity=0.80,
            max_similarity=0.90,
            divergence_points=[
                DivergencePoint(
                    edge=("a", "b", "temporal"),
                    present_in_runs=["r1", "r2"],
                    absent_in_runs=["r3"],
                    agreement_ratio=0.67,
                )
            ],
            consensus_edges={("x", "y", "knowledge")},
            contested_edges={("a", "b", "temporal")},
        )

        serialized = result.to_dict()

        print(f"  Serialized keys: {list(serialized.keys())}")
        print(f"  Run count: {serialized['run_count']}")
        print(f"  Grade: {serialized['robustness_grade']}")
        print(f"  Divergence points: {len(serialized['divergence_points'])}")

        assert serialized['convergence_score'] == 0.85
        assert serialized['robustness_grade'] == "B"
        assert serialized['run_count'] == 3
        assert len(serialized['divergence_points']) == 1

        print("\n✅ PASSED: ConvergenceResult serialization works")


@pytest.mark.e2e
def test_full_convergence_pipeline():
    """
    Full E2E test of the convergence pipeline.

    Simulates multiple runs and analyzes convergence.
    """
    print("\n" + "=" * 70)
    print("FULL E2E CONVERGENCE PIPELINE TEST")
    print("=" * 70)

    # Create 5 graphs simulating runs with varying agreement
    graphs = []
    base_temporal = [("origin", "crisis"), ("crisis", "resolution")]
    base_knowledge = [("alice", "bob"), ("bob", "carol")]

    for i in range(5):
        temporal = list(base_temporal)
        knowledge = list(base_knowledge)

        # Add some variation
        if i % 2 == 0:
            temporal.append(("resolution", f"aftermath_{i}"))
        if i % 3 == 0:
            knowledge.append(("carol", "dave"))

        g = CausalGraph(
            run_id=f"pipeline_run_{i}",
            template_id="pipeline_test",
            temporal_edges=set(temporal),
            knowledge_edges=set(knowledge),
        )
        graphs.append(g)

    # Compute convergence
    result = compute_convergence_from_graphs(graphs)

    print(f"\nPipeline Results (5 runs):")
    print(f"  Convergence Score: {result.convergence_score:.1%}")
    print(f"  Robustness Grade: {result.robustness_grade}")
    print(f"  Min/Max Similarity: {result.min_similarity:.1%} / {result.max_similarity:.1%}")
    print(f"  Consensus Edges: {len(result.consensus_edges)}")
    print(f"  Contested Edges: {len(result.contested_edges)}")
    print(f"  Divergence Points: {len(result.divergence_points)}")

    if result.divergence_points:
        print("\n  Top Divergence Points:")
        for dp in result.divergence_points[:3]:
            print(f"    - {dp.edge}: {dp.agreement_ratio:.0%} agreement")

    # Verify reasonable results
    assert 0 < result.convergence_score < 1, "Score should be between 0 and 1"
    assert result.run_count == 5
    assert len(result.consensus_edges) >= 2, "Should have base consensus edges"

    print("\n" + "=" * 70)
    print("✅ FULL E2E CONVERGENCE PIPELINE TEST: SUCCESS")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    pytest_args = [__file__, "-v", "-s", "-m", "e2e"]
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)
