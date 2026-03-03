"""
Metadata tracking system for Timepoint-Pro

Provides:
- Run tracking and metadata storage
- Coverage matrix generation
- Mechanism tracking decorators
- Logfire integration
"""

from . import logfire_setup
from .coverage_matrix import CoverageMatrix
from .run_tracker import (
    ALL_MECHANISMS,
    MechanismUsage,
    MetadataManager,
    ResolutionAssignment,
    RunMetadata,
    ValidationRecord,
)
from .tracking import (
    clear_current_run_id,
    get_current_run_id,
    get_metadata_manager,
    set_current_run_id,
    set_metadata_manager,
    track_mechanism,
    track_resolution,
    track_validation,
)

__all__ = [
    "MetadataManager",
    "RunMetadata",
    "MechanismUsage",
    "ResolutionAssignment",
    "ValidationRecord",
    "ALL_MECHANISMS",
    "CoverageMatrix",
    "track_mechanism",
    "track_resolution",
    "track_validation",
    "set_current_run_id",
    "get_current_run_id",
    "clear_current_run_id",
    "set_metadata_manager",
    "get_metadata_manager",
    "logfire_setup",
]
