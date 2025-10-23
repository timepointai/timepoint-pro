"""
Metadata tracking system for Timepoint-Daedalus

Provides:
- Run tracking and metadata storage
- Coverage matrix generation
- Mechanism tracking decorators
- Logfire integration
"""

from .run_tracker import (
    MetadataManager,
    RunMetadata,
    MechanismUsage,
    ResolutionAssignment,
    ValidationRecord,
    ALL_MECHANISMS
)

from .coverage_matrix import CoverageMatrix

from .tracking import (
    track_mechanism,
    track_resolution,
    track_validation,
    set_current_run_id,
    get_current_run_id,
    clear_current_run_id,
    set_metadata_manager,
    get_metadata_manager
)

from . import logfire_setup

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
    "logfire_setup"
]
