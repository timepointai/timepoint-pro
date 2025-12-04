"""
Pydantic models for Simulation API request/response schemas.

Defines data transfer objects for simulation job management.

Phase 6: Public API - Simulation Endpoints
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class SimulationStatus(str, Enum):
    """Simulation job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TemporalModeAPI(str, Enum):
    """Temporal mode options for API."""
    PEARL = "pearl"
    DIRECTORIAL = "directorial"
    CYCLICAL = "cyclical"
    BRANCHING = "branching"
    PORTAL = "portal"


# ============================================================================
# Request Models
# ============================================================================

class SimulationCreateRequest(BaseModel):
    """Request model for creating a simulation job."""

    # Natural language description OR template
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Natural language description of the simulation scenario"
    )
    template_id: Optional[str] = Field(
        None,
        description="Template ID to use (e.g., 'board_meeting', 'detective_interrogation')"
    )

    # Entity configuration
    entity_count: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of entities to generate (1-20)"
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description="Types of entities (e.g., ['human', 'organization'])"
    )

    # Temporal configuration
    timepoint_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of timepoints to generate (1-20)"
    )
    temporal_mode: TemporalModeAPI = Field(
        default=TemporalModeAPI.PEARL,
        description="Temporal reasoning mode"
    )

    # Output configuration
    generate_summaries: bool = Field(
        default=True,
        description="Generate LLM-powered narrative summaries"
    )
    export_formats: List[str] = Field(
        default=["json", "markdown"],
        description="Export formats: 'json', 'markdown', 'pdf'"
    )

    # Optional metadata
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the simulation"
    )

    @field_validator("export_formats")
    @classmethod
    def validate_export_formats(cls, v):
        """Validate export formats."""
        valid_formats = {"json", "markdown", "pdf"}
        for fmt in v:
            if fmt not in valid_formats:
                raise ValueError(f"Invalid export format: {fmt}. Valid: {valid_formats}")
        return v

    def model_post_init(self, __context):
        """Validate that either description or template_id is provided."""
        if not self.description and not self.template_id:
            raise ValueError("Either 'description' or 'template_id' must be provided")


class SimulationCancelRequest(BaseModel):
    """Request to cancel a running simulation."""
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional reason for cancellation"
    )


# ============================================================================
# Response Models
# ============================================================================

class SimulationJobResponse(BaseModel):
    """Response model for a simulation job."""

    job_id: str = Field(..., description="Unique job identifier")
    status: SimulationStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")

    # Configuration echo
    template_id: Optional[str] = Field(None, description="Template used")
    description: Optional[str] = Field(None, description="Description used")
    entity_count: int = Field(..., description="Configured entity count")
    timepoint_count: int = Field(..., description="Configured timepoint count")
    temporal_mode: str = Field(..., description="Temporal mode")

    # Progress
    progress_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)"
    )
    current_step: Optional[str] = Field(None, description="Current processing step")

    # Results (populated when completed)
    run_id: Optional[str] = Field(None, description="Internal run ID")
    entities_created: Optional[int] = Field(None, description="Entities created")
    timepoints_created: Optional[int] = Field(None, description="Timepoints created")
    cost_usd: Optional[float] = Field(None, description="API cost in USD")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")

    # Error info (populated on failure)
    error_message: Optional[str] = Field(None, description="Error message if failed")

    # Owner info
    owner_id: str = Field(..., description="User who created the job")

    class Config:
        from_attributes = True


class SimulationResultResponse(BaseModel):
    """Detailed simulation result response."""

    job: SimulationJobResponse = Field(..., description="Job details")

    # Simulation outputs
    entities: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Generated entities"
    )
    timepoints: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Generated timepoints"
    )
    relationships: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Entity relationships"
    )

    # Narrative outputs
    summary: Optional[str] = Field(None, description="Narrative summary")
    narrative_exports: Optional[Dict[str, str]] = Field(
        None,
        description="Export file URLs by format"
    )

    # Metrics
    convergence_score: Optional[float] = Field(
        None,
        description="Causal consistency score (0-1)"
    )
    robustness_grade: Optional[str] = Field(
        None,
        description="Robustness grade (A-F)"
    )


class SimulationListResponse(BaseModel):
    """Response model for listing simulation jobs."""

    jobs: List[SimulationJobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total job count")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")


class SimulationStatsResponse(BaseModel):
    """Statistics about simulation jobs."""

    total_jobs: int = Field(..., description="Total jobs created")
    pending_jobs: int = Field(..., description="Jobs waiting to run")
    running_jobs: int = Field(..., description="Currently running jobs")
    completed_jobs: int = Field(..., description="Successfully completed jobs")
    failed_jobs: int = Field(..., description="Failed jobs")
    cancelled_jobs: int = Field(..., description="Cancelled jobs")

    total_cost_usd: float = Field(..., description="Total API cost")
    total_tokens: int = Field(..., description="Total tokens used")
    avg_duration_seconds: Optional[float] = Field(
        None,
        description="Average job duration"
    )


# ============================================================================
# Template Models
# ============================================================================

class TemplateInfo(BaseModel):
    """Information about an available template."""

    template_id: str = Field(..., description="Template identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    tier: str = Field(..., description="Complexity tier: quick, standard, comprehensive")
    mechanisms: List[str] = Field(..., description="Mechanisms exercised (M1-M18)")
    default_entity_count: int = Field(..., description="Default entity count")
    default_timepoint_count: int = Field(..., description="Default timepoint count")
    estimated_cost_usd: float = Field(..., description="Estimated cost")
    estimated_duration_seconds: int = Field(..., description="Estimated duration")


class TemplateListResponse(BaseModel):
    """Response model for listing available templates."""

    templates: List[TemplateInfo] = Field(..., description="Available templates")
    total: int = Field(..., description="Total template count")
    categories: List[str] = Field(..., description="Available categories")
