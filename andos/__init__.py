"""
ANDOS (Acyclical Network Directed Orthogonal Synthesis)
========================================================

Phase 10 implementation to solve M14/M15 circular dependency.

Core concept: Train entities in reverse topological order (periphery to core)
like crystal formation from seeds, ensuring tensors exist before dialog synthesis.

Modules:
    - layer_computer: Core ANDOS algorithm for computing training layers
"""

from .layer_computer import (
    compute_andos_layers,
    validate_andos_layers,
    build_interaction_graph
)

__all__ = [
    'compute_andos_layers',
    'validate_andos_layers',
    'build_interaction_graph'
]

__version__ = '0.1.0'
