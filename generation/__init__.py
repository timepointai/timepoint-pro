"""
Generation Infrastructure for Timepoint-Pro Phase 2

This module provides synthetic data generation capabilities including:
- World management and isolation
- Horizontal generation (scenario variations)
- Vertical generation (temporal depth)
- Progress tracking and fault handling
"""

from .world_manager import WorldManager, IsolationMode
from .config_schema import SimulationConfig
from .horizontal_generator import HorizontalGenerator
from .variation_strategies import (
    VariationStrategy,
    VariationStrategyFactory,
    PersonalityVariation,
    KnowledgeVariation,
    RelationshipVariation,
    OutcomeVariation,
    StartingConditionVariation
)
from .vertical_generator import VerticalGenerator
from .temporal_expansion import TemporalExpander
from .progress_tracker import ProgressTracker, GenerationMetrics
from .fault_handler import FaultHandler, ErrorSeverity
from .checkpoint_manager import CheckpointManager

__all__ = [
    "WorldManager",
    "IsolationMode",
    "SimulationConfig",
    "HorizontalGenerator",
    "VariationStrategy",
    "VariationStrategyFactory",
    "PersonalityVariation",
    "KnowledgeVariation",
    "RelationshipVariation",
    "OutcomeVariation",
    "StartingConditionVariation",
    "VerticalGenerator",
    "TemporalExpander",
    "ProgressTracker",
    "GenerationMetrics",
    "FaultHandler",
    "ErrorSeverity",
    "CheckpointManager",
]
