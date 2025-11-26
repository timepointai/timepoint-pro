# evaluation/__init__.py - Causal graph convergence evaluation
"""
Evaluation module for measuring causal graph convergence across simulation runs.

This module provides tools for:
- Extracting causal graphs from simulation runs
- Computing similarity between causal graphs
- Measuring convergence across multiple runs of the same scenario
- Identifying divergence points in causal chains

The key insight: Timepoint predicts causal mechanisms, not just outcomes.
Convergence across independent runs indicates robust causal chains.
"""

from evaluation.convergence import (
    CausalGraph,
    ConvergenceResult,
    extract_causal_graph,
    graph_similarity,
    compute_convergence,
    find_divergence_points,
)

__all__ = [
    "CausalGraph",
    "ConvergenceResult",
    "extract_causal_graph",
    "graph_similarity",
    "compute_convergence",
    "find_divergence_points",
]
